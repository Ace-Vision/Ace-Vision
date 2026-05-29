"""
tools/shot_stats.py — Print max wrist/elbow height + pre-contact wrist dx per shot.

dx = average horizontal velocity of right wrist in the ~20 frames before peak.
  negative dx → wrist moving LEFT  (forehand: coming from right side)
  positive dx → wrist moving RIGHT (backhand: coming from left/below)

Usage:
    python tools/shot_stats.py <video_path>
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.shot_detector import (
    extract_keypoints_strided, detect_shots,
    _body_scale, _wrist_above_shoulder, WRIST_THRESHOLD_RATIO,
)

LOOKBACK_FRAMES = 20  # frames before peak to compute dx


def elbow_above_shoulder(kp: dict) -> float:
    elbow    = kp.get("right_elbow")
    shoulder = kp.get("right_shoulder")
    if not elbow or not shoulder:
        return 0.0
    return shoulder["y"] - elbow["y"]


def wrist_approach_dx(keypoints_list: list, peak_frame: int) -> float:
    """
    Compute mean dx of right wrist in the LOOKBACK_FRAMES before peak.
    Uses first-half vs second-half average to smooth noise.
    """
    xs = []
    for fi in range(max(0, peak_frame - LOOKBACK_FRAMES), peak_frame + 1):
        kp = keypoints_list[fi] if fi < len(keypoints_list) else {}
        w = kp.get("right_wrist")
        if w:
            xs.append(w["x"])

    if len(xs) < 4:
        return 0.0

    mid = len(xs) // 2
    early_mean = sum(xs[:mid]) / mid
    late_mean  = sum(xs[mid:]) / len(xs[mid:])
    return late_mean - early_mean   # negative = moving left = forehand


def main(video_path: str):
    print(f"Extracting keypoints: {video_path}")
    keypoints_list, fps = extract_keypoints_strided(video_path)
    shots = detect_shots(keypoints_list, fps)
    print(f"Detected {len(shots)} shots\n")

    print(f"{'#':>3}  {'peak(s)':>7}  {'wrist':>6}  {'elbow':>6}  {'dx(pre)':>9}  direction")
    print("-" * 58)

    for i, shot in enumerate(shots):
        max_wrist = 0.0
        max_elbow = 0.0
        for fi in range(shot["start_frame"], shot["end_frame"] + 1):
            kp = keypoints_list[fi] if fi < len(keypoints_list) else {}
            if not kp:
                continue
            scale = _body_scale(kp)
            if not scale:
                continue
            max_wrist = max(max_wrist, _wrist_above_shoulder(kp) / scale)
            max_elbow = max(max_elbow, elbow_above_shoulder(kp) / scale)

        dx        = wrist_approach_dx(keypoints_list, shot["peak_frame"])
        direction = "← forehand" if dx < -0.01 else ("→ backhand" if dx > 0.01 else "  unclear")

        print(f"{i+1:>3}  {shot['peak_time_s']:>7.1f}s  {max_wrist:>6.3f}  {max_elbow:>6.3f}  {dx:>+9.4f}  {direction}")

    print(f"\n閾値: WRIST_THRESHOLD_RATIO={WRIST_THRESHOLD_RATIO}, LOOKBACK_FRAMES={LOOKBACK_FRAMES}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python tools/shot_stats.py <video>")
        sys.exit(1)
    main(sys.argv[1])
