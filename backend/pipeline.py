"""
backend/pipeline.py — Orchestrates the full analysis pipeline.

Chains all ml/ modules in order to process a serve video end-to-end:
1. extractor  — extract per-frame keypoints from video
2. smoother   — smooth keypoint time series (not yet implemented, skipped for now)
3. normaliser — hip-centred, scale-free normalisation (not yet implemented, skipped for now)
4. calculator — compute joint angles at each frame
5. scorer     — compare angles vs expert baselines → deviation scores
6. renderer   — draw skeleton overlay with colour-coded deviations

Key responsibilities:
- Accept an uploaded video path, sport_type, and skill_level
- Run each pipeline stage sequentially, passing output to the next
- Compute an overall score (0-100) from average deviation severity
- Return overlay video path, deviation scores dict, overall score, and session metadata
- Handle errors at each stage and report which step failed
"""

import uuid

from ml import extractor, calculator, scorer, renderer


def run_pipeline(video_path: str, sport_type: str) -> dict:
    """
    Run the full ML pipeline on the given video file and return the results.

    Args:
        video_path (str): Path to the uploaded video file.
        sport_type (str): Either "badminton" or "tennis_serve".

    Returns:
        dict: Contains session_id, deviation_scores, overlay_path, sport_type, overall_score.
    """

    # Step 1: Extract pose keypoints from every frame in the video
    keypoints_list = extractor.extract_keypoints(video_path)

    # Step 2: Calculate joint angles for every frame
    # (smoother and normaliser are skipped for now — not yet implemented)
    angles_list = calculator.calculate_angles(keypoints_list)

    # Step 3: Score the player's angles against the expert baselines for this sport
    deviation_scores = scorer.score_deviations(angles_list, sport_type)

    # Step 4: Render the overlay video with colour-coded skeleton
    overlay_path = renderer.render_video(video_path, keypoints_list, deviation_scores)

    # Step 5: Compute overall score (100 = perfect, 0 = all joints at max deviation)
    deviations = deviation_scores.get("deviations", {})
    if deviations:
        avg_severity = sum(d["severity_score"] for d in deviations.values()) / len(deviations)
        overall_score = max(0, round((1 - avg_severity) * 100))
    else:
        overall_score = 0

    session_id = str(uuid.uuid4())

    return {
        "session_id": session_id,
        "deviation_scores": deviation_scores,
        "overlay_path": overlay_path,
        "sport_type": sport_type,
        "overall_score": overall_score,
    }
