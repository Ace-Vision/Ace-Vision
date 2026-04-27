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


# Pre-compute joint-to-keypoint mappings to avoid rebuilding every frame
JOINT_KEYPOINTS = {
    'right_elbow_flexion': ('right_shoulder', 'right_elbow', 'right_wrist'),
    'left_elbow_flexion': ('left_shoulder', 'left_elbow', 'left_wrist'),
    'right_shoulder_abduction': ('right_hip', 'right_shoulder', 'right_elbow'),
    'left_shoulder_abduction': ('left_hip', 'left_shoulder', 'left_elbow'),
    'right_knee_flexion': ('right_hip', 'right_knee', 'right_ankle'),
    'left_knee_flexion': ('left_hip', 'left_knee', 'left_ankle'),
    'trunk_lateral_tilt': ('left_hip', 'nose', 'right_hip'),
    'hip_shoulder_separation': ('left_hip', 'left_shoulder', 'right_shoulder'),
    'wrist_extension': ('right_elbow', 'right_wrist', 'right_index'),
}


def _get_point(keypoints: dict, name: str) -> np.ndarray | None:
    """Get a single keypoint as a numpy array, or None if missing."""
    if name in keypoints:
        kp = keypoints[name]
        return np.array([kp['x'], kp['y'], kp['z']], dtype=np.float32)
    return None


def _calc_angle(p1: np.ndarray, vertex: np.ndarray, p2: np.ndarray) -> float | None:
    """
    Calculate angle at vertex between vectors to p1 and p2.
    Uses dot-product formula: θ = arccos(dot(v1, v2) / (|v1| × |v2|))
    """
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

        # Use pre-computed joint mapping to avoid rebuilding
        for joint, (p1_name, vertex_name, p2_name) in JOINT_KEYPOINTS.items():
            p1 = _get_point(kp, p1_name)
            vertex = _get_point(kp, vertex_name)
            p2 = _get_point(kp, p2_name)
            angles[joint] = _calc_angle(p1, vertex, p2)

        angles_list.append(angles)

    return angles_list
