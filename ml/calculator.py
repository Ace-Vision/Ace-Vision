"""
ml/calculator.py — Joint angle computation.

Computes angles at the 9 serve-specific joints using the arccos dot-product
formula: θ = arccos(dot(v1, v2) / (|v1| × |v2|)), where v1 and v2 point
away from the vertex joint.

Joints analysed:
- Right/left elbow flexion
- Right/left shoulder abduction
- Right/left knee flexion
- Trunk lateral tilt
- Hip-shoulder separation
- Wrist extension

Key responsibilities:
- Accept normalised keypoint data per frame
- For each joint, extract the three relevant keypoints (two limb endpoints + vertex)
- Compute the angle at the vertex using the vector dot-product formula
- Return per-frame angle dict for all 9 joints
"""

import math
import numpy as np


def calculate_angles(keypoints_list: list[dict]) -> list[dict]:
    """
    Calculate joint angles from keypoints for each frame.

    Args:
        keypoints_list (list[dict]): List of keypoints per frame.

    Returns:
        list[dict]: List of angle dicts per frame.
    """
    angles_list = []

    for kp in keypoints_list:
        angles = {}

        if not kp:
            angles_list.append({})
            continue

        # Helper function to get point
        def get_point(name):
            if name in kp:
                return np.array([kp[name]['x'], kp[name]['y'], kp[name]['z']])
            return None

        # Helper function to calculate angle
        def calc_angle(p1, vertex, p2):
            if p1 is None or vertex is None or p2 is None:
                return None
            v1 = p1 - vertex
            v2 = p2 - vertex
            dot = np.dot(v1, v2)
            mag1 = np.linalg.norm(v1)
            mag2 = np.linalg.norm(v2)
            if mag1 == 0 or mag2 == 0:
                return None
            cos_theta = dot / (mag1 * mag2)
            cos_theta = np.clip(cos_theta, -1, 1)
            return math.degrees(math.acos(cos_theta))

        # Right elbow flexion: right_shoulder, right_elbow, right_wrist
        angles['right_elbow_flexion'] = calc_angle(
            get_point('right_shoulder'), get_point('right_elbow'), get_point('right_wrist')
        )

        # Left elbow flexion: left_shoulder, left_elbow, left_wrist
        angles['left_elbow_flexion'] = calc_angle(
            get_point('left_shoulder'), get_point('left_elbow'), get_point('left_wrist')
        )

        # Right shoulder abduction: right_hip, right_shoulder, right_elbow
        angles['right_shoulder_abduction'] = calc_angle(
            get_point('right_hip'), get_point('right_shoulder'), get_point('right_elbow')
        )

        # Left shoulder abduction: left_hip, left_shoulder, left_elbow
        angles['left_shoulder_abduction'] = calc_angle(
            get_point('left_hip'), get_point('left_shoulder'), get_point('left_elbow')
        )

        # Right knee flexion: right_hip, right_knee, right_ankle
        angles['right_knee_flexion'] = calc_angle(
            get_point('right_hip'), get_point('right_knee'), get_point('right_ankle')
        )

        # Left knee flexion: left_hip, left_knee, left_ankle
        angles['left_knee_flexion'] = calc_angle(
            get_point('left_hip'), get_point('left_knee'), get_point('left_ankle')
        )

        # Trunk lateral tilt: left_hip, nose, right_hip (or similar)
        # Assuming trunk tilt as angle at nose between left_hip and right_hip
        angles['trunk_lateral_tilt'] = calc_angle(
            get_point('left_hip'), get_point('nose'), get_point('right_hip')
        )

        # Hip-shoulder separation: left_hip, left_shoulder, right_shoulder
        # Angle at left_shoulder between left_hip and right_shoulder
        angles['hip_shoulder_separation'] = calc_angle(
            get_point('left_hip'), get_point('left_shoulder'), get_point('right_shoulder')
        )

        # Wrist extension: right_elbow, right_wrist, right_index (or middle finger)
        # Assuming right_wrist extension
        angles['wrist_extension'] = calc_angle(
            get_point('right_elbow'), get_point('right_wrist'), get_point('right_index')
        )

        angles_list.append(angles)

    return angles_list
