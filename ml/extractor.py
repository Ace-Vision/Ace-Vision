"""
ml/extractor.py — MediaPipe pose extraction.

Reads a video file frame-by-frame, runs MediaPipe Pose to detect 33 body
landmarks per frame, and returns the raw keypoint time series as per-frame
JSON-serialisable dicts.

Key responsibilities:
- Open video with OpenCV VideoCapture
- Run MediaPipe Pose on each RGB frame in VIDEO mode (temporal tracking enabled)
- Collect landmark (x, y, z, visibility) for all 33 keypoints per frame
- Return list[dict] indexed by frame number
"""

import cv2
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision


def extract_keypoints(video_path: str) -> list[dict]:
    """
    Extract pose keypoints from a video file using MediaPipe Pose.

    Uses VIDEO running mode so MediaPipe tracks landmarks across frames,
    which reduces per-frame jitter compared to IMAGE mode.

    Args:
        video_path (str): Path to the video file.

    Returns:
        list[dict]: List of dictionaries, each containing keypoints for a frame.
                    Each dict has keys as landmark names (e.g., 'nose', 'left_shoulder')
                    and values as dicts with 'x', 'y', 'z', 'visibility'.
                    Empty dict for frames where no pose was detected.
    """
    base_options = python.BaseOptions(model_asset_path="models/pose_landmarker.task")
    options = vision.PoseLandmarkerOptions(
        base_options=base_options,
        running_mode=vision.RunningMode.VIDEO,
        min_pose_detection_confidence=0.5,
        min_pose_presence_confidence=0.5,
        min_tracking_confidence=0.5,
    )
    pose_landmarker = vision.PoseLandmarker.create_from_options(options)

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise ValueError(f"Could not open video file: {video_path}")

    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    keypoints_list = []
    frame_idx = 0

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        timestamp_ms = int(frame_idx * 1000 / fps)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=frame_rgb)
        result = pose_landmarker.detect_for_video(mp_image, timestamp_ms)

        if result.pose_landmarks:
            landmarks = {}
            for idx, landmark in enumerate(result.pose_landmarks[0]):
                name = vision.PoseLandmark(idx).name.lower()
                landmarks[name] = {
                    "x": landmark.x,
                    "y": landmark.y,
                    "z": landmark.z,
                    "visibility": landmark.visibility,
                }
            keypoints_list.append(landmarks)
        else:
            keypoints_list.append({})

        frame_idx += 1

    cap.release()
    pose_landmarker.close()

    return keypoints_list
