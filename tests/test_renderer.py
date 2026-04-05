#!/usr/bin/env python3
"""
Test script for rendering video with keypoints overlay
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from ml.extractor import extract_keypoints
from ml.renderer import render_video

def test_render():
    video_path = "data/samples/expert_clear.mp4"

    if not os.path.exists(video_path):
        print(f"Video not found: {video_path}")
        return

    print("Extracting keypoints...")
    keypoints = extract_keypoints(video_path)
    print(f"Extracted from {len(keypoints)} frames.")

    print("Rendering video...")
    output_path = render_video(video_path, keypoints)
    print(f"Rendered video saved to: {output_path}")

if __name__ == "__main__":
    test_render()