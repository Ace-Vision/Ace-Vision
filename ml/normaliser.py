"""
ml/normaliser.py — Hip-centred, scale-free normalisation.

Translates all keypoints so the midpoint of the left and right hips is the
origin, then scales by torso length (hip-midpoint to shoulder-midpoint) so
that players of different sizes produce comparable coordinates.

Key responsibilities:
- Compute hip midpoint per frame as the new origin
- Translate all keypoints relative to hip midpoint
- Compute torso length (hip midpoint → shoulder midpoint)
- Divide all coordinates by torso length for scale invariance
- Return normalised keypoint time series
"""
