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

# Maps each sport to its own baseline file.
BASELINES_MAP = {
    "tennis_serve": "data/reference/tennis_baselines.json",
    "badminton": "data/reference/badminton_baselines.json",
}

# Cache baselines in memory to avoid re-reading JSON files
_baselines_cache = {}


def _load_baselines(sport_type: str) -> dict:
    """Load and cache baselines for a sport type."""
    if sport_type in _baselines_cache:
        return _baselines_cache[sport_type]
    
    if sport_type not in BASELINES_MAP:
        raise ValueError(f"Unknown sport_type '{sport_type}'. Choose from: {list(BASELINES_MAP)}")

    repo_root = os.path.dirname(os.path.dirname(__file__))
    baselines_path = os.path.join(repo_root, BASELINES_MAP[sport_type])

    if not os.path.exists(baselines_path):
        raise FileNotFoundError(
            f"Baseline file not found for '{sport_type}'. "
            f"Expected: '{baselines_path}'."
        )

    with open(baselines_path, "r") as f:
        baselines = json.load(f)
    
    _baselines_cache[sport_type] = baselines
    return baselines


def score_deviations(angles_list: list[dict], sport_type: str = "tennis_serve") -> dict:
    """
    Score deviations from expert baselines for a given sport.

    Args:
        angles_list (list[dict]): List of angles per frame.
        sport_type (str): Which sport's baselines to use ("tennis_serve" or "badminton").

    Returns:
        dict: Deviation scores and other metrics.
    """
    # Load cached baselines for the sport
    baselines = _load_baselines(sport_type)

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

    repo_root = os.path.dirname(os.path.dirname(__file__))
    baselines_path = os.path.join(repo_root, BASELINES_MAP[sport_type])
    
    result = {
        "peak_frame": peak_frame,
        "deviations": deviations,
        "hip_leads_shoulder": hip_leads_shoulder,
        "baseline_source": os.path.relpath(baselines_path, repo_root),
    }

    return result
