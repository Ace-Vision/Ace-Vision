"""
Test body-relative net_dx approach with multiple lookback windows.
dominant_dir = +1 if rs.x > ls.x (faces camera), -1 if facing away.
body_rel_net_dx = net_dx * dominant_dir
  < 0 → wrist moved toward non-dominant side → FOREHAND
  > 0 → wrist moved toward dominant side → BACKHAND
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from backend import shot_detector
import cv2
import mediapipe as _mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

BACKHAND_SHOTS = {2, 3, 5, 9, 11, 17, 20, 28}
VIDEO_PATH = "data/samples/badminton/badminton_match.mov"

RIGHT_WRIST    = 16
RIGHT_SHOULDER = 12
LEFT_SHOULDER  = 11

print("Extracting keypoints (strided)...")
keypoints_list, fps = shot_detector.extract_keypoints_strided(VIDEO_PATH)
shots = shot_detector.detect_shots(keypoints_list, fps)
print(f"Detected {len(shots)} shots, fps={fps}\n")

base_options = python.BaseOptions(model_asset_path="models/pose_landmarker.task")
options = vision.PoseLandmarkerOptions(base_options=base_options, running_mode=vision.RunningMode.IMAGE)
landmarker = vision.PoseLandmarker.create_from_options(options)
cap = cv2.VideoCapture(VIDEO_PATH)

LOOKBACKS = [5, 10, 15, 20, 30]

# Pre-collect data for all shots once
shot_data = []  # list of (peak, peak_rsx, peak_lsx, wrist_xs_by_lookback)

for shot in shots:
    peak = shot["peak_frame"]
    # Read up to 30 frames before peak + peak itself
    start = max(0, peak - 30)
    cap.set(cv2.CAP_PROP_POS_FRAMES, start)

    frame_wrist_x = {}  # relative_offset → wrist_x
    frame_rs_x = {}
    frame_ls_x = {}

    for offset in range(0, peak - start + 1):
        ret, frame = cap.read()
        if not ret:
            break
        actual_frame = start + offset
        relative = peak - actual_frame  # 0 = peak, 1 = one before peak, etc.

        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_img = _mp.Image(image_format=_mp.ImageFormat.SRGB, data=frame_rgb)
        result = landmarker.detect(mp_img)
        if result.pose_landmarks:
            lms = result.pose_landmarks[0]
            frame_wrist_x[relative] = lms[RIGHT_WRIST].x
            frame_rs_x[relative]    = lms[RIGHT_SHOULDER].x
            frame_ls_x[relative]    = lms[LEFT_SHOULDER].x

    shot_data.append({
        "peak": peak,
        "wrist_x": frame_wrist_x,
        "rs_x":    frame_rs_x,
        "ls_x":    frame_ls_x,
    })

cap.release()

# For each lookback, compute accuracy
print(f"{'Lookback':>10}  {'Confident':>10}  {'Accuracy':>10}")
print("-" * 40)
THRESHOLD = shot_detector.CLASSIFY_CONFIDENCE_THRESHOLD

best_lookback = 5
best_acc = 0

for lb in LOOKBACKS:
    correct = 0
    total_conf = 0
    details = []

    for i, (shot, sd) in enumerate(zip(shots, shot_data)):
        num = i + 1
        true_type = "backhand" if num in BACKHAND_SHOTS else "forehand"
        wrist_x = sd["wrist_x"]
        rs_x = sd["rs_x"]
        ls_x = sd["ls_x"]

        # peak frame direction (relative=0 is peak)
        if 0 in rs_x and 0 in ls_x:
            dominant_dir = 1.0 if rs_x[0] > ls_x[0] else -1.0
        else:
            dominant_dir = 1.0

        # collect wrist_x for frames [peak-lb .. peak] (relative lb → 0)
        xs = []
        for rel in range(lb, -1, -1):  # lb, lb-1, ..., 0
            if rel in wrist_x:
                xs.append(wrist_x[rel])

        if len(xs) < 2:
            pred = "forehand"; conf = 0.5
        else:
            net_dx = xs[-1] - xs[0]
            body_rel = net_dx * dominant_dir
            # forehand: body_rel < 0 (wrist moved toward non-dominant side)
            # backhand: body_rel > 0
            conf = min(1.0, 0.5 + abs(body_rel) * 5.0)
            pred = "backhand" if body_rel > 0 else "forehand"

        if conf >= THRESHOLD:
            total_conf += 1
            if pred == true_type:
                correct += 1
        details.append((num, true_type, pred, conf))

    acc = (100 * correct // total_conf) if total_conf else 0
    marker = " ← BEST" if acc > best_acc else ""
    print(f"{lb:>10}  {total_conf:>4}/{len(shots):<5}    {correct}/{total_conf}={acc:>3}%{marker}")
    if acc > best_acc:
        best_acc = acc
        best_lookback = lb
        best_details = details

print(f"\n--- Detail for best lookback={best_lookback} ---")
print(f"{'Shot':>4} {'true':>9} {'pred':>9} {'conf':>6} {'ok':>3}")
for num, true_type, pred, conf in best_details:
    mark = "✓" if pred == true_type else "✗"
    star = "" if conf >= THRESHOLD else "*"
    print(f"{num:>4} {true_type:>9} {pred:>9} {conf:>6.2f} {mark}{star}")
