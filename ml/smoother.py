"""
ml/smoother.py — Gaussian smoothing on keypoint time series.

Applies a 1-D Gaussian filter (scipy.ndimage.gaussian_filter1d) to each
keypoint coordinate across frames to reduce jitter from MediaPipe detection
noise.
"""

import copy
from scipy.ndimage import gaussian_filter1d

def smooth_keypoints(keypoints_list: list[dict], sigma: float = 2.0) -> list[dict]:
    """
    Smooths keypoint coordinates across frames using a Gaussian filter.
    """
    if not keypoints_list:
        return []

    # Deep copy to avoid mutating the original keypoints_list
    smoothed = [copy.deepcopy(kp) if kp else {} for kp in keypoints_list]

    # Find all possible keypoint names
    all_names = set()
    for kp in smoothed:
        if kp:
            all_names.update(kp.keys())

    # For each keypoint name, extract its time series, smooth it, and write it back
    for name in all_names:
        x_series = []
        y_series = []
        z_series = []
        valid_indices = []

        for i, kp in enumerate(smoothed):
            if kp and name in kp:
                x_series.append(kp[name]['x'])
                y_series.append(kp[name]['y'])
                z_series.append(kp[name]['z'])
                valid_indices.append(i)

        if not valid_indices:
            continue

        # Apply Gaussian filter
        x_smooth = gaussian_filter1d(x_series, sigma=sigma)
        y_smooth = gaussian_filter1d(y_series, sigma=sigma)
        z_smooth = gaussian_filter1d(z_series, sigma=sigma)

        # Write smoothed values back
        for idx, x, y, z in zip(valid_indices, x_smooth, y_smooth, z_smooth):
            smoothed[idx][name]['x'] = float(x)
            smoothed[idx][name]['y'] = float(y)
            smoothed[idx][name]['z'] = float(z)

    return smoothed
