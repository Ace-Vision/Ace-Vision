"""
ml/extractor.py — MediaPipe pose extraction.

Reads a video file frame-by-frame, runs MediaPipe Pose to detect 33 body
landmarks per frame, and returns the raw keypoint time series as per-frame
JSON-serialisable dicts.

Key responsibilities:
- Open video with OpenCV VideoCapture
- Run MediaPipe Pose on each RGB frame
- Collect landmark (x, y, z, visibility) for all 33 keypoints per frame
- Return list[dict] indexed by frame number
"""

import cv2
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
import numpy as np

# Cache the pose landmarker globally to avoid reinitializing the model per call
_pose_landmarker = None

def _get_pose_landmarker():
    """Lazy-load and cache the MediaPipe Pose Landmarker model."""
    global _pose_landmarker
    if _pose_landmarker is None:
        base_options = python.BaseOptions(model_asset_path="models/pose_landmarker.task")
        options = vision.PoseLandmarkerOptions(
            base_options=base_options,
            running_mode=vision.RunningMode.IMAGE,
            min_pose_detection_confidence=0.5,
            min_pose_presence_confidence=0.5,
            min_tracking_confidence=0.5
        )
        _pose_landmarker = vision.PoseLandmarker.create_from_options(options)
    return _pose_landmarker


def extract_keypoints(video_path: str) -> list[dict]:
    """
    Extract pose keypoints from a video file using MediaPipe Pose.

    Args:
        video_path (str): Path to the video file.

    Returns:
        list[dict]: List of dictionaries, each containing keypoints for a frame.
                    Each dict has keys as landmark names (e.g., 'nose', 'left_shoulder')
                    and values as dicts with 'x', 'y', 'z', 'visibility'.
    """
    # Use cached pose landmarker (avoids model reload)
    pose_landmarker = _get_pose_landmarker()

    # Open video
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise ValueError(f"Could not open video file: {video_path}")

    keypoints_list = []
    frame_count = 0

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        # Convert to MediaPipe Image
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=frame)

        # Process frame with MediaPipe Pose Landmarker
        pose_landmarker_result = pose_landmarker.detect(mp_image)

        if pose_landmarker_result.pose_landmarks:
            # Extract landmarks — pre-allocate dict and use direct assignment for speed
            landmarks = {}
            for idx, landmark in enumerate(pose_landmarker_result.pose_landmarks[0]):
                landmark_name = vision.PoseLandmark(idx).name.lower()
                landmarks[landmark_name] = {
                    'x': landmark.x,
                    'y': landmark.y,
                    'z': landmark.z,
                    'visibility': landmark.visibility
                }
            keypoints_list.append(landmarks)
        else:
            # If no landmarks detected, append empty dict
            keypoints_list.append({})

        frame_count += 1

    cap.release()
    # Don't close the landmarker — keep it cached for next call

    return keypoints_list
