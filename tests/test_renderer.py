#!/usr/bin/env python3
"""
Test script for rendering video with keypoints overlay
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from ml.extractor import extract_keypoints
from ml.calculator import calculate_angles
from ml.scorer import score_deviations
from ml.renderer import render_video

def test_render():
    video_path = "data/samples/clear.mp4"

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

    print("Rendering video...")
    output_path = render_video(video_path, keypoints, scores)
    print(f"Rendered video saved to: {output_path}")

if __name__ == "__main__":
    test_render()