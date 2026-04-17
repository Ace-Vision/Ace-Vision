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
- Accept a sport_type and skill_level string
- Pick the correct sample video based on sport_type
- Run each pipeline stage sequentially, passing output to the next
- Return overlay video path, deviation scores dict, and session metadata
- Handle errors at each stage and report which step failed
"""

import glob
import uuid

from ml import extractor, calculator, scorer, renderer

# Maps each sport to its sample video folder.
# We pick the first video file found in the folder so the filename doesn't matter.
SAMPLE_DIRS = {
    "badminton":    "data/samples/badminton",
    "tennis_serve": "data/samples/tennis",
}


def _find_sample_video(sport_type: str) -> str:
    """
    Find the first .mp4 or .avi file in the sample folder for this sport.
    Raises FileNotFoundError if the folder is empty.
    """
    folder = SAMPLE_DIRS[sport_type]
    matches = glob.glob(f"{folder}/*.mp4") + glob.glob(f"{folder}/*.avi")
    if not matches:
        raise FileNotFoundError(
            f"No video files found in '{folder}'. "
            f"Add an .mp4 or .avi sample video for {sport_type}."
        )
    return matches[0]


def run_pipeline(sport_type: str, skill_level: str) -> dict:
    """
    Run the full ML pipeline for a given sport and return the results.

    Args:
        sport_type (str): Either "badminton" or "tennis_serve".
        skill_level (str): Player's self-reported level (e.g. "beginner").

    Returns:
        dict: Contains session_id, deviation_scores, overlay_path, sport_type.
    """

    # Step 1: Find the sample video for the chosen sport (any filename works)
    video_path = _find_sample_video(sport_type)

    # Step 2: Extract pose keypoints from every frame in the video
    keypoints_list = extractor.extract_keypoints(video_path)

    # Step 3: Calculate joint angles for every frame
    # (smoother and normaliser are skipped for now — not yet implemented)
    angles_list = calculator.calculate_angles(keypoints_list)

    # Step 4: Score the player's angles against the expert baselines for this sport.
    # Pass keypoints_list so the scorer can detect trophy + racket_drop checkpoints.
    deviation_scores = scorer.score_deviations(
        angles_list,
        sport_type,
        keypoints_list=keypoints_list,
    )

    # Step 5: Render the overlay video with colour-coded skeleton.
    # Pass angles_list so the renderer can show live per-frame values in the HUD.
    overlay_path = renderer.render_video(video_path, keypoints_list, deviation_scores, angles_list)

    # Give this analysis run a unique ID so results can be fetched later
    session_id = str(uuid.uuid4())

    return {
        "session_id": session_id,
        "deviation_scores": deviation_scores,
        "overlay_path": overlay_path,
        "sport_type": sport_type,
    }
