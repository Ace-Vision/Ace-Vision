"""
backend/shot_detector.py - Detect overhead shot events from pose keypoint sequences.

Algorithm:
  1. Per frame: check if right wrist is significantly above right shoulder,
     using a body-scale-relative threshold so camera distance doesn't matter.
  2. Collect triggered frames → merge frames within MERGE_GAP_FRAMES into one event.
  3. Within each event, pick the peak frame (wrist highest above shoulder).
  4. Return clip windows: [peak - PRE_FRAMES, peak + POST_FRAMES] per shot.
  5. Extract and concatenate clips with OpenCV.
"""

import cv2
import os
import tempfile

from qtfaststart import processor as _qtfs


def _faststart(path: str) -> None:
    """Move moov atom to the front so browsers can stream the MP4."""
    tmp = path + ".tmp"
    try:
        _qtfs.process(path, tmp)
        os.replace(tmp, path)
    except Exception:
        if os.path.exists(tmp):
            os.unlink(tmp)

# Wrist must be this fraction of body height above the shoulder to count as overhead
WRIST_THRESHOLD_RATIO = 0.12

# Frames within this gap are merged into the same shot event (~0.5s at 30fps)
MERGE_GAP_FRAMES = 18

# Clip window around peak contact frame
PRE_CONTACT_FRAMES  = 45   # ~1.5s before contact
POST_CONTACT_FRAMES = 20   # ~0.67s after contact

# Skip every N frames during extraction to speed up long videos (1 = process all)
SAMPLE_STRIDE = 3


def _body_scale(kp: dict) -> float:
    """Estimate body height in normalised coords (nose-y to mid-hip-y)."""
    nose  = kp.get("nose")
    l_hip = kp.get("left_hip")
    r_hip = kp.get("right_hip")
    if not nose or not l_hip or not r_hip:
        return 0.25
    mid_hip_y = (l_hip["y"] + r_hip["y"]) / 2.0
    return max(mid_hip_y - nose["y"], 0.05)


def _wrist_above_shoulder(kp: dict) -> float:
    """
    Return how far the right wrist is above the right shoulder in normalised coords.
    Positive = wrist is higher (y decreases upward in normalised space).
    Returns 0.0 if landmarks missing.
    """
    wrist    = kp.get("right_wrist")
    shoulder = kp.get("right_shoulder")
    if not wrist or not shoulder:
        return 0.0
    # y increases downward, so wrist above shoulder → wrist.y < shoulder.y
    return shoulder["y"] - wrist["y"]


# Actual (non-strided) frames before contact to examine for classification
CLASSIFY_LOOKBACK = 5

# Minimum confidence to include a clip in typed groups
CLASSIFY_CONFIDENCE_THRESHOLD = 0.60


def classify_shots_from_video(
    video_path: str,
    shots: list[dict],
    fps: float,
) -> list[dict]:
    """
    Classify each shot as forehand or backhand by reading the 5 consecutive
    (non-strided) frames before the contact peak and checking right-wrist x movement.

    MediaPipe coords are screen-relative: x=0 left edge, x=1 right edge.
    Forehand: wrist approaches from screen-right → x decreases before contact.
    Backhand: wrist approaches from screen-left  → x increases before contact.
    """
    import cv2 as _cv2
    import mediapipe as _mp
    from mediapipe.tasks import python
    from mediapipe.tasks.python import vision

    RIGHT_WRIST_IDX = 16  # MediaPipe pose landmark index for right_wrist

    base_options = python.BaseOptions(model_asset_path="models/pose_landmarker.task")
    options = vision.PoseLandmarkerOptions(
        base_options=base_options,
        running_mode=vision.RunningMode.IMAGE,
    )
    landmarker = vision.PoseLandmarker.create_from_options(options)
    cap = _cv2.VideoCapture(video_path)

    for shot in shots:
        peak = shot["peak_frame"]
        start = max(0, peak - CLASSIFY_LOOKBACK)

        cap.set(_cv2.CAP_PROP_POS_FRAMES, start)
        wrist_xs = []

        for _ in range(peak - start + 1):
            ret, frame = cap.read()
            if not ret:
                break
            frame_rgb = _cv2.cvtColor(frame, _cv2.COLOR_BGR2RGB)
            mp_img = _mp.Image(image_format=_mp.ImageFormat.SRGB, data=frame_rgb)
            result = landmarker.detect(mp_img)
            if result.pose_landmarks:
                wrist_xs.append(result.pose_landmarks[0][RIGHT_WRIST_IDX].x)

        if len(wrist_xs) < 2:
            shot["shot_type"] = "forehand"
            shot["confidence"] = 0.5
            continue

        net_dx = wrist_xs[-1] - wrist_xs[0]
        confidence = min(1.0, 0.5 + abs(net_dx) * 5.0)
        shot["shot_type"] = "forehand" if net_dx < 0 else "backhand"
        shot["confidence"] = round(confidence, 3)

    cap.release()
    return shots


def detect_shots(keypoints_list: list[dict], fps: float) -> list[dict]:
    """
    Detect overhead shot events from a pose keypoint sequence.

    Args:
        keypoints_list: one dict per frame (may be sparse if SAMPLE_STRIDE > 1,
                        but indices must correspond to original frame numbers).
        fps: video frame rate.

    Returns:
        List of dicts:
            peak_frame  – frame index with highest wrist position
            start_frame – clip start (clamped to 0)
            end_frame   – clip end (clamped to last frame)
            peak_time_s – peak_frame / fps
    """
    total_frames = len(keypoints_list)

    # Step 1: score every frame
    triggered = []
    for i, kp in enumerate(keypoints_list):
        if not kp:
            continue
        above = _wrist_above_shoulder(kp)
        scale = _body_scale(kp)
        if above > WRIST_THRESHOLD_RATIO * scale:
            triggered.append((i, above))

    if not triggered:
        return []

    # Step 2: merge nearby frames into events
    events: list[list[tuple]] = []
    group = [triggered[0]]
    for item in triggered[1:]:
        if item[0] - group[-1][0] <= MERGE_GAP_FRAMES:
            group.append(item)
        else:
            events.append(group)
            group = [item]
    events.append(group)

    # Step 3: pick peak frame per event, build clip windows
    # Classification happens later in classify_shots_from_video (uses actual video frames)
    shots = []
    for group in events:
        peak_frame, _ = max(group, key=lambda x: x[1])
        shots.append({
            "peak_frame":  peak_frame,
            "start_frame": max(0, peak_frame - PRE_CONTACT_FRAMES),
            "end_frame":   min(total_frames - 1, peak_frame + POST_CONTACT_FRAMES),
            "peak_time_s": peak_frame / fps,
            "shot_type":   "forehand",
            "confidence":  0.5,
        })

    return shots


def extract_clip(video_path: str, start_frame: int, end_frame: int, out_path: str) -> None:
    """Write frames [start_frame, end_frame] inclusive from video_path to out_path."""
    cap    = cv2.VideoCapture(video_path)
    fps    = cap.get(cv2.CAP_PROP_FPS) or 30.0
    w      = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h      = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fourcc = cv2.VideoWriter_fourcc(*"avc1")
    out    = cv2.VideoWriter(out_path, fourcc, fps, (w, h))

    cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)
    for _ in range(end_frame - start_frame + 1):
        ret, frame = cap.read()
        if not ret:
            break
        out.write(frame)

    cap.release()
    out.release()
    _faststart(out_path)


def concatenate_clips(clip_paths: list[str], out_path: str) -> None:
    """Concatenate a list of clip videos into a single output video."""
    if not clip_paths:
        raise ValueError("No clips to concatenate")

    cap    = cv2.VideoCapture(clip_paths[0])
    fps    = cap.get(cv2.CAP_PROP_FPS) or 30.0
    w      = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h      = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    cap.release()

    fourcc = cv2.VideoWriter_fourcc(*"avc1")
    out    = cv2.VideoWriter(out_path, fourcc, fps, (w, h))

    for path in clip_paths:
        cap = cv2.VideoCapture(path)
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            out.write(frame)
        cap.release()

    out.release()


def extract_keypoints_strided(video_path: str, stride: int = SAMPLE_STRIDE) -> tuple[list[dict], float]:
    """
    Run pose estimation on every `stride`-th frame for speed.
    Returns (keypoints_list, fps) where keypoints_list[i] corresponds to
    frame i of the ORIGINAL video (non-sampled frames get empty dicts).
    """
    import cv2 as _cv2
    import mediapipe as _mp
    from mediapipe.tasks import python
    from mediapipe.tasks.python import vision

    cap        = _cv2.VideoCapture(video_path)
    fps        = cap.get(_cv2.CAP_PROP_FPS) or 30.0
    total      = int(cap.get(_cv2.CAP_PROP_FRAME_COUNT))
    cap.release()

    base_options = python.BaseOptions(model_asset_path="models/pose_landmarker.task")
    options = vision.PoseLandmarkerOptions(
        base_options=base_options,
        running_mode=vision.RunningMode.VIDEO,
        min_pose_detection_confidence=0.5,
        min_pose_presence_confidence=0.5,
        min_tracking_confidence=0.5,
    )
    landmarker = vision.PoseLandmarker.create_from_options(options)

    cap = _cv2.VideoCapture(video_path)
    keypoints_list: list[dict] = [{}] * total
    frame_idx = 0

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        if frame_idx % stride == 0:
            frame_rgb  = _cv2.cvtColor(frame, _cv2.COLOR_BGR2RGB)
            mp_image   = _mp.Image(image_format=_mp.ImageFormat.SRGB, data=frame_rgb)
            timestamp  = int(frame_idx / fps * 1000)
            result     = landmarker.detect_for_video(mp_image, timestamp)

            if result.pose_landmarks:
                landmarks = {}
                for idx, lm in enumerate(result.pose_landmarks[0]):
                    name = vision.PoseLandmark(idx).name.lower()
                    landmarks[name] = {"x": lm.x, "y": lm.y, "z": lm.z, "visibility": lm.visibility}
                keypoints_list[frame_idx] = landmarks

        frame_idx += 1

    cap.release()
    return keypoints_list, fps
