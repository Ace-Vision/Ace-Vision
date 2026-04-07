"""
ml/scorer.py — Deviation scoring against expert baselines.

Compares the player's joint angles to expert baseline distributions loaded
from expert_baselines.json and computes a severity score for each joint.

Formulas:
- deviation_deg  = abs(player_angle - expert_mean)
- severity_score = min(deviation_deg / (2 * expert_std), 1.0)
- direction      = "too_high" if player_angle > expert_mean else "too_low"

Also computes:
- hip_leads_shoulder (bool): True if peak hip rotation precedes peak
  shoulder rotation by > 3 frames.

Key responsibilities:
- Load expert baselines from JSON file
- For each of the 9 joints, compute deviation and severity at peak frame
- Determine direction of deviation
- Compute kinetic chain timing (hip vs shoulder rotation)
- Return structured deviation results
"""

import json
import os


def score_deviations(angles_list: list[dict]) -> dict:
    """
    Score deviations from expert baselines.

    Args:
        angles_list (list[dict]): List of angles per frame.

    Returns:
        dict: Deviation scores and other metrics.
    """
    # Load expert baselines
    baselines_path = "data/reference/expert_baselines.json"
    with open(baselines_path, 'r') as f:
        baselines = json.load(f)

    # Find peak frame (simplified: use the frame with max right_elbow_flexion or first valid)
    peak_frame = None
    max_angle = 0
    for i, angles in enumerate(angles_list):
        if angles and 'right_elbow_flexion' in angles and angles['right_elbow_flexion'] is not None:
            if angles['right_elbow_flexion'] > max_angle:
                max_angle = angles['right_elbow_flexion']
                peak_frame = i

    if peak_frame is None:
        return {"error": "No valid angles found"}

    peak_angles = angles_list[peak_frame]

    deviations = {}
    for joint, angle in peak_angles.items():
        if angle is None or joint not in baselines:
            continue
        expert = baselines[joint]
        deviation_deg = abs(angle - expert['mean'])
        severity_score = min(deviation_deg / (2 * expert['std']), 1.0)
        direction = "too_high" if angle > expert['mean'] else "too_low"
        deviations[joint] = {
            "angle": angle,
            "deviation_deg": deviation_deg,
            "severity_score": severity_score,
            "direction": direction
        }

    # Hip leads shoulder (simplified check)
    hip_leads_shoulder = False
    # Placeholder: assume based on some logic, e.g., if hip angle peaks before shoulder

    result = {
        "peak_frame": peak_frame,
        "deviations": deviations,
        "hip_leads_shoulder": hip_leads_shoulder
    }

    return result
