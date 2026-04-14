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
