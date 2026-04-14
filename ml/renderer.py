"""
ml/renderer.py — Skeleton overlay and colour-coded deviation rendering.

Draws visual feedback on each video frame showing the player's pose with
colour-coded joint indicators based on deviation severity.

Drawing order per frame:
1. White skeleton lines (MediaPipe POSE_CONNECTIONS, 60% opacity)
2. Colour-coded joint dots for the 9 serve joints:
   - Green  #4CAF50 — severity < 0.3
   - Amber  #FF9800 — severity 0.3–0.6
   - Red    #F44336 — severity > 0.6
3. Small angle arc at each joint (radius 30px, matching colour)
4. HUD top-right: top 3 deviations with joint name + degrees off

Key responsibilities:
- Accept original video frames, keypoints, and deviation scores
- Draw skeleton connections with transparency
- Draw coloured circles at each of the 9 joints based on severity
- Draw angle arcs at joint vertices
- Render text HUD overlay with top deviations
- Encode output as an MP4 video file
"""
