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


# ── Constants ────────────────────────────────────────────────────────────────

VISIBILITY_THRESHOLD = 0.5  # MediaPipe landmarks below this are unreliable
_SMOOTH_WINDOW = 5           # rolling-median half-width for extremum detection
_SWING_PAD_FRAMES = 45       # padding added each side of swing window (~1.5 s at 30 fps)


# ── Swing-window detection ───────────────────────────────────────────────────

_MERGE_GAP_SEC = 0.7   # runs separated by ≤ this many seconds are merged into one swing


def _find_swing_window(
    keypoints_list: list[dict],
    pad_frames: int = _SWING_PAD_FRAMES,
    fps: float = 30.0,
) -> tuple[int, int]:
    """
    Locate the frame range that contains the actual stroke motion.

    Strategy:
    1. Find frames where right_wrist_y < right_shoulder_y (wrist above shoulder).
    2. Merge nearby runs separated by ≤ 0.7 s into one — this handles players
       whose wrist briefly dips below the shoulder mid-swing, which would
       otherwise split a single swing into multiple fragments.  The threshold
       is expressed in seconds so it scales correctly with video frame-rate.
    3. Among merged runs, pick the one with the most extreme wrist elevation.
    4. Pad each side by `pad_frames`, but cap the end so padding never bleeds
       into a neighbouring merged run (which would be a different swing).

    Falls back to the full video if no arm-raised frames exist.

    Args:
        keypoints_list: per-frame keypoint dicts (normalised recommended).
        pad_frames:     frames added before/after the detected core window.
        fps:            video frame-rate, used to convert merge threshold to frames.

    Returns:
        (start_frame, end_frame) — inclusive bounds for checkpoint search.
    """
    n = len(keypoints_list)
    if n == 0:
        return 0, 0

    merge_gap = int(_MERGE_GAP_SEC * fps)

    # Build per-frame flags: True where wrist is visibly above shoulder.
    above = []
    wrist_y_series = []
    for kp in keypoints_list:
        if (kp
                and _is_visible(kp, 'right_wrist', 'right_shoulder')
                and kp['right_wrist']['y'] < kp['right_shoulder']['y']):
            above.append(True)
            wrist_y_series.append(kp['right_wrist']['y'])
        else:
            above.append(False)
            wrist_y_series.append(None)

    # Collect contiguous runs of True.
    raw_runs: list[tuple[int, int]] = []
    i = 0
    while i < n:
        if above[i]:
            j = i
            while j < n and above[j]:
                j += 1
            raw_runs.append((i, j - 1))
            i = j
        else:
            i += 1

    if not raw_runs:
        return 0, n - 1

    # Merge runs whose gap is ≤ merge_gap frames.
    merged: list[tuple[int, int]] = [raw_runs[0]]
    for start, end in raw_runs[1:]:
        prev_end = merged[-1][1]
        if start - prev_end - 1 <= merge_gap:
            merged[-1] = (merged[-1][0], end)
        else:
            merged.append((start, end))

    # For each merged run, find the best (lowest) wrist y within it.
    def best_y_in(start, end):
        ys = [wrist_y_series[k] for k in range(start, end + 1)
              if wrist_y_series[k] is not None]
        return min(ys) if ys else 0.0

    runs_with_y = [(s, e, best_y_in(s, e)) for s, e in merged]

    # Choose the run where the wrist reaches the highest point (min y).
    best_idx = int(np.argmin([r[2] for r in runs_with_y]))
    best_start, best_end, _ = runs_with_y[best_idx]

    # Pad, but never let the end bleed into the next merged run.
    win_start = max(0, best_start - pad_frames)
    if best_idx + 1 < len(runs_with_y):
        next_run_start = runs_with_y[best_idx + 1][0]
        win_end = min(best_end + pad_frames, next_run_start - 1)
    else:
        win_end = min(best_end + pad_frames, n - 1)

    return win_start, win_end


# ── Helpers ──────────────────────────────────────────────────────────────────

def _is_visible(kp: dict, *landmark_names: str) -> bool:
    """Return True only if all named landmarks exist and meet the visibility threshold."""
    return all(
        name in kp and kp[name].get('visibility', 0) >= VISIBILITY_THRESHOLD
        for name in landmark_names
    )


def _rolling_median_extremum(
    indices: list[int],
    values: list[float],
    find_min: bool,
    window: int = _SMOOTH_WINDOW,
) -> int | None:
    """
    Find the frame index of the extremum after rolling-median smoothing.

    The rolling median suppresses single-frame spikes so a lone noisy frame
    cannot become the selected checkpoint.
    """
    if not indices:
        return None

    arr = np.array(values, dtype=float)
    n = len(arr)

    smoothed = np.empty(n)
    for k in range(n):
        lo = max(0, k - window)
        hi = min(n, k + window + 1)
        smoothed[k] = np.median(arr[lo:hi])

    best_k = int(np.argmin(smoothed) if find_min else np.argmax(smoothed))
    return indices[best_k]


# ── Checkpoint detectors ─────────────────────────────────────────────────────
#
# All detectors now accept start_frame / end_frame bounds.
# When called from score_deviations, these are set to the swing window so
# only frames inside the actual stroke are considered.

def _find_trophy_frame(
    keypoints_list: list[dict],
    start_frame: int = 0,
    end_frame: int | None = None,
) -> int | None:
    """Highest right-wrist position (smallest y) within [start_frame, end_frame]."""
    if end_frame is None:
        end_frame = len(keypoints_list) - 1
    idxs, vals = [], []
    for i, kp in enumerate(keypoints_list):
        if i < start_frame or i > end_frame:
            continue
        if kp and _is_visible(kp, 'right_wrist', 'right_elbow'):
            idxs.append(i)
            vals.append(kp['right_wrist']['y'])
    return _rolling_median_extremum(idxs, vals, find_min=True)


def _find_racket_drop_frame(
    keypoints_list: list[dict],
    after_frame: int,
    end_frame: int | None = None,
) -> int | None:
    """Lowest right-wrist position (largest y) after trophy, within end_frame."""
    if end_frame is None:
        end_frame = len(keypoints_list) - 1
    idxs, vals = [], []
    for i, kp in enumerate(keypoints_list):
        if i <= after_frame or i > end_frame:
            continue
        if kp and _is_visible(kp, 'right_wrist', 'right_elbow'):
            idxs.append(i)
            vals.append(kp['right_wrist']['y'])
    return _rolling_median_extremum(idxs, vals, find_min=False)


def _find_contact_frame(
    angles_list: list[dict],
    after_frame: int,
    keypoints_list: list[dict] | None = None,
    end_frame: int | None = None,
) -> int | None:
    """Max right-elbow extension after racket drop, within end_frame."""
    if end_frame is None:
        end_frame = len(angles_list) - 1
    idxs, vals = [], []
    for i, angles in enumerate(angles_list):
        if i <= after_frame or i > end_frame:
            continue
        if keypoints_list and i < len(keypoints_list):
            kp = keypoints_list[i]
            if not kp or not _is_visible(kp, 'right_elbow', 'right_shoulder', 'right_wrist'):
                continue
        if angles and angles.get('right_elbow_flexion') is not None:
            idxs.append(i)
            vals.append(angles['right_elbow_flexion'])
    return _rolling_median_extremum(idxs, vals, find_min=False)


# ── Badminton-specific detectors ─────────────────────────────────────────────

def _find_clear_contact_frame(
    keypoints_list: list[dict],
    start_frame: int = 0,
    end_frame: int | None = None,
) -> int | None:
    """Contact for a badminton clear = highest right-wrist within the swing window."""
    return _find_trophy_frame(keypoints_list, start_frame=start_frame, end_frame=end_frame)


def _find_backswing_frame(
    angles_list: list[dict],
    before_frame: int,
    keypoints_list: list[dict] | None = None,
    start_frame: int = 0,
) -> int | None:
    """
    Most-bent right elbow (minimum flexion angle) in [start_frame, before_frame).

    The swing window's start_frame replaces the old hard-coded 120-frame lookback.
    """
    idxs, vals = [], []
    for i in range(start_frame, before_frame):
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
    end_frame: int | None = None,
) -> int | None:
    """Lowest right-wrist position after contact, within end_frame."""
    return _find_racket_drop_frame(
        keypoints_list, after_frame=after_frame, end_frame=end_frame
    )


# ── Single-frame scorer ──────────────────────────────────────────────────────

def _score_one_frame(frame_angles: dict, checkpoint_baselines: dict) -> dict:
    """
    Score one frame's joint angles against one checkpoint's expert baselines.

    For each joint that exists in both the frame and the baselines:
      deviation_deg  = abs(player_angle - expert_mean)
      severity_score = min(deviation_deg / (2 * expert_std), 1.0)
      direction      = "too_high" or "too_low"
    """
    deviations = {}
    for joint, angle in frame_angles.items():
        if angle is None:
            continue
        if joint not in checkpoint_baselines:
            continue
        expert = checkpoint_baselines[joint]
        deviation_deg  = abs(angle - expert['mean'])
        # Floor the std at 12° so single-video baselines (std=5) don't make
        # severity hit 1.0 on trivially small deviations. Remove once proper
        # multi-video baselines are in place.
        effective_std  = max(expert['std'], 12.0)
        severity_score = min(deviation_deg / (2 * effective_std), 1.0)
        direction      = "too_high" if angle > expert['mean'] else "too_low"
        deviations[joint] = {
            "angle":          angle,
            "deviation_deg":  deviation_deg,
            "severity_score": severity_score,
            "direction":      direction,
        }
    return deviations


# ── Main public function ─────────────────────────────────────────────────────

def score_deviations(
    angles_list: list[dict],
    sport_type: str = "tennis_serve",
    keypoints_list: list[dict] | None = None,
    fps: float = 30.0,
) -> dict:
    """
    Detect the three serve checkpoints and score each one against expert baselines.

    Step 0: find the swing window (frames where wrist is above shoulder) so
    checkpoint search is confined to the actual stroke, not the run-up.

    Args:
        angles_list:    per-frame angle dicts from calculator.py
        sport_type:     "tennis_serve" or "badminton"
        keypoints_list: per-frame keypoint dicts from extractor.py

    Returns:
        dict with shape:
        {
          "checkpoints": { name: {"frame": int, "deviations": {...}} | None },
          "deviations":        { joint: {...} },  # contact deviations for renderer
          "swing_window":      [start_frame, end_frame],
          "hip_leads_shoulder": bool,
          "baseline_source":    str,
        }
    """
    # ── 1. Load baseline file ────────────────────────────────────────────────
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

    kp_list = keypoints_list or []

    # ── 2. Detect swing window ───────────────────────────────────────────────
    win_start, win_end = _find_swing_window(kp_list, fps=fps)

    # ── 3. Detect checkpoints within the swing window ────────────────────────
    def score_checkpoint(frame_idx, checkpoint_name):
        if frame_idx is None:
            return None
        frame_angles = angles_list[frame_idx] if frame_idx < len(angles_list) else {}
        deviations   = _score_one_frame(frame_angles, baselines[checkpoint_name])
        return {"frame": frame_idx, "deviations": deviations}

    if sport_type == "badminton":
        contact_frame = _find_clear_contact_frame(
            kp_list, start_frame=win_start, end_frame=win_end
        )
        backswing_frame = _find_backswing_frame(
            angles_list,
            before_frame=contact_frame if contact_frame is not None else win_end,
            keypoints_list=kp_list,
            start_frame=win_start,
        )
        follow_through_frame = _find_follow_through_frame(
            kp_list,
            after_frame=contact_frame if contact_frame is not None else win_start,
            end_frame=win_end,
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
        trophy_frame = _find_trophy_frame(
            kp_list, start_frame=win_start, end_frame=win_end
        )
        racket_drop_frame = _find_racket_drop_frame(
            kp_list,
            after_frame=trophy_frame if trophy_frame is not None else win_start,
            end_frame=win_end,
        )
        contact_frame = _find_contact_frame(
            angles_list,
            after_frame=racket_drop_frame if racket_drop_frame is not None else win_start,
            keypoints_list=kp_list,
            end_frame=win_end,
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

    # ── 4. Return ────────────────────────────────────────────────────────────
    return {
        "checkpoints":        checkpoints,
        "deviations":         primary_deviations,
        "swing_window":       [win_start, win_end],
        "hip_leads_shoulder": False,
        "baseline_source":    os.path.relpath(baselines_path, repo_root),
    }
