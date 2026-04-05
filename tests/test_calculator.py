#!/usr/bin/env python3
"""
Test script for ml/calculator.py
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from ml.extractor import extract_keypoints
from ml.calculator import calculate_angles

def test_calculator():
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

    # Show sample
    if angles:
        first_with_angles = next((i for i, ang in enumerate(angles) if ang), None)
        if first_with_angles is not None:
            print(f"First frame with angles: {first_with_angles}")
            sample_angles = angles[first_with_angles]
            for joint, angle in sample_angles.items():
                if angle is not None:
                    print(f"  {joint}: {angle:.2f} degrees")
        else:
            print("No angles calculated.")

    print("Test passed!")

if __name__ == "__main__":
    test_calculator()