"""
ml/smoother.py — Gaussian smoothing on keypoint time series.

Applies a 1-D Gaussian filter (scipy.ndimage.gaussian_filter1d) to each
keypoint coordinate across frames to reduce jitter from MediaPipe detection
noise.
"""

from scipy.ndimage import gaussian_filter1d
import numpy as np


_COORDS = ("x", "y", "z")


def smooth_keypoints(keypoints_list: list[dict], sigma: float = 2.0) -> list[dict]:
    """
    Smooth per-frame keypoints with a 1-D Gaussian filter along the time axis.

    Only landmarks that are present for the full run of consecutive non-empty
    frames are smoothed. Isolated empty frames (no detection) are left as-is.
    The output list has the same length and structure as the input.

    Args:
        keypoints_list: Raw per-frame keypoint dicts from extractor.py.
        sigma:          Standard deviation for the Gaussian kernel (frames).
                        Larger = smoother but more lag. Default 2.0 works well
                        at 30 fps; increase to 3–4 for very noisy footage.

    Returns:
        Smoothed keypoints list in the same format as the input.
    """
    if not keypoints_list:
        return keypoints_list

    # Collect all landmark names seen across the video
    landmark_names = set()
    for kp in keypoints_list:
        landmark_names.update(kp.keys())

    n_frames = len(keypoints_list)
    result = [dict(frame) for frame in keypoints_list]  # shallow-copy each frame

    for name in landmark_names:
        for coord in _COORDS:
            # Build a time series; use NaN where the landmark is missing
            series = np.array([
                kp[name][coord] if name in kp else np.nan
                for kp in keypoints_list
            ], dtype=float)

            # Find contiguous runs of valid (non-NaN) values and smooth each
            valid_mask = ~np.isnan(series)
            if not valid_mask.any():
                continue

            smoothed = _smooth_valid_runs(series, valid_mask, sigma)

            # Write smoothed values back (only where the landmark existed)
            for i in range(n_frames):
                if name in result[i]:
                    result[i][name] = dict(result[i][name])  # don't mutate original
                    result[i][name][coord] = float(smoothed[i])

    return result


def _smooth_valid_runs(series: np.ndarray, valid_mask: np.ndarray, sigma: float) -> np.ndarray:
    """
    Smooth the valid (non-NaN) runs of `series` in place, leaving NaN gaps unchanged.

    Runs are smoothed independently so that a gap (missing detection) does not
    bleed its NaN into neighbouring valid frames.
    """
    out = series.copy()

    # Find contiguous valid segments
    padded = np.concatenate(([False], valid_mask, [False]))
    starts = np.where(~padded[:-1] & padded[1:])[0]
    ends   = np.where(padded[:-1] & ~padded[1:])[0]

    for s, e in zip(starts, ends):
        segment = series[s:e]
        if len(segment) >= 3:  # too short to benefit from smoothing
            out[s:e] = gaussian_filter1d(segment, sigma=sigma)

    return out
