"""
backend/court_tracker.py — Player movement tracking, bird's-eye view rendering.

Assumption: camera is fixed behind the user (near side).
Therefore the user is always the person with the HIGHEST y centroid
(lowest in the frame = closest to the camera).
When two people are detected, we simply pick the one with larger hip-y.
This is simpler and more robust than velocity-based ID tracking.
"""

import json
import os
import uuid
import math

import cv2
import numpy as np
import mediapipe as _mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

from backend.shot_detector import _faststart

# ── MediaPipe landmark indices ────────────────────────────────────────────────
LEFT_HIP    = 23
RIGHT_HIP   = 24
LEFT_ANKLE  = 27
RIGHT_ANKLE = 28

# ── Constants ─────────────────────────────────────────────────────────────────
MOVEMENT_STRIDE  = 6
COURT_W, COURT_H = 400, 440
TRAIL_LEN        = 40


# Landmark indices needed for shot detection (names match shot_detector convention)
_SHOT_LM = {
    0: 'nose',
    11: 'left_shoulder',  12: 'right_shoulder',
    13: 'left_elbow',     14: 'right_elbow',
    15: 'left_wrist',     16: 'right_wrist',
    23: 'left_hip',       24: 'right_hip',
    27: 'left_ankle',     28: 'right_ankle',
}


# ── Landmark helpers ──────────────────────────────────────────────────────────

def _hip_y(lms) -> float:
    return (lms[LEFT_HIP].y + lms[RIGHT_HIP].y) / 2

def _ankle_mid(lms) -> tuple[float, float]:
    la, ra = lms[LEFT_ANKLE], lms[RIGHT_ANKLE]
    return ((la.x + ra.x) / 2, (la.y + ra.y) / 2)

def _to_kp_dict(lms) -> dict:
    """Convert MediaPipe landmarks to the dict format expected by detect_shots."""
    return {name: {'x': lms[idx].x, 'y': lms[idx].y, 'z': lms[idx].z}
            for idx, name in _SHOT_LM.items()}


# ── Pose extraction ───────────────────────────────────────────────────────────

def extract_ankle_positions(video_path: str) -> tuple[list, list, float, int, int]:
    """
    Extract user's ankle midpoint + full keypoints for each sampled frame.

    Returns (positions, keypoints_list, fps, video_w, video_h).
      positions:      list of {frame, time_s, x, y} or None  (one per sampled frame)
      keypoints_list: sparse list indexed by actual frame number, for detect_shots()
    """
    cap          = cv2.VideoCapture(video_path)
    fps          = cap.get(cv2.CAP_PROP_FPS) or 30.0
    video_w      = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    video_h      = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    cap.release()

    base = python.BaseOptions(model_asset_path="models/pose_landmarker.task")
    opts = vision.PoseLandmarkerOptions(
        base_options=base,
        running_mode=vision.RunningMode.VIDEO,
        num_poses=2,
        min_pose_detection_confidence=0.4,
        min_pose_presence_confidence=0.4,
        min_tracking_confidence=0.4,
    )
    landmarker    = vision.PoseLandmarker.create_from_options(opts)
    cap           = cv2.VideoCapture(video_path)
    positions:    list = []
    keypoints_list: list = [{}] * total_frames   # sparse; indexed by frame number
    frame_idx = 0

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        if frame_idx % MOVEMENT_STRIDE == 0:
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            mp_img    = _mp.Image(image_format=_mp.ImageFormat.SRGB, data=frame_rgb)
            ts        = int(frame_idx / fps * 1000)
            result    = landmarker.detect_for_video(mp_img, ts)
            poses     = result.pose_landmarks

            if not poses:
                positions.append(None)
            else:
                user_lms = max(poses, key=_hip_y)
                ax, ay   = _ankle_mid(user_lms)
                positions.append({
                    "frame":  frame_idx,
                    "time_s": frame_idx / fps,
                    "x": ax,
                    "y": ay,
                })
                keypoints_list[frame_idx] = _to_kp_dict(user_lms)

        frame_idx += 1

    cap.release()
    detected = sum(1 for p in positions if p is not None)
    print(f"[movement] {detected}/{len(positions)} frames with pose detected")
    return positions, keypoints_list, fps, video_w, video_h


# ── Shot detection by wrist speed ────────────────────────────────────────────

def detect_shots_by_wrist_speed(keypoints_list: list, fps: float) -> set[int]:
    """
    Detect shot events by the speed of the right wrist.

    For each pair of consecutive sampled frames, compute the wrist displacement.
    Frames where displacement > WRIST_SPEED_THRESHOLD are 'triggered'.
    Nearby triggered frames are merged into one event; the peak (fastest) frame
    of each event is returned as the shot frame number.
    """
    # Collect (actual_frame_idx, wrist_x, wrist_y) for sampled frames only
    wrist_seq = []
    for i, kp in enumerate(keypoints_list):
        if not kp:
            continue
        w = kp.get("right_wrist")
        if w:
            wrist_seq.append((i, w["x"], w["y"]))

    if len(wrist_seq) < 2:
        return set()

    # Compute per-step displacement (only for consecutive sampled frames)
    triggered = []
    for j in range(1, len(wrist_seq)):
        i0, x0, y0 = wrist_seq[j - 1]
        i1, x1, y1 = wrist_seq[j]
        if i1 - i0 != MOVEMENT_STRIDE:
            continue   # skip non-consecutive pairs (detection gap)
        dist = math.hypot(x1 - x0, y1 - y0)
        if dist >= WRIST_SPEED_THRESHOLD:
            triggered.append((i1, dist))

    if not triggered:
        return set()

    # Merge nearby triggers into events
    events: list[list] = []
    group = [triggered[0]]
    for item in triggered[1:]:
        if item[0] - group[-1][0] <= WRIST_MERGE_GAP:
            group.append(item)
        else:
            events.append(group)
            group = [item]
    events.append(group)

    # Peak frame = highest displacement within each event
    shot_frames = {max(g, key=lambda x: x[1])[0] for g in events}
    print(f"[shots] wrist-speed detected {len(shot_frames)} shot(s) "
          f"(threshold={WRIST_SPEED_THRESHOLD})")
    return shot_frames


# ── Court-bounds filter + smoother ────────────────────────────────────────────

COURT_MARGIN    = 30     # pixel margin: positions this far outside court → invalid
JUMP_THRESHOLD  = 0.12   # normalised distance between consecutive valid positions
JUMP_LOOK_AHEAD = 40     # how many valid frames ahead to search for a return point

# Shot detection by wrist speed
WRIST_SPEED_THRESHOLD = 0.07   # min normalised displacement per sampled frame
WRIST_MERGE_GAP       = 18     # actual frames; events closer than this are merged


def _invalidate_out_of_bounds(
    positions: list, H: np.ndarray, video_w: int, video_h: int
) -> list:
    """
    Mark positions that transform outside the court as None.
    Any detection with a transformed y < 0 (beyond the net) is the opponent.
    """
    result = []
    for p in positions:
        if p is None:
            result.append(None)
            continue
        src = np.float32([[[p["x"] * video_w, p["y"] * video_h]]])
        dst = cv2.perspectiveTransform(src, H)
        x, y = dst[0][0]
        in_bounds = (
            np.isfinite(x) and np.isfinite(y)
            and -COURT_MARGIN <= x <= COURT_W + COURT_MARGIN
            and -COURT_MARGIN <= y <= COURT_H + COURT_MARGIN
        )
        result.append(p if in_bounds else None)
    invalidated = sum(1 for a, b in zip(positions, result) if a is not None and b is None)
    print(f"[filter] invalidated {invalidated} out-of-bounds detections")
    return result


def _smooth_positions(positions: list) -> list:
    """
    Two-pass smoother:
    1. Fill None gaps (from missing / invalidated detections) with linear interpolation.
    2. Detect remaining sudden jumps and interpolate across them.
    """
    valid = [(i, p) for i, p in enumerate(positions) if p is not None]
    if len(valid) < 2:
        return positions

    result = list(positions)

    vi = 0
    while vi < len(valid) - 1:
        idx_a, p_a = valid[vi]
        idx_b, p_b = valid[vi + 1]

        dist = math.hypot(p_b["x"] - p_a["x"], p_b["y"] - p_a["y"])
        has_gap = idx_b > idx_a + 1   # there are None slots between the two

        if has_gap:
            # Fill every None between idx_a and idx_b
            span = idx_b - idx_a
            for k in range(idx_a + 1, idx_b):
                if result[k] is None:
                    t = (k - idx_a) / span
                    result[k] = {
                        "frame":  round(p_a["frame"] + t * (p_b["frame"] - p_a["frame"])),
                        "time_s": p_a["time_s"] + t * (p_b["time_s"] - p_a["time_s"]),
                        "x":      p_a["x"]     + t * (p_b["x"]     - p_a["x"]),
                        "y":      p_a["y"]     + t * (p_b["y"]     - p_a["y"]),
                    }
            vi += 1

        elif dist > JUMP_THRESHOLD:
            # Look for a return point within the look-ahead window
            end_vi = None
            for vj in range(vi + 2, min(vi + JUMP_LOOK_AHEAD, len(valid))):
                _, p_c = valid[vj]
                if math.hypot(p_c["x"] - p_a["x"], p_c["y"] - p_a["y"]) <= JUMP_THRESHOLD:
                    end_vi = vj
                    break

            if end_vi is not None:
                idx_end, p_end = valid[end_vi]
                span = idx_end - idx_a
                for vk in range(vi + 1, end_vi):
                    idx_bad, _ = valid[vk]
                    t = (idx_bad - idx_a) / span
                    result[idx_bad] = {
                        **result[idx_bad],
                        "x": p_a["x"] + t * (p_end["x"] - p_a["x"]),
                        "y": p_a["y"] + t * (p_end["y"] - p_a["y"]),
                    }
                vi = end_vi
                continue

            vi += 1
        else:
            vi += 1

    return result


# ── Court drawing ─────────────────────────────────────────────────────────────

def _draw_court(w: int, h: int) -> np.ndarray:
    """Own-half court: net at top, baseline at bottom."""
    img = np.full((h, w, 3), 18, dtype=np.uint8)
    pad = 20

    cv2.rectangle(img, (pad, pad), (w - pad, h - pad), (70, 70, 70), 2)
    cv2.line(img, (pad, pad), (w - pad, pad), (120, 120, 120), 3)

    svc   = pad + (h - 2 * pad) // 3
    mid_x = w // 2
    cv2.line(img, (pad,   svc), (w - pad, svc),   (50, 50, 50), 1)
    cv2.line(img, (mid_x, svc), (mid_x, h - pad), (45, 45, 45), 1)

    return img


# ── Homography ────────────────────────────────────────────────────────────────

def _build_homography(corners: list[dict], video_w: int, video_h: int) -> np.ndarray:
    """corners: TL, TR, BR, BL — user's own half (net top, baseline bottom)."""
    src = np.float32([
        [c["x"] / 100.0 * video_w, c["y"] / 100.0 * video_h]
        for c in corners
    ])
    dst = np.float32([
        [0,       0      ],
        [COURT_W, 0      ],
        [COURT_W, COURT_H],
        [0,       COURT_H],
    ])
    return cv2.getPerspectiveTransform(src, dst)


def _transform_point(pt: dict, H: np.ndarray, video_w: int, video_h: int) -> tuple[int, int] | None:
    if pt is None:
        return None
    src = np.float32([[[pt["x"] * video_w, pt["y"] * video_h]]])
    dst = cv2.perspectiveTransform(src, H)
    x, y = dst[0][0]
    if not (np.isfinite(x) and np.isfinite(y)):
        return None
    return int(round(np.clip(x, 0, COURT_W))), int(round(np.clip(y, 0, COURT_H)))


# ── Debug overlay video ───────────────────────────────────────────────────────

def generate_debug_overlay(
    video_path: str,
    positions: list,
    keypoints_list: list,
    fps: float,
    session_id: str,
    shot_frames: set | None = None,
) -> str:
    """
    Render the original video (at sampled FPS) with tracked keypoints overlaid:
      - Green filled circle  : ankle midpoint  (turns red on shot frames)
      - Cyan  filled circle  : right wrist
    """
    results_dir = os.path.join("data", "results", session_id)
    out_path    = os.path.join(results_dir, "debug.mp4")

    cap     = cv2.VideoCapture(video_path)
    vid_w   = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    vid_h   = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    out_fps = max(1.0, fps / MOVEMENT_STRIDE)
    writer  = cv2.VideoWriter(
        out_path, cv2.VideoWriter_fourcc(*"avc1"), out_fps, (vid_w, vid_h)
    )

    frame_to_pos = {p["frame"]: p for p in positions if p is not None}

    shot_set: set[int] = set()
    if shot_frames:
        window = MOVEMENT_STRIDE * 3
        for sf in shot_frames:
            for d in range(-window, window + 1):
                shot_set.add(sf + d)

    frame_idx = 0
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        if frame_idx % MOVEMENT_STRIDE == 0:
            pos = frame_to_pos.get(frame_idx)
            kp  = keypoints_list[frame_idx] if frame_idx < len(keypoints_list) else {}

            if pos:
                ax, ay   = int(pos["x"] * vid_w), int(pos["y"] * vid_h)
                is_shot  = frame_idx in shot_set
                a_color  = (0, 0, 255) if is_shot else (0, 255, 0)
                cv2.circle(frame, (ax, ay), 16, a_color, -1)
                cv2.circle(frame, (ax, ay), 18, (255, 255, 255), 2)
                if is_shot:
                    cv2.putText(frame, "SHOT", (ax + 22, ay - 12),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)

            if kp and kp.get("right_wrist"):
                wr = kp["right_wrist"]
                wx, wy = int(wr["x"] * vid_w), int(wr["y"] * vid_h)
                cv2.circle(frame, (wx, wy), 10, (0, 255, 255), -1)
                cv2.circle(frame, (wx, wy), 12, (255, 255, 255), 1)

            writer.write(frame)

        frame_idx += 1

    cap.release()
    writer.release()
    _faststart(out_path)
    return out_path


# ── Video rendering ───────────────────────────────────────────────────────────

def generate_movement_video(
    positions: list,
    H: np.ndarray,
    video_w: int,
    video_h: int,
    fps: float,
    session_id: str,
    shot_frames: set | None = None,
) -> str:
    results_dir = os.path.join("data", "results", session_id)
    os.makedirs(results_dir, exist_ok=True)
    out_path = os.path.join(results_dir, "movement.mp4")

    out_fps    = max(1.0, fps / MOVEMENT_STRIDE)
    writer     = cv2.VideoWriter(
        out_path, cv2.VideoWriter_fourcc(*"avc1"), out_fps, (COURT_W, COURT_H)
    )
    court_pts  = [_transform_point(p, H, video_w, video_h) for p in positions]
    court_base = _draw_court(COURT_W, COURT_H)

    # Expand shot peaks into a frame-number set for fast lookup
    shot_frame_set: set[int] = set()
    if shot_frames:
        window = MOVEMENT_STRIDE * 3   # ±3 sampled frames around each shot peak
        for sf in shot_frames:
            for d in range(-window, window + 1):
                shot_frame_set.add(sf + d)

    for i, pt in enumerate(court_pts):
        frame = court_base.copy()

        for j in range(max(0, i - TRAIL_LEN), i):
            p = court_pts[j]
            if p is None:
                continue
            alpha = 1.0 - (i - j) / TRAIL_LEN
            cv2.circle(frame, p, max(3, int(10 * alpha)),
                       (int(87 * alpha), int(255 * alpha), int(200 * alpha)), -1)

        if pt is not None:
            pos = positions[i]
            is_shot = bool(pos and pos["frame"] in shot_frame_set)
            color = (0, 0, 255) if is_shot else (87, 255, 200)   # red or green (BGR)
            cv2.circle(frame, pt, 14, color, -1)
            cv2.circle(frame, pt, 16, (255, 255, 255), 2)

        writer.write(frame)

    writer.release()
    _faststart(out_path)
    return out_path


# ── Phase analysis ────────────────────────────────────────────────────────────

def _render_phase_heatmap(court_pts: list, out_path: str) -> None:
    """Render a density heatmap for a single phase's court positions."""
    from matplotlib.figure import Figure
    from matplotlib.backends.backend_agg import FigureCanvasAgg

    grid = np.zeros((COURT_H, COURT_W), dtype=np.float32)
    for x, y in court_pts:
        ix = int(np.clip(x, 0, COURT_W - 1))
        iy = int(np.clip(y, 0, COURT_H - 1))
        grid[iy, ix] += 1

    if grid.max() > 0:
        sigma = 18
        ksize = int(sigma * 6) | 1
        grid = cv2.GaussianBlur(grid, (ksize, ksize), sigma)

    court_rgb = cv2.cvtColor(_draw_court(COURT_W, COURT_H), cv2.COLOR_BGR2RGB)
    fig = Figure(figsize=(COURT_W / 100, COURT_H / 100), dpi=100)
    FigureCanvasAgg(fig)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.imshow(court_rgb, extent=[0, COURT_W, COURT_H, 0], aspect="auto")
    if grid.max() > 0:
        ax.imshow(grid, extent=[0, COURT_W, COURT_H, 0],
                  cmap="YlGn", alpha=0.75, vmin=0, vmax=grid.max(),
                  aspect="auto", interpolation="bilinear")
    ax.set_xlim(0, COURT_W)
    ax.set_ylim(COURT_H, 0)
    ax.axis("off")
    fig.savefig(out_path, dpi=100, bbox_inches="tight", pad_inches=0, facecolor="#111111")


def generate_phase_analysis(
    positions: list,
    H: np.ndarray,
    video_w: int,
    video_h: int,
    session_id: str,
) -> dict | None:
    """
    Split the match into three equal time phases, compute a heatmap and
    coverage metric for each, and flag potential stamina decline.

    Coverage metric = std_x × std_y (proxy for spread area in court coordinates).

    Returns:
        {
            "phases": [{"phase": int, "start_s": float, "end_s": float,
                        "coverage_pct": float}, ...],
            "stamina_flag": bool,
            "coverage_trend": [float, float, float],   # normalised %
        }
        or None if there is insufficient data.
    """
    valid = [(p["time_s"], p) for p in positions if p is not None]
    if len(valid) < 15:
        return None

    t_start = valid[0][0]
    t_end   = valid[-1][0]
    duration = t_end - t_start
    if duration < 10:
        return None

    phase_len = duration / 3
    boundaries = [
        (t_start,               t_start + phase_len),
        (t_start + phase_len,   t_start + 2 * phase_len),
        (t_start + 2 * phase_len, t_end),
    ]

    out_dir = os.path.join("data", "results", session_id)
    os.makedirs(out_dir, exist_ok=True)

    raw_coverages: list[float] = []
    phases_out: list[dict] = []

    for idx, (s, e) in enumerate(boundaries):
        phase_num = idx + 1
        phase_positions = [p for t, p in valid if s <= t <= e]

        court_pts: list[tuple[int, int]] = []
        for p in phase_positions:
            xy = _transform_point(p, H, video_w, video_h)
            if xy is not None and 0 <= xy[0] <= COURT_W and 0 <= xy[1] <= COURT_H:
                court_pts.append(xy)

        if len(court_pts) >= 3:
            xs = [p[0] for p in court_pts]
            ys = [p[1] for p in court_pts]
            cov = float(np.std(xs) * np.std(ys))
        else:
            cov = 0.0
        raw_coverages.append(cov)

        heatmap_path = os.path.join(out_dir, f"heatmap_phase_{phase_num}.png")
        _render_phase_heatmap(court_pts, heatmap_path)

        phases_out.append({
            "phase":   phase_num,
            "start_s": round(s, 1),
            "end_s":   round(e, 1),
        })

    # Normalise to percentage of maximum coverage
    max_cov = max(raw_coverages) if max(raw_coverages) > 0 else 1.0
    coverage_trend = [round(c / max_cov * 100, 1) for c in raw_coverages]

    for i, p in enumerate(phases_out):
        p["coverage_pct"] = coverage_trend[i]

    # Stamina flag: phase 3 coverage dropped below 65% of phase 1
    stamina_flag = (raw_coverages[0] > 0 and
                    raw_coverages[2] / raw_coverages[0] < 0.65)

    result = {
        "phases":         phases_out,
        "stamina_flag":   stamina_flag,
        "coverage_trend": coverage_trend,
    }

    with open(os.path.join(out_dir, "phase_analysis.json"), "w") as f:
        json.dump(result, f)

    print(f"[phase] coverage trend: {coverage_trend}, stamina_flag={stamina_flag}")
    return result


# ── Heatmap ───────────────────────────────────────────────────────────────────

def generate_heatmap(
    positions: list,
    H: np.ndarray,
    video_w: int,
    video_h: int,
    fps: float,
    rallies: list[dict],
    session_id: str,
) -> dict:
    """
    Generate position heatmaps for won and lost rallies and save as PNG.

    Each rally's contribution is normalised by its length so that short and
    long rallies carry equal weight in the heatmap.

    Returns: {"win": path, "loss": path}
    """
    from matplotlib.figure import Figure
    from matplotlib.backends.backend_agg import FigureCanvasAgg  # noqa (server-safe)

    out_dir = os.path.join("data", "results", session_id)
    os.makedirs(out_dir, exist_ok=True)

    # Map positions to court coordinates (time_s, cx, cy)
    timed: list[tuple[float, float, float]] = []
    for p in positions:
        if p is None:
            continue
        xy = _transform_point(p, H, video_w, video_h)
        if xy is None:
            continue
        cx, cy = xy
        if 0 <= cx < COURT_W and 0 <= cy < COURT_H:
            timed.append((p["time_s"], float(cx), float(cy)))

    def _collect(rally_list: list[dict]) -> np.ndarray:
        grid = np.zeros((COURT_H, COURT_W), dtype=np.float64)
        for rally in rally_list:
            start_s = rally.get("start_s", 0.0)
            end_s   = rally.get("end_s",   0.0)
            pts = [(cx, cy) for t, cx, cy in timed if start_s <= t <= end_s]
            if not pts:
                continue
            w = 1.0 / len(pts)   # equal weight per rally regardless of length
            for cx, cy in pts:
                grid[int(cy), int(cx)] += w
        return grid

    win_rallies  = [r for r in rallies if r.get("rally_winner") == "user"]
    loss_rallies = [r for r in rallies if r.get("rally_winner") == "opponent"]

    sigma = 20
    ksize = int(sigma * 6) | 1   # must be odd

    saved: dict[str, str] = {}
    for label, rally_list, cmap_name in [
        ("win",  win_rallies,  "YlGn"),
        ("loss", loss_rallies, "YlOrRd"),
    ]:
        grid = _collect(rally_list)
        if grid.max() > 0:
            grid = cv2.GaussianBlur(grid.astype(np.float32), (ksize, ksize), sigma)

        court_rgb = cv2.cvtColor(_draw_court(COURT_W, COURT_H), cv2.COLOR_BGR2RGB)

        fig = Figure(figsize=(COURT_W / 100, COURT_H / 100), dpi=100)
        FigureCanvasAgg(fig)
        ax  = fig.add_axes([0, 0, 1, 1])

        ax.imshow(court_rgb, extent=[0, COURT_W, COURT_H, 0], aspect="auto")
        if grid.max() > 0:
            ax.imshow(
                grid,
                extent=[0, COURT_W, COURT_H, 0],
                cmap=cmap_name,
                alpha=0.75,
                vmin=0, vmax=grid.max(),
                aspect="auto",
                interpolation="bilinear",
            )

        ax.set_xlim(0, COURT_W)
        ax.set_ylim(COURT_H, 0)
        ax.axis("off")

        out_path = os.path.join(out_dir, f"heatmap_{label}.png")
        fig.savefig(out_path, dpi=100, bbox_inches="tight", pad_inches=0,
                    facecolor="#111111")
        saved[label] = out_path

    print(f"[heatmap] win={len(win_rallies)} loss={len(loss_rallies)} rallies → {out_dir}")
    return saved


# ── Entry point ───────────────────────────────────────────────────────────────

def _downscale_if_needed(video_path: str, max_width: int = 1280) -> tuple[str, bool]:
    """If video width exceeds max_width, return a downscaled temp copy; else return original."""
    import subprocess, tempfile
    cap = cv2.VideoCapture(video_path)
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    cap.release()
    if w <= max_width:
        return video_path, False
    suffix = os.path.splitext(video_path)[1] or ".mp4"
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    tmp.close()
    print(f"[movement] Downscaling {w}px → {max_width}px for faster processing…")
    subprocess.run(
        ["ffmpeg", "-y", "-i", video_path,
         "-vf", f"scale={max_width}:-2",
         "-c:v", "libx264", "-crf", "23", "-preset", "fast",
         "-c:a", "copy", tmp.name],
        check=True, capture_output=True,
    )
    return tmp.name, True


def run_court_analysis(video_path: str, court_corners: list[dict]) -> dict:
    session_id = str(uuid.uuid4())

    work_path, is_tmp = _downscale_if_needed(video_path)
    try:
        print("[movement] Extracting positions…")
        positions, keypoints_list, fps, video_w, video_h = extract_ankle_positions(work_path)
    finally:
        if is_tmp and os.path.exists(work_path):
            os.unlink(work_path)

    H = _build_homography(court_corners, video_w, video_h)

    print("[movement] Filtering out-of-bounds detections…")
    positions = _invalidate_out_of_bounds(positions, H, video_w, video_h)

    print("[movement] Smoothing trajectory…")
    positions = _smooth_positions(positions)

    print("[movement] Detecting shots by wrist speed…")
    shot_frames = detect_shots_by_wrist_speed(keypoints_list, fps)

    print("[movement] Rendering bird's-eye video…")
    out_path = generate_movement_video(
        positions, H, video_w, video_h, fps, session_id, shot_frames=shot_frames
    )

    print("[movement] Rendering debug overlay…")
    generate_debug_overlay(
        video_path, positions, keypoints_list, fps, session_id, shot_frames=shot_frames
    )
    print(f"[movement] Done → {out_path}")

    # Save court-transformed positions for frontend minimap
    court_pts_export = []
    for p in positions:
        if p is None:
            continue
        xy = _transform_point(p, H, video_w, video_h)
        if xy is not None:
            court_pts_export.append({
                "time_s": round(p["time_s"], 3),
                "cx": int(xy[0]),
                "cy": int(xy[1]),
            })
    results_dir = os.path.join("data", "results", session_id)
    os.makedirs(results_dir, exist_ok=True)
    with open(os.path.join(results_dir, "positions.json"), "w") as _pf:
        json.dump(court_pts_export, _pf)

    print("[movement] Running phase analysis…")
    phase_analysis = generate_phase_analysis(positions, H, video_w, video_h, session_id)

    first_valid = next((p for p in positions if p is not None), None)
    match_start_s = round(first_valid["time_s"], 3) if first_valid else 0.0

    return {
        "session_id":          session_id,
        "movement_video_path": out_path,
        "total_positions":     sum(1 for p in positions if p is not None),
        "duration_s":          round(len(positions) * MOVEMENT_STRIDE / fps, 1),
        "phase_analysis":      phase_analysis,
        "match_start_s":       match_start_s,
        # Internal data passed to generate_heatmap() in main.py
        "_positions": positions,
        "_H":         H,
        "_fps":       fps,
        "_video_w":   video_w,
        "_video_h":   video_h,
    }
