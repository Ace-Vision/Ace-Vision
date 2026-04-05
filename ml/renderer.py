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
4. HUD top-right: top 3 deviations with joint name + degrees off

Key responsibilities:
- Accept original video frames, keypoints, and deviation scores
- Draw skeleton connections with transparency
- Draw coloured circles at each of the 9 joints based on severity
- Draw angle arcs at joint vertices
- Render text HUD overlay with top deviations
- Encode output as an MP4 video file
"""

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


def render_video(video_path: str, keypoints_list: list[dict], deviation_scores: dict = None) -> str:
    """
    Render video with pose skeleton overlay.

    Args:
        video_path (str): Path to the input video.
        keypoints_list (list[dict]): List of keypoints per frame.
        deviation_scores (dict, optional): Deviation scores for joints. Defaults to None.

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

    # Output video
    output_path = video_path.replace('.mp4', '_overlay.mp4')
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

    frame_num = 0
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        kp = keypoints_list[frame_num] if frame_num < len(keypoints_list) else {}

        # Draw skeleton
        if kp:
            # Draw connections
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
                cv2.circle(frame, (x, y), 5, (0, 255, 0), -1)  # Green dots

        out.write(frame)
        frame_num += 1

    cap.release()
    out.release()

    return output_path
