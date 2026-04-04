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
