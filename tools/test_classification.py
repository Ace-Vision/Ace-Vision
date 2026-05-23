"""
Test the new classify_shots_from_video() against known ground truth.
Ground truth backhands (1-indexed): 2, 3, 5, 9, 11, 17, 20, 28
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from backend import shot_detector

BACKHAND_SHOTS = {2, 3, 5, 9, 11, 17, 20, 28}  # 1-indexed
VIDEO_PATH = "data/samples/badminton/badminton_match.mov"

print("Step 1: Extracting keypoints (strided)...")
keypoints_list, fps = shot_detector.extract_keypoints_strided(VIDEO_PATH)
print(f"  fps={fps:.1f}, frames={len(keypoints_list)}")

print("\nStep 2: Detecting shots...")
shots = shot_detector.detect_shots(keypoints_list, fps)
print(f"  Detected {len(shots)} shots")

print("\nStep 3: Classifying with new video-frame method...")
shot_detector.classify_shots_from_video(VIDEO_PATH, shots, fps)

print("\n--- Results ---")
correct = 0
total_confident = 0
threshold = shot_detector.CLASSIFY_CONFIDENCE_THRESHOLD

for i, s in enumerate(shots):
    num = i + 1
    true_type = "backhand" if num in BACKHAND_SHOTS else "forehand"
    pred_type = s["shot_type"]
    conf = s["confidence"]
    confident = conf >= threshold
    match = "✓" if pred_type == true_type else "✗"

    if confident:
        total_confident += 1
        if pred_type == true_type:
            correct += 1

    marker = f"[conf={conf:.2f}]" + (" *" if not confident else "")
    print(f"  Shot {num:2d}: true={true_type:<9} pred={pred_type:<9} {match} {marker}")

print(f"\n閾値({threshold})以上: {total_confident}/{len(shots)}本")
print(f"うち正解: {correct}/{total_confident} ({100*correct/total_confident:.0f}% accuracy)" if total_confident else "0 confident shots")
