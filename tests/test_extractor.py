#!/usr/bin/env python3
"""
Test script for ml/extractor.py
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from ml.extractor import extract_keypoints

def test_extractor():
    # Note: This test requires a sample video file.
    # For now, we'll just test the import and function signature.
    # To fully test, place a video file in data/samples/ and update the path.

    video_path = "data/samples/badminton.mp4"  # Use the dummy video

    if not os.path.exists(video_path):
        print(f"Sample video not found at {video_path}. Please add a video file for testing.")
        return

    try:
        keypoints = extract_keypoints(video_path)
        print(f"Extracted keypoints from {len(keypoints)} frames.")
        
        # Count frames with landmarks
        frames_with_landmarks = sum(1 for kp in keypoints if kp)
        print(f"Frames with detected landmarks: {frames_with_landmarks}/{len(keypoints)}")
        
        print(f"Keypoints extracted successfully.")
        
        if keypoints:
            # Find first frame with landmarks
            first_with_landmarks = next((i for i, kp in enumerate(keypoints) if kp), None)
            if first_with_landmarks is not None:
                print(f"First frame with landmarks: {first_with_landmarks}")
                first_frame = keypoints[first_with_landmarks]
                print("Sample keypoint data from first frame with landmarks:")
                # Print a few landmarks
                for landmark in ['nose', 'left_shoulder', 'right_shoulder']:
                    if landmark in first_frame:
                        print(f"  {landmark}: {first_frame[landmark]}")
            else:
                print("No landmarks detected in any frame.")
        print("Test passed!")
    except Exception as e:
        print(f"Test failed: {e}")

if __name__ == "__main__":
    test_extractor()