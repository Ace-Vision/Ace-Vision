"""
ml/normaliser.py — Hip-centred, scale-free normalisation.

Translates all keypoints so the midpoint of the left and right hips is the
origin, then scales by torso length (hip-midpoint to shoulder-midpoint) so
that players of different sizes produce comparable coordinates.
"""

import copy
import numpy as np

def normalise_keypoints(keypoints_list: list[dict]) -> list[dict]:
    """
    Normalises keypoints by centering on the hip midpoint and scaling by torso length.
    """
    if not keypoints_list:
        return []

    normalised = [copy.deepcopy(kp) if kp else {} for kp in keypoints_list]

    for kp in normalised:
        if not kp:
            continue

        # Check for required joints
        required = ['left_hip', 'right_hip', 'left_shoulder', 'right_shoulder']
        if not all(j in kp for j in required):
            continue

        lh = np.array([kp['left_hip']['x'], kp['left_hip']['y'], kp['left_hip']['z']])
        rh = np.array([kp['right_hip']['x'], kp['right_hip']['y'], kp['right_hip']['z']])
        ls = np.array([kp['left_shoulder']['x'], kp['left_shoulder']['y'], kp['left_shoulder']['z']])
        rs = np.array([kp['right_shoulder']['x'], kp['right_shoulder']['y'], kp['right_shoulder']['z']])

        hip_mid = (lh + rh) / 2.0
        shoulder_mid = (ls + rs) / 2.0

        torso_vec = shoulder_mid - hip_mid
        torso_length = np.linalg.norm(torso_vec)

        if torso_length == 0:
            continue

        # Normalise all keypoints in this frame
        for name, data in kp.items():
            pt = np.array([data['x'], data['y'], data['z']])
            
            # Translate and scale
            pt_norm = (pt - hip_mid) / torso_length
            
            data['x'] = float(pt_norm[0])
            data['y'] = float(pt_norm[1])
            data['z'] = float(pt_norm[2])

    return normalised
