#!/usr/bin/env python3
"""
Test script for ml/scorer.py
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from ml.extractor import extract_keypoints
from ml.calculator import calculate_angles
from ml.scorer import score_deviations

def test_scorer():
    video_path = "data/samples/badminton.mp4"

    if not os.path.exists(video_path):
        print(f"Video not found: {video_path}")
        return

    print("Extracting keypoints...")
    keypoints = extract_keypoints(video_path)
    print(f"Extracted from {len(keypoints)} frames.")

    print("Calculating angles...")
    angles = calculate_angles(keypoints)
    print(f"Calculated angles for {len(angles)} frames.")

    print("Scoring deviations...")
    scores = score_deviations(angles)
    print(f"Peak frame: {scores.get('peak_frame')}")
    print("Deviations:")
    for joint, data in scores.get('deviations', {}).items():
        print(f"  {joint}: {data['angle']:.2f} deg, deviation {data['deviation_deg']:.2f}, severity {data['severity_score']:.2f}, {data['direction']}")

    print("Test passed!")

if __name__ == "__main__":
    test_scorer()