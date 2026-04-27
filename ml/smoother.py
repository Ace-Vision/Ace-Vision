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

import numpy as np
from scipy.ndimage import gaussian_filter1d


def smooth_keypoints(keypoints_list: list[dict], sigma: float = 1.5) -> list[dict]:
    """
    Smooth per-frame keypoint coordinates with a Gaussian filter.

    For each landmark, builds a time series across all frames, fills any
    detection gaps with linear interpolation (for smoothing only), applies
    the filter, then writes smoothed values back — but only for frames
    where the landmark was originally detected.

    Visibility scores are not smoothed; they reflect MediaPipe's per-frame
    confidence and should stay tied to the original detection.

    Args:
        keypoints_list: list of per-frame keypoint dicts from extractor.py
        sigma:          Gaussian filter standard deviation in frames.
                        Higher = smoother but more lag. Default 1.5 works
                        well for 30-60 fps footage.

    Returns:
        Smoothed keypoint list in the same format as the input.
    """
    if not keypoints_list:
        return keypoints_list

    n_frames = len(keypoints_list)

    # Collect every landmark name that appears in any frame
    all_landmarks: set[str] = set()
    for kp in keypoints_list:
        all_landmarks.update(kp.keys())

    smoothed: list[dict] = [{} for _ in range(n_frames)]

    for lm_name in all_landmarks:
        # Build per-coordinate time series; NaN where the landmark is absent
        xs = np.full(n_frames, np.nan)
        ys = np.full(n_frames, np.nan)
        zs = np.full(n_frames, np.nan)
        vs = np.full(n_frames, np.nan)  # visibility kept as-is

        for i, kp in enumerate(keypoints_list):
            if lm_name in kp:
                xs[i] = kp[lm_name]['x']
                ys[i] = kp[lm_name]['y']
                zs[i] = kp[lm_name]['z']
                vs[i] = kp[lm_name]['visibility']

        present = ~np.isnan(xs)
        if not np.any(present):
            continue

        # Need at least 2 detected frames to smooth meaningfully
        present_indices = np.where(present)[0]
        if len(present_indices) < 2:
            # Single frame: write back as-is
            i = present_indices[0]
            smoothed[i][lm_name] = {
                'x': float(xs[i]), 'y': float(ys[i]),
                'z': float(zs[i]), 'visibility': float(vs[i]),
            }
            continue

        # Fill NaN gaps with linear interpolation so the Gaussian filter
        # doesn't propagate NaNs across detection boundaries
        all_indices = np.arange(n_frames)
        for arr in (xs, ys, zs):
            arr[~present] = np.interp(
                all_indices[~present], present_indices, arr[present]
            )

        # Apply Gaussian smoothing to the full (gap-filled) time series
        xs_s = gaussian_filter1d(xs, sigma=sigma)
        ys_s = gaussian_filter1d(ys, sigma=sigma)
        zs_s = gaussian_filter1d(zs, sigma=sigma)

        # Write back only to originally-detected frames
        for i in present_indices:
            smoothed[i][lm_name] = {
                'x':          float(xs_s[i]),
                'y':          float(ys_s[i]),
                'z':          float(zs_s[i]),
                'visibility': float(vs[i]),
            }

    return smoothed
