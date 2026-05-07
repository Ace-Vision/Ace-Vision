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

import numpy as np

# Maps each sport to its nested baseline file.
BASELINES_MAP = {
    "tennis_serve": "data/reference/tennis_baselines.json",
    "badminton":    "data/reference/badminton_baselines.json",
}


# ── Checkpoint detection helpers ────────────────────────────────────────────

VISIBILITY_THRESHOLD = 0.5  # MediaPipe landmarks below this are unreliable
_SMOOTH_WINDOW = 5           # rolling-median window for extremum detection


def _rolling_median_extremum(
    indices: list[int],
    values: list[float],
    find_min: bool,
    window: int = _SMOOTH_WINDOW,
) -> int | None:
    """
    Find the frame index of the extremum (min or max) of a metric time series,
    using a rolling median to suppress single-frame spikes before searching.

    Args:
        indices: frame indices corresponding to `values`
        values:  metric values at each valid frame
        find_min: True to find the minimum, False to find the maximum
        window:   rolling-median half-width (total window = 2*window+1)

    Returns:
        Frame index of the (smoothed) extremum, or None if series is empty.
    """
    if not indices:
        return None

    arr = np.array(values, dtype=float)
    n = len(arr)

    # Apply rolling median (reflect-pad to keep edge frames)
    smoothed = np.empty(n)
    for k in range(n):
        lo = max(0, k - window)
        hi = min(n, k + window + 1)
        smoothed[k] = np.median(arr[lo:hi])

    best_k = int(np.argmin(smoothed) if find_min else np.argmax(smoothed))
    return indices[best_k]


def _is_visible(kp: dict, *landmark_names: str) -> bool:
    """Return True only if all named landmarks exist and meet the visibility threshold."""
    return all(
        name in kp and kp[name].get('visibility', 0) >= VISIBILITY_THRESHOLD
        for name in landmark_names
    )


def _find_trophy_frame(keypoints_list: list[dict]) -> int | None:
    """
    Find the frame where the right wrist is highest (trophy position).

    In MediaPipe normalized coords, y=0 is the TOP of the frame.
    Highest wrist = smallest right_wrist y. Uses a rolling median before
    finding the minimum so single-frame spikes don't hijack the result.
    """
    idxs, vals = [], []
    for i, kp in enumerate(keypoints_list):
        if kp and _is_visible(kp, 'right_wrist', 'right_elbow'):
            idxs.append(i)
            vals.append(kp['right_wrist']['y'])
    return _rolling_median_extremum(idxs, vals, find_min=True)


def _find_racket_drop_frame(keypoints_list: list[dict], after_frame: int) -> int | None:
    """
    Find the frame where the right wrist is lowest (racket drop), after trophy.

    Lowest wrist = largest right_wrist y. Only searches frames after `after_frame`.
    Uses a rolling median to suppress spike frames before finding the maximum.
    """
    idxs, vals = [], []
    for i, kp in enumerate(keypoints_list):
        if i <= after_frame:
            continue
        if kp and _is_visible(kp, 'right_wrist', 'right_elbow'):
            idxs.append(i)
            vals.append(kp['right_wrist']['y'])
    return _rolling_median_extremum(idxs, vals, find_min=False)


def _find_contact_frame(angles_list: list[dict], after_frame: int, keypoints_list: list[dict] | None = None) -> int | None:
    """
    Find the frame of ball contact (max right elbow extension), after racket drop.

    At contact the arm is fully extended, so right_elbow_flexion peaks.
    Uses a rolling median on the elbow angle series before finding the maximum.
    """
    idxs, vals = [], []
    for i, angles in enumerate(angles_list):
        if i <= after_frame:
            continue
        if keypoints_list and i < len(keypoints_list):
            kp = keypoints_list[i]
            if not kp or not _is_visible(kp, 'right_elbow', 'right_shoulder', 'right_wrist'):
                continue
        if angles and angles.get('right_elbow_flexion') is not None:
            idxs.append(i)
            vals.append(angles['right_elbow_flexion'])
    return _rolling_median_extremum(idxs, vals, find_min=False)


# ── Badminton clear–specific detection ──────────────────────────────────────

def _find_clear_contact_frame(keypoints_list: list[dict]) -> int | None:
    """
    Find the contact frame for a badminton clear: the frame where the right
    wrist is at its highest point (minimum y in MediaPipe coords).

    For a clear the player reaches up to strike the shuttle at the top of
    their reach, so highest wrist == contact.
    """
    return _find_trophy_frame(keypoints_list)


def _find_backswing_frame(
    angles_list: list[dict],
    before_frame: int,
    keypoints_list: list[dict] | None = None,
) -> int | None:
    """
    Find the backswing (loading) frame for a badminton clear.

    Searches the 120 frames before contact for the minimum right_elbow_flexion
    (most bent elbow = arm fully cocked). Uses rolling median before searching.
    """
    search_start = max(0, before_frame - 120)
    idxs, vals = [], []
    for i in range(search_start, before_frame):
        if keypoints_list and i < len(keypoints_list):
            kp = keypoints_list[i]
            if not kp or not _is_visible(kp, 'right_elbow', 'right_shoulder', 'right_wrist'):
                continue
        angles = angles_list[i] if i < len(angles_list) else {}
        if angles and angles.get('right_elbow_flexion') is not None:
            idxs.append(i)
            vals.append(angles['right_elbow_flexion'])
    return _rolling_median_extremum(idxs, vals, find_min=True)


def _find_follow_through_frame(
    keypoints_list: list[dict],
    after_frame: int,
) -> int | None:
    """
    Find the follow-through frame for a badminton clear.

    After contact the racket arm swings down. Finds the lowest wrist position
    (maximum y) after contact, using rolling median for spike robustness.
    """
    return _find_racket_drop_frame(keypoints_list, after_frame=after_frame)


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

    # ── 2. Detect checkpoints (sport-specific) ──────────────────────────────
    kp_list = keypoints_list or []

    def score_checkpoint(frame_idx, checkpoint_name):
        """Score one checkpoint frame against the given baseline key."""
        if frame_idx is None:
            return None
        frame_angles = angles_list[frame_idx] if frame_idx < len(angles_list) else {}
        deviations   = _score_one_frame(frame_angles, baselines[checkpoint_name])
        return {"frame": frame_idx, "deviations": deviations}

    if sport_type == "badminton":
        # ── Badminton clear checkpoints ──────────────────────────────────────
        # Order: contact is detected first (highest wrist = hit moment),
        # then backswing is found before it, follow_through after it.
        contact_frame       = _find_clear_contact_frame(kp_list)
        backswing_frame     = _find_backswing_frame(
            angles_list, before_frame=contact_frame or 0, keypoints_list=kp_list
        )
        follow_through_frame = _find_follow_through_frame(
            kp_list, after_frame=contact_frame or 0
        )

        checkpoints = {
            "backswing":      score_checkpoint(backswing_frame,      "backswing"),
            "contact":        score_checkpoint(contact_frame,        "contact"),
            "follow_through": score_checkpoint(follow_through_frame, "follow_through"),
        }
        primary_deviations = (
            checkpoints["contact"]["deviations"]
            if checkpoints["contact"] is not None else {}
        )

    else:
        # ── Tennis serve checkpoints (unchanged) ─────────────────────────────
        trophy_frame      = _find_trophy_frame(kp_list)
        racket_drop_frame = _find_racket_drop_frame(kp_list, after_frame=trophy_frame or 0)
        contact_frame     = _find_contact_frame(
            angles_list, after_frame=racket_drop_frame or 0, keypoints_list=kp_list
        )

        checkpoints = {
            "trophy":      score_checkpoint(trophy_frame,      "trophy"),
            "racket_drop": score_checkpoint(racket_drop_frame, "racket_drop"),
            "contact":     score_checkpoint(contact_frame,     "contact"),
        }
        primary_deviations = (
            checkpoints["contact"]["deviations"]
            if checkpoints["contact"] is not None else {}
        )

    # ── 3. Flat "deviations" key for renderer.py ────────────────────────────
    # renderer.py reads deviation_scores["deviations"] directly (contact frame).

    return {
        "checkpoints":        checkpoints,
        "deviations":         primary_deviations,
        "hip_leads_shoulder": False,  # placeholder — timing check not yet implemented
        "baseline_source":    os.path.relpath(baselines_path, repo_root),
    }
