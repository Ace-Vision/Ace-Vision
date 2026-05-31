"""
ml/renderer.py — Skeleton overlay and colour-coded deviation rendering.

Draws visual feedback on each video frame showing the player's pose with
colour-coded joint indicators based on deviation severity.

Drawing order per frame:
1. White skeleton lines (MediaPipe POSE_CONNECTIONS, 60% opacity)
2. Colour-coded joint dots for the 9 serve joints:
   - Green  #4CAF50 — severity < 0.3
   - Amber  #FF9800 — severity 0.3–0.6
   - Red    #F44336 — severity > 0.6
3. Small angle arc at each joint (radius 30px, matching colour)
4. HUD top-left: All 9 deviations with direction (高いです/低いです)

Key responsibilities:
- Accept original video frames, keypoints, and deviation scores
- Draw skeleton connections with transparency
- Draw coloured circles at each of the 9 joints based on severity
- Draw angle arcs at joint vertices
- Render text HUD overlay with top deviations
- Encode output as an MP4 video file
"""

import os
import cv2
import numpy as np
import mediapipe as mp
from mediapipe.tasks.python import vision


# Pose connections (landmark indices)
POSE_CONNECTIONS = [
    (0, 1), (1, 2), (2, 3), (3, 7), (0, 4), (4, 5), (5, 6), (6, 8),
    (9, 10), (11, 12), (11, 13), (13, 15), (15, 17), (15, 19), (15, 21),
    (17, 19), (12, 14), (14, 16), (16, 18), (16, 20), (16, 22), (18, 20),
    (11, 23), (12, 24), (23, 24),
    (23, 25), (25, 27), (27, 29), (29, 31),
    (24, 26), (26, 28), (28, 30), (30, 32),
    (25, 27), (26, 28), (27, 29), (28, 30), (29, 31), (30, 32)
]

# Get landmark names
landmark_names = [landmark.name.lower() for landmark in vision.PoseLandmark]
index_to_name = {i: name for i, name in enumerate(landmark_names)}


def render_video(video_path: str, keypoints_list: list[dict], deviation_scores: dict = None, angles_list: list[dict] = None, highlight_joint: str | None = None) -> str:
    """
    Render video with pose skeleton overlay and deviation feedback.

    Args:
        video_path (str): Path to the input video.
        keypoints_list (list[dict]): List of keypoints per frame.
        deviation_scores (dict, optional): Deviation scores from scorer. Defaults to None.

    Returns:
        str: Path to the output video.
    """
    # Open input video
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise ValueError(f"Could not open video file: {video_path}")

    # Get video properties
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    base, _ = os.path.splitext(video_path)
    output_path = base + '_overlay.mp4'

    # Try H.264 encoders natively available in OpenCV.
    # On Linux servers OpenCV is often built without H.264, so we fall back to
    # writing mp4v and then re-encoding to H.264 via ffmpeg.
    out = None
    use_ffmpeg_reencode = False
    for codec in ["avc1", "H264", "X264"]:
        fourcc = cv2.VideoWriter_fourcc(*codec)
        candidate = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
        if candidate.isOpened():
            out = candidate
            break
        candidate.release()

    if out is None:
        # No native H.264 — write to a temp file with mp4v, transcode later.
        import tempfile
        _tmp_fd, _tmp_path = tempfile.mkstemp(suffix='_overlay_raw.mp4')
        os.close(_tmp_fd)
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        out = cv2.VideoWriter(_tmp_path, fourcc, fps, (width, height))
        if not out.isOpened():
            raise ValueError("Could not open any video writer (tried avc1, H264, X264, mp4v).")
        use_ffmpeg_reencode = True

    # Joint to landmark mapping
    joint_landmarks = {
        'right_elbow_flexion': 'right_elbow',
        'left_elbow_flexion': 'left_elbow',
        'right_shoulder_abduction': 'right_shoulder',
        'left_shoulder_abduction': 'left_shoulder',
        'right_knee_flexion': 'right_knee',
        'left_knee_flexion': 'left_knee',
        'trunk_lateral_tilt': 'nose',  # Approximate
        'hip_shoulder_separation': 'left_shoulder',  # Approximate
        'wrist_extension': 'right_wrist'
    }

    sw = (deviation_scores or {}).get("swing_window")
    win_start = sw[0] if sw else 0
    win_end   = sw[1] if sw else frame_count - 1

    frame_num = 0
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        if frame_num < win_start:
            frame_num += 1
            continue
        if frame_num > win_end:
            break

        kp = keypoints_list[frame_num] if frame_num < len(keypoints_list) else {}

        # Draw skeleton
        if kp:
            for start_idx, end_idx in POSE_CONNECTIONS:
                start_name = index_to_name.get(start_idx)
                end_name = index_to_name.get(end_idx)
                if start_name in kp and end_name in kp:
                    start_point = (int(kp[start_name]['x'] * width), int(kp[start_name]['y'] * height))
                    end_point = (int(kp[end_name]['x'] * width), int(kp[end_name]['y'] * height))
                    cv2.line(frame, start_point, end_point, (220, 220, 220), 4, cv2.LINE_AA)

        # Build per-frame deviations.
        # If we have live angles for this frame, compute severity on the fly.
        # Fall back to the peak-frame deviation_scores if angles aren't available.
        frame_angles = angles_list[frame_num] if (angles_list and frame_num < len(angles_list)) else {}
        peak_deviations = deviation_scores.get('deviations', {}) if deviation_scores else {}

        # For each joint, pick severity from live angles (using peak severity as reference scale)
        # or fall back to the static peak value.
        def get_live_severity(joint):
            # If we have a live angle and a peak reference, scale severity the same way.
            if joint in frame_angles and frame_angles[joint] is not None and joint in peak_deviations:
                peak = peak_deviations[joint]
                # Re-compute severity using same 2*std denominator from peak data.
                # severity = deviation / (2*std)  =>  2*std = deviation / severity
                if peak['severity_score'] > 0:
                    two_std = peak['deviation_deg'] / peak['severity_score']
                    live_dev = abs(frame_angles[joint] - (peak['angle'] - peak['deviation_deg']
                                   if peak['direction'] == 'too_high'
                                   else peak['angle'] + peak['deviation_deg']))
                    return min(live_dev / two_std, 1.0), frame_angles[joint]
            # Fall back to peak value
            if joint in peak_deviations:
                return peak_deviations[joint]['severity_score'], peak_deviations[joint]['angle']
            return None, None

        def severity_color(severity):
            if severity < 0.3:
                return (76, 175, 80)   # Green
            elif severity < 0.6:
                return (255, 152, 0)   # Amber
            else:
                return (244, 67, 54)   # Red

        # Draw deviation overlays — filled dots with white border
        for joint, landmark_name in joint_landmarks.items():
            if landmark_name in kp:
                x, y = int(kp[landmark_name]['x'] * width), int(kp[landmark_name]['y'] * height)
                severity, _ = get_live_severity(joint)
                if severity is not None:
                    color = severity_color(severity)
                    cv2.circle(frame, (x, y), 13, (255, 255, 255), -1, cv2.LINE_AA)
                    cv2.circle(frame, (x, y), 10, color, -1, cv2.LINE_AA)


        # Highlight the worst joint — semi-transparent filled glow
        if highlight_joint and kp and highlight_joint in kp:
            hx = int(kp[highlight_joint]['x'] * width)
            hy = int(kp[highlight_joint]['y'] * height)
            pulse = int(6 * abs(np.sin(frame_num * 0.25)))
            # Outer glow (semi-transparent)
            overlay = frame.copy()
            cv2.circle(overlay, (hx, hy), 38 + pulse, (0, 0, 230), -1, cv2.LINE_AA)
            cv2.addWeighted(overlay, 0.35, frame, 0.65, 0, frame)
            # Inner solid fill
            cv2.circle(frame, (hx, hy), 18, (0, 0, 230), -1, cv2.LINE_AA)
            # White border
            cv2.circle(frame, (hx, hy), 18, (255, 255, 255), 2, cv2.LINE_AA)

        out.write(frame)
        frame_num += 1

    cap.release()
    out.release()

    if use_ffmpeg_reencode:
        import subprocess
        subprocess.run(
            ["ffmpeg", "-y", "-i", _tmp_path,
             "-vcodec", "libx264", "-preset", "fast", "-crf", "23",
             "-movflags", "+faststart", output_path],
            check=True, capture_output=True,
        )
        os.unlink(_tmp_path)

    return output_path
