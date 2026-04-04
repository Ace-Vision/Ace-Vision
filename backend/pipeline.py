"""
backend/pipeline.py — Orchestrates the full analysis pipeline.

Chains all ml/ modules in order to process a serve video end-to-end:
1. extractor  — extract per-frame keypoints from video
2. smoother   — smooth keypoint time series
3. normaliser — hip-centred, scale-free normalisation
4. calculator — compute joint angles at each frame
5. scorer     — compare angles vs expert baselines → deviation scores
6. renderer   — draw skeleton overlay with colour-coded deviations

Key responsibilities:
- Accept a video file path and skill_level string
- Run each pipeline stage sequentially, passing output to the next
- Return overlay video path, deviation scores dict, and session metadata
- Handle errors at each stage and report which step failed
"""
