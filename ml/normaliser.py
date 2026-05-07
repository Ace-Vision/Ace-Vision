"""
ml/normaliser.py — Hip-centred, scale-free normalisation.

Translates all keypoints so the midpoint of the left and right hips is the
origin, then scales by torso length (hip-midpoint to shoulder-midpoint) so
that players of different sizes and camera distances produce comparable
coordinates.
"""

import numpy as np

_LEFT_HIP   = "left_hip"
_RIGHT_HIP  = "right_hip"
_LEFT_SHOULDER  = "left_shoulder"
_RIGHT_SHOULDER = "right_shoulder"
_REQUIRED = (_LEFT_HIP, _RIGHT_HIP, _LEFT_SHOULDER, _RIGHT_SHOULDER)


def normalise_keypoints(keypoints_list: list[dict]) -> list[dict]:
    """
    Apply hip-centred, torso-length normalisation to each frame.

    For each frame where all four anchor points (both hips, both shoulders)
    are visible:
      1. Compute hip midpoint → new origin.
      2. Compute torso length = distance(hip_mid, shoulder_mid).
      3. Translate all landmarks by -hip_mid, then divide x/y/z by torso_length.

    Frames where the anchor points are missing are returned unchanged so
    downstream code can still fall back to raw coordinates.

    Args:
        keypoints_list: Per-frame keypoint dicts (from smoother or extractor).

    Returns:
        Normalised keypoints in the same format.
    """
    result = []
    for kp in keypoints_list:
        if not kp or not all(name in kp for name in _REQUIRED):
            result.append(kp)
            continue

        lh = np.array([kp[_LEFT_HIP]["x"],  kp[_LEFT_HIP]["y"],  kp[_LEFT_HIP]["z"]])
        rh = np.array([kp[_RIGHT_HIP]["x"], kp[_RIGHT_HIP]["y"], kp[_RIGHT_HIP]["z"]])
        ls = np.array([kp[_LEFT_SHOULDER]["x"],  kp[_LEFT_SHOULDER]["y"],  kp[_LEFT_SHOULDER]["z"]])
        rs = np.array([kp[_RIGHT_SHOULDER]["x"], kp[_RIGHT_SHOULDER]["y"], kp[_RIGHT_SHOULDER]["z"]])

        hip_mid      = (lh + rh) / 2.0
        shoulder_mid = (ls + rs) / 2.0
        torso_length = float(np.linalg.norm(shoulder_mid - hip_mid))

        if torso_length < 1e-6:
            result.append(kp)
            continue

        norm_frame = {}
        for name, data in kp.items():
            raw = np.array([data["x"], data["y"], data["z"]])
            translated = raw - hip_mid
            scaled     = translated / torso_length
            norm_frame[name] = {
                "x":          float(scaled[0]),
                "y":          float(scaled[1]),
                "z":          float(scaled[2]),
                "visibility": data["visibility"],
            }
        result.append(norm_frame)

    return result
