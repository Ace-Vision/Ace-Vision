"""
ml/scorer.py — Deviation scoring against expert baselines.

Compares the player's joint angles at three key checkpoints in the serve
to expert baseline distributions and computes a severity score for each joint.

The three checkpoints:
  trophy      — arm fully raised, racket up (highest wrist point)
  racket_drop — racket drops behind the back (lowest wrist point)
  contact     — ball strike (maximum elbow extension)

Formulas (same for all checkpoints):
  deviation_deg  = abs(player_angle - expert_mean)
  severity_score = min(deviation_deg / (2 * expert_std), 1.0)
  direction      = "too_high" if player_angle > expert_mean else "too_low"
"""

import json
import os

# Maps each sport to its nested baseline file.
BASELINES_MAP = {
    "tennis_serve": "data/reference/tennis_baselines.json",
    "badminton":    "data/reference/badminton_baselines.json",
}


# ── Checkpoint detection helpers ────────────────────────────────────────────

def _find_trophy_frame(keypoints_list: list[dict]) -> int | None:
    """
    Find the frame where the right wrist is highest (trophy position).

    In MediaPipe normalized coords, y=0 is the TOP of the frame.
    So the highest wrist = the frame with the SMALLEST right_wrist y value.

    Args:
        keypoints_list: per-frame keypoint dicts from extractor.py

    Returns:
        Frame index, or None if right_wrist is never visible.
    """
    best_frame = None
    best_y = float('inf')   # we want the smallest y

    for i, kp in enumerate(keypoints_list):
        if kp and 'right_wrist' in kp:
            y = kp['right_wrist']['y']
            if y < best_y:
                best_y = y
                best_frame = i

    return best_frame


def _find_racket_drop_frame(keypoints_list: list[dict], after_frame: int) -> int | None:
    """
    Find the frame where the right wrist is lowest (racket drop), after trophy.

    The lowest wrist = the frame with the LARGEST right_wrist y value.
    We only search frames that come after the trophy frame so we don't
    accidentally pick a frame from earlier in the video.

    Args:
        keypoints_list: per-frame keypoint dicts from extractor.py
        after_frame:    only look at frames with index > after_frame

    Returns:
        Frame index, or None if right_wrist is never visible after trophy.
    """
    best_frame = None
    best_y = float('-inf')  # we want the largest y

    for i, kp in enumerate(keypoints_list):
        if i <= after_frame:
            continue  # skip everything before (and including) the trophy frame
        if kp and 'right_wrist' in kp:
            y = kp['right_wrist']['y']
            if y > best_y:
                best_y = y
                best_frame = i

    return best_frame


def _find_contact_frame(angles_list: list[dict], after_frame: int) -> int | None:
    """
    Find the frame of ball contact (max right elbow extension), after racket drop.

    At contact, the arm is fully extended so right_elbow_flexion is at its peak.
    We only search frames after the racket drop to avoid false positives.

    Args:
        angles_list:  per-frame angle dicts from calculator.py
        after_frame:  only look at frames with index > after_frame

    Returns:
        Frame index, or None if no valid elbow angle is found after racket drop.
    """
    best_frame = None
    best_angle = 0.0

    for i, angles in enumerate(angles_list):
        if i <= after_frame:
            continue  # skip everything before (and including) the racket drop frame
        if angles and 'right_elbow_flexion' in angles:
            angle = angles['right_elbow_flexion']
            if angle is not None and angle > best_angle:
                best_angle = angle
                best_frame = i

    return best_frame


# ── Single-frame scorer ──────────────────────────────────────────────────────

def _score_one_frame(frame_angles: dict, checkpoint_baselines: dict) -> dict:
    """
    Score one frame's joint angles against one checkpoint's expert baselines.

    For each joint that exists in both the frame and the baselines:
      deviation_deg  = abs(player_angle - expert_mean)
      severity_score = min(deviation_deg / (2 * expert_std), 1.0)
      direction      = "too_high" or "too_low"

    Args:
        frame_angles:         angle dict for one frame (from calculator.py)
        checkpoint_baselines: the sub-dict for one checkpoint, e.g. baselines["trophy"]

    Returns:
        dict: { joint_name: { angle, deviation_deg, severity_score, direction } }
    """
    deviations = {}

    for joint, angle in frame_angles.items():
        # Skip joints with no angle (MediaPipe couldn't see that keypoint)
        if angle is None:
            continue
        # Skip joints we don't have a baseline for
        if joint not in checkpoint_baselines:
            continue

        expert = checkpoint_baselines[joint]
        deviation_deg  = abs(angle - expert['mean'])
        severity_score = min(deviation_deg / (2 * expert['std']), 1.0)
        direction      = "too_high" if angle > expert['mean'] else "too_low"

        deviations[joint] = {
            "angle":         angle,
            "deviation_deg": deviation_deg,
            "severity_score": severity_score,
            "direction":     direction,
        }

    return deviations


# ── Main public function ─────────────────────────────────────────────────────

def score_deviations(
    angles_list: list[dict],
    sport_type: str = "tennis_serve",
    keypoints_list: list[dict] | None = None,
) -> dict:
    """
    Detect the three serve checkpoints and score each one against expert baselines.

    Args:
        angles_list:    per-frame angle dicts from calculator.py
        sport_type:     "tennis_serve" or "badminton"
        keypoints_list: per-frame keypoint dicts from extractor.py
                        (needed for trophy + racket_drop detection)

    Returns:
        dict with shape:
        {
          "checkpoints": {
            "trophy":      { "frame": int, "deviations": { joint: {...} } } or None,
            "racket_drop": { "frame": int, "deviations": { joint: {...} } } or None,
            "contact":     { "frame": int, "deviations": { joint: {...} } } or None,
          },
          "deviations":        { joint: {...} },  # contact deviations (for renderer)
          "hip_leads_shoulder": bool,
          "baseline_source":    str,
        }
    """
    # ── 1. Load the nested baseline file ────────────────────────────────────
    if sport_type not in BASELINES_MAP:
        raise ValueError(
            f"Unknown sport_type '{sport_type}'. Choose from: {list(BASELINES_MAP)}"
        )

    repo_root      = os.path.dirname(os.path.dirname(__file__))
    baselines_path = os.path.join(repo_root, BASELINES_MAP[sport_type])

    if not os.path.exists(baselines_path):
        raise FileNotFoundError(
            f"Baseline file not found for '{sport_type}'. Expected: '{baselines_path}'"
        )

    with open(baselines_path, "r") as f:
        baselines = json.load(f)

    # ── 2. Detect the three checkpoints in order ─────────────────────────────
    # Each checkpoint must happen AFTER the previous one.
    # If detection fails, we pass after_frame=0 so the next step still runs.

    kp_list = keypoints_list or []

    trophy_frame      = _find_trophy_frame(kp_list)
    racket_drop_frame = _find_racket_drop_frame(kp_list, after_frame=trophy_frame or 0)
    contact_frame     = _find_contact_frame(angles_list, after_frame=racket_drop_frame or 0)

    # ── 3. Score each detected checkpoint ────────────────────────────────────
    def score_checkpoint(frame_idx, checkpoint_name):
        """Helper: score a single checkpoint, return None if not detected."""
        if frame_idx is None:
            return None
        frame_angles = angles_list[frame_idx] if frame_idx < len(angles_list) else {}
        deviations   = _score_one_frame(frame_angles, baselines[checkpoint_name])
        return {
            "frame":      frame_idx,
            "deviations": deviations,
        }

    checkpoints = {
        "trophy":      score_checkpoint(trophy_frame,      "trophy"),
        "racket_drop": score_checkpoint(racket_drop_frame, "racket_drop"),
        "contact":     score_checkpoint(contact_frame,     "contact"),
    }

    # ── 4. Backward-compat: flat "deviations" key for renderer.py ────────────
    # renderer.py reads deviation_scores["deviations"] directly.
    # We give it the contact checkpoint deviations so the overlay video
    # keeps working without any changes to renderer.py.
    contact_deviations = (
        checkpoints["contact"]["deviations"]
        if checkpoints["contact"] is not None
        else {}
    )

    return {
        "checkpoints":        checkpoints,
        "deviations":         contact_deviations,
        "hip_leads_shoulder": False,  # placeholder — timing check not yet implemented
        "baseline_source":    os.path.relpath(baselines_path, repo_root),
    }
