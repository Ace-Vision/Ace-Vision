"""
ml/calculator.py — Joint angle computation.

Computes angles at the 9 serve-specific joints using the arccos dot-product
formula: θ = arccos(dot(v1, v2) / (|v1| × |v2|)), where v1 and v2 point
away from the vertex joint.

Joints analysed:
- Right/left elbow flexion
- Right/left shoulder abduction
- Right/left knee flexion
- Trunk lateral tilt
- Hip-shoulder separation
- Wrist extension

Key responsibilities:
- Accept normalised keypoint data per frame
- For each joint, extract the three relevant keypoints (two limb endpoints + vertex)
- Compute the angle at the vertex using the vector dot-product formula
- Return per-frame angle dict for all 9 joints
"""
