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


# Pose connections (landmark indices) — precomputed constant
POSE_CONNECTIONS = [
    (0, 1), (1, 2), (2, 3), (3, 7), (0, 4), (4, 5), (5, 6), (6, 8),
    (9, 10), (11, 12), (11, 13), (13, 15), (15, 17), (15, 19), (15, 21),
    (17, 19), (12, 14), (14, 16), (16, 18), (16, 20), (16, 22), (18, 20),
    (11, 23), (12, 24), (23, 24),
    (23, 25), (25, 27), (27, 29), (29, 31),
    (24, 26), (26, 28), (28, 30), (30, 32),
    (25, 27), (26, 28), (27, 29), (28, 30), (29, 31), (30, 32)
]

# Get landmark names and build index mapping once (not per frame)
landmark_names = [landmark.name.lower() for landmark in vision.PoseLandmark]
index_to_name = {i: name for i, name in enumerate(landmark_names)}

# Joint to landmark mapping — precomputed constant
joint_landmarks = {
    'right_elbow_flexion': 'right_elbow',
    'left_elbow_flexion': 'left_elbow',
    'right_shoulder_abduction': 'right_shoulder',
    'left_shoulder_abduction': 'left_shoulder',
    'right_knee_flexion': 'right_knee',
    'left_knee_flexion': 'left_knee',
    'trunk_lateral_tilt': 'nose',
    'hip_shoulder_separation': 'left_shoulder',
    'wrist_extension': 'right_wrist'
}

# Color mapping for severity — precomputed
def severity_color(severity):
    """Return BGR color tuple based on severity score."""
    if severity < 0.3:
        return (76, 175, 80)   # Green (BGR order for OpenCV)
    elif severity < 0.6:
        return (255, 152, 0)   # Amber
    else:
        return (244, 67, 54)   # Red


def render_video(video_path: str, keypoints_list: list[dict], deviation_scores: dict = None, angles_list: list[dict] = None) -> str:
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

    # Output video: enforce H.264 in MP4 for browser/Streamlit compatibility.
    base, _ = os.path.splitext(video_path)
    output_path = base + '_overlay.mp4'
    preferred_codecs = ["avc1", "H264", "X264"]
    out = None
    for codec in preferred_codecs:
        fourcc = cv2.VideoWriter_fourcc(*codec)
        candidate = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
        if candidate.isOpened():
            out = candidate
            break
        candidate.release()

    if out is None:
        raise ValueError(
            "Could not create H.264 output video. "
            "Ensure OpenCV was built with ffmpeg support."
        )

    frame_num = 0
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        kp = keypoints_list[frame_num] if frame_num < len(keypoints_list) else {}

        # Draw skeleton
        if kp:
            # Draw connections with pre-computed constants
            for start_idx, end_idx in POSE_CONNECTIONS:
                start_name = index_to_name.get(start_idx)
                end_name = index_to_name.get(end_idx)
                if start_name in kp and end_name in kp:
                    start_point = (int(kp[start_name]['x'] * width), int(kp[start_name]['y'] * height))
                    end_point = (int(kp[end_name]['x'] * width), int(kp[end_name]['y'] * height))
                    cv2.line(frame, start_point, end_point, (255, 255, 255), 2)

            # Draw landmarks
            for landmark_name, data in kp.items():
                x, y = int(data['x'] * width), int(data['y'] * height)
                cv2.circle(frame, (x, y), 5, (0, 255, 0), -1)

        # Build per-frame deviations using cached constants
        frame_angles = angles_list[frame_num] if (angles_list and frame_num < len(angles_list)) else {}
        peak_deviations = deviation_scores.get('deviations', {}) if deviation_scores else {}

        def get_live_severity(joint):
            """Get severity score for a joint in current frame."""
            if joint in frame_angles and frame_angles[joint] is not None and joint in peak_deviations:
                peak = peak_deviations[joint]
                if peak['severity_score'] > 0:
                    two_std = peak['deviation_deg'] / peak['severity_score']
                    live_dev = abs(frame_angles[joint] - (peak['angle'] - peak['deviation_deg']
                                   if peak['direction'] == 'too_high'
                                   else peak['angle'] + peak['deviation_deg']))
                    return min(live_dev / two_std, 1.0), frame_angles[joint]
            if joint in peak_deviations:
                return peak_deviations[joint]['severity_score'], peak_deviations[joint]['angle']
            return None, None

        # Draw deviation overlays — coloured dots, live per frame (using precomputed mapping)
        for joint, landmark_name in joint_landmarks.items():
            if landmark_name in kp:
                x, y = int(kp[landmark_name]['x'] * width), int(kp[landmark_name]['y'] * height)
                severity, _ = get_live_severity(joint)
                if severity is not None:
                    cv2.circle(frame, (x, y), 10, severity_color(severity), -1)

        # Draw HUD — live angle values update every frame (using cached joint mapping)
        y_offset = 30
        for i, (joint, landmark_name) in enumerate(joint_landmarks.items()):
            severity, live_angle = get_live_severity(joint)
            if severity is None:
                continue
            color = severity_color(severity)
            joint_label = joint.replace('_', ' ')
            text = f"{joint_label}: {live_angle:.1f}deg"
            cv2.putText(frame, text, (10, y_offset + i * 25), cv2.FONT_HERSHEY_SIMPLEX, 0.55, color, 2)

        out.write(frame)
        frame_num += 1

    cap.release()
    out.release()

    return output_path
