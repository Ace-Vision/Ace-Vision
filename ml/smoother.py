"""
ml/smoother.py — Gaussian smoothing on keypoint time series.

Applies a 1-D Gaussian filter (scipy.ndimage.gaussian_filter1d) to each
keypoint coordinate across frames to reduce jitter from MediaPipe detection
noise.

Key responsibilities:
- Accept raw per-frame keypoint data from extractor
- Smooth each (x, y, z) coordinate independently over the time axis
- Configurable sigma parameter for filter width
- Return smoothed keypoint time series in the same format
"""
