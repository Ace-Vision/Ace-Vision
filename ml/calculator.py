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

        # Trunk lateral tilt: angle between the trunk vector (hip-midpoint → shoulder-midpoint)
        # and the vertical axis (0, -1) in the image plane.
        # Using only x/y since z adds noise from MediaPipe's depth estimation.
        ls, rs = get_point('left_shoulder'), get_point('right_shoulder')
        lh, rh = get_point('left_hip'),      get_point('right_hip')
        if ls is not None and rs is not None and lh is not None and rh is not None:
            shoulder_mid = (ls[:2] + rs[:2]) / 2
            hip_mid      = (lh[:2] + rh[:2]) / 2
            trunk_vec    = shoulder_mid - hip_mid          # points upward in image coords (y flipped)
            vertical     = np.array([0.0, -1.0])           # up in image coords
            mag = np.linalg.norm(trunk_vec)
            if mag > 0:
                cos_t = np.clip(np.dot(trunk_vec / mag, vertical), -1, 1)
                angles['trunk_lateral_tilt'] = math.degrees(math.acos(cos_t))
            else:
                angles['trunk_lateral_tilt'] = None
        else:
            angles['trunk_lateral_tilt'] = None

        # Hip-shoulder separation: angle between the hip axis and the shoulder axis,
        # both measured as 2-D vectors across the frame.
        # A value of 0° means hips and shoulders face the same direction;
        # larger values indicate more rotation between the two segments.
        if ls is not None and rs is not None and lh is not None and rh is not None:
            shoulder_axis = rs[:2] - ls[:2]
            hip_axis      = rh[:2] - lh[:2]
            mag_s = np.linalg.norm(shoulder_axis)
            mag_h = np.linalg.norm(hip_axis)
            if mag_s > 0 and mag_h > 0:
                cos_t = np.clip(
                    np.dot(shoulder_axis / mag_s, hip_axis / mag_h), -1, 1
                )
                angles['hip_shoulder_separation'] = math.degrees(math.acos(cos_t))
            else:
                angles['hip_shoulder_separation'] = None
        else:
            angles['hip_shoulder_separation'] = None

        # Wrist extension: right_elbow, right_wrist, right_index (or middle finger)
        # Assuming right_wrist extension
        angles['wrist_extension'] = calc_angle(
            get_point('right_elbow'), get_point('right_wrist'), get_point('right_index')
        )

        angles_list.append(angles)

    return angles_list
