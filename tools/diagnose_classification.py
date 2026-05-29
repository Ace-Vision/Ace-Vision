"""
Diagnostic: print wrist position RELATIVE TO BODY at peak frame for each shot.
If player faces camera: rs.x > ls.x (right shoulder on screen-right)
If player faces away:   rs.x < ls.x (right shoulder on screen-left)

For forehand overhead: right wrist should be on the ANATOMICALLY-RIGHT side of body.
  -> wrist_relative > 0
For backhand overhead: right wrist crosses to the anatomically-left side.
  -> wrist_relative < 0

wrist_relative = (wrist.x - shoulder_mid.x) * sign(rs.x - ls.x)
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

RIGHT_WRIST = 16
RIGHT_SHOULDER = 12
LEFT_SHOULDER = 11

print("Extracting keypoints (strided)...")
keypoints_list, fps = shot_detector.extract_keypoints_strided(VIDEO_PATH)
shots = shot_detector.detect_shots(keypoints_list, fps)
print(f"Detected {len(shots)} shots\n")

# Build IMAGE mode landmarker
base_options = python.BaseOptions(model_asset_path="models/pose_landmarker.task")
options = vision.PoseLandmarkerOptions(base_options=base_options, running_mode=vision.RunningMode.IMAGE)
landmarker = vision.PoseLandmarker.create_from_options(options)
cap = cv2.VideoCapture(VIDEO_PATH)

print(f"{'Shot':>4} {'true':>9} {'wrist_rel':>10} {'wrist.x':>8} {'rs.x':>6} {'ls.x':>6} {'net_dx':>8} {'pred_rel':>10} {'pred_dx':>9}")
print("-" * 80)

threshold = shot_detector.CLASSIFY_CONFIDENCE_THRESHOLD
correct_rel = 0
correct_dx = 0
confident_rel = 0
confident_dx = 0

for i, shot in enumerate(shots):
    num = i + 1
    true_type = "backhand" if num in BACKHAND_SHOTS else "forehand"
    peak = shot["peak_frame"]
    start = max(0, peak - 5)

    cap.set(cv2.CAP_PROP_POS_FRAMES, start)
    wrist_xs = []
    rel_positions = []

    for _ in range(peak - start + 1):
        ret, frame = cap.read()
        if not ret:
            break
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_img = _mp.Image(image_format=_mp.ImageFormat.SRGB, data=frame_rgb)
        result = landmarker.detect(mp_img)
        if result.pose_landmarks:
            lms = result.pose_landmarks[0]
            wx = lms[RIGHT_WRIST].x
            rsx = lms[RIGHT_SHOULDER].x
            lsx = lms[LEFT_SHOULDER].x
            mid = (rsx + lsx) / 2
            dominant_dir = 1.0 if rsx > lsx else -1.0
            wrist_rel = (wx - mid) * dominant_dir
            wrist_xs.append(wx)
            rel_positions.append(wrist_rel)

    # --- Approach A: wrist_relative at peak frame ---
    if rel_positions:
        peak_rel = rel_positions[-1]
        conf_a = min(1.0, 0.5 + abs(peak_rel) * 5.0)
        pred_a = "forehand" if peak_rel > 0 else "backhand"
    else:
        peak_rel = 0.0
        conf_a = 0.5
        pred_a = "forehand"

    # --- Approach B: net_dx in absolute coords (current) ---
    if len(wrist_xs) >= 2:
        net_dx = wrist_xs[-1] - wrist_xs[0]
        conf_b = min(1.0, 0.5 + abs(net_dx) * 5.0)
        pred_b = "forehand" if net_dx < 0 else "backhand"
    else:
        net_dx = 0.0
        conf_b = 0.5
        pred_b = "forehand"

    wrist_x_peak = wrist_xs[-1] if wrist_xs else 0
    rs_x_peak = 0
    ls_x_peak = 0
    cap.set(cv2.CAP_PROP_POS_FRAMES, peak)
    ret, frame = cap.read()
    if ret:
        result2 = landmarker.detect(_mp.Image(image_format=_mp.ImageFormat.SRGB, data=cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)))
        if result2.pose_landmarks:
            lms2 = result2.pose_landmarks[0]
            rs_x_peak = lms2[RIGHT_SHOULDER].x
            ls_x_peak = lms2[LEFT_SHOULDER].x

    mark_a = "✓" if pred_a == true_type else "✗"
    mark_b = "✓" if pred_b == true_type else "✗"

    if conf_a >= threshold:
        confident_rel += 1
        if pred_a == true_type:
            correct_rel += 1
    if conf_b >= threshold:
        confident_dx += 1
        if pred_b == true_type:
            correct_dx += 1

    print(f"{num:>4} {true_type:>9} {peak_rel:>+10.3f} {wrist_x_peak:>8.3f} {rs_x_peak:>6.3f} {ls_x_peak:>6.3f} {net_dx:>+8.3f}  {mark_a} {pred_a:<9} {mark_b} {pred_b}")

cap.release()

print(f"\n--- Approach A (body-relative position at peak) ---")
print(f"閾値({threshold})以上: {confident_rel}/{len(shots)}, 正解: {correct_rel}/{confident_rel} ({100*correct_rel/confident_rel:.0f}%)" if confident_rel else "0 confident")

print(f"\n--- Approach B (absolute net_dx, current) ---")
print(f"閾値({threshold})以上: {confident_dx}/{len(shots)}, 正解: {correct_dx}/{confident_dx} ({100*correct_dx/confident_dx:.0f}%)" if confident_dx else "0 confident")
