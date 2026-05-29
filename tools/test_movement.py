"""
Diagnose court_tracker: check transformed ankle positions against canvas bounds.
Uses default corner positions matching CourtCalibrator initial state.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from backend import court_tracker
import numpy as np

VIDEO_PATH = "data/samples/badminton/badminton_match.mov"

# Default corners from CourtCalibrator (x,y in % of frame)
CORNERS = [
    {"x": 15, "y": 20},  # TL
    {"x": 85, "y": 20},  # TR
    {"x": 85, "y": 80},  # BR
    {"x": 15, "y": 80},  # BL
]

print("Extracting ankle positions (first 300 sampled frames)...")
positions, fps, video_w, video_h = court_tracker.extract_ankle_positions(VIDEO_PATH)
print(f"  video: {video_w}x{video_h} @ {fps}fps, sampled {len(positions)} frames")

detected = [(i, p) for i, p in enumerate(positions) if p is not None]
print(f"  detected: {len(detected)}/{len(positions)}")

if not detected:
    print("ERROR: No poses detected at all!")
    sys.exit(1)

# Show first 5 detected raw positions
print("\nFirst 5 raw ankle midpoints (normalised):")
for i, p in detected[:5]:
    print(f"  frame {p['frame']:5d}: x={p['x']:.3f}, y={p['y']:.3f}")

H = court_tracker._build_homography(CORNERS, video_w, video_h)
print(f"\nHomography matrix:\n{H}")

# Transform positions
print("\nFirst 20 transformed positions (court px):")
in_bounds = 0
out_bounds = 0
for i, p in detected[:20]:
    pt = court_tracker._transform_point(p, H, video_w, video_h)
    x, y = pt
    ok = 0 <= x <= court_tracker.COURT_W and 0 <= y <= court_tracker.COURT_H
    status = "OK" if ok else "OUT"
    if ok: in_bounds += 1
    else:  out_bounds += 1
    print(f"  frame {p['frame']:5d}: ({x:4d}, {y:4d}) {status}")

# Check all
print(f"\nChecking all {len(detected)} detected positions...")
in_all = 0
for _, p in detected:
    pt = court_tracker._transform_point(p, H, video_w, video_h)
    x, y = pt
    if 0 <= x <= court_tracker.COURT_W and 0 <= y <= court_tracker.COURT_H:
        in_all += 1

print(f"  In-bounds: {in_all}/{len(detected)} ({100*in_all//len(detected)}%)")
print(f"  COURT_W={court_tracker.COURT_W}, COURT_H={court_tracker.COURT_H}")
