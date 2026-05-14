"""
backend/pipeline.py — Orchestrates the full analysis pipeline.

Chains all ml/ modules in order to process a serve video end-to-end:
1. extractor  — extract per-frame keypoints from video (VIDEO mode, BGR→RGB)
2. smoother   — Gaussian smoothing to reduce keypoint jitter
3. normaliser — hip-centred, torso-length normalisation
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

import glob
import os
import shutil
import uuid

from ml import extractor, smoother, normaliser, calculator, scorer, renderer

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


def run_pipeline(video_path: str, sport_type: str, skill_level: str = "") -> dict:
    """
    Run the full ML pipeline on the given video file and return the results.

    Args:
        video_path (str): Path to the uploaded video file.
        sport_type (str): Either "badminton" or "tennis_serve".
        skill_level (str): Player's self-reported level.

    Returns:
        dict: Contains session_id, deviation_scores, overlay_path, sport_type, overall_score.
    """

    # Step 1: Extract pose keypoints (VIDEO mode, BGR→RGB)
    import cv2 as _cv2
    _cap = _cv2.VideoCapture(video_path)
    fps = _cap.get(_cv2.CAP_PROP_FPS) or 30.0
    _cap.release()

    raw_keypoints = extractor.extract_keypoints(video_path)

    # Step 2: Smooth keypoints to suppress per-frame jitter
    smoothed_keypoints = smoother.smooth_keypoints(raw_keypoints)

    # Step 3: Normalise to hip-centred, torso-length coordinates
    # Makes angles comparable across different camera distances and body sizes.
    # The renderer still needs the raw (pixel-space) keypoints for drawing, so
    # we keep both and pass the normalised version to angle calculation/scoring.
    norm_keypoints = normaliser.normalise_keypoints(smoothed_keypoints)

    # Step 4: Calculate joint angles on normalised keypoints
    angles_list = calculator.calculate_angles(norm_keypoints)

    # Step 5: Score the player's angles against the expert baselines for this sport.
    # Pass normalised keypoints so checkpoint detection uses smoothed coordinates.
    deviation_scores = scorer.score_deviations(
        angles_list,
        sport_type,
        keypoints_list=norm_keypoints,
        fps=fps,
    )

    # Step 6: Render overlay using raw (smoothed, pixel-space) keypoints
    # so the skeleton sits on the actual body rather than the normalised coords.
    session_id = str(uuid.uuid4())
    overlay_tmp = renderer.render_video(video_path, smoothed_keypoints, deviation_scores, angles_list)

    # Move overlay to persistent uploads directory so it can be served over HTTP.
    os.makedirs("uploads", exist_ok=True)
    overlay_dest = os.path.join("uploads", f"{session_id}_overlay.mp4")
    shutil.move(overlay_tmp, overlay_dest)

    # Step 6: Weighted overall score across all checkpoints.
    # contact carries the most weight since it's the decisive moment;
    # the prep and follow-through contribute but matter less.
    _WEIGHTS = {
        "contact":        0.5,
        "backswing":      0.3,   # badminton
        "trophy":         0.3,   # tennis
        "follow_through": 0.2,   # badminton
        "racket_drop":    0.2,   # tennis
    }

    def _cp_score(cp_data):
        if not cp_data:
            return None
        devs = cp_data.get("deviations", {})
        if not devs:
            return None
        avg_sev = sum(d["severity_score"] for d in devs.values()) / len(devs)
        return 1 - avg_sev

    checkpoints = deviation_scores.get("checkpoints", {})
    weighted_sum = 0.0
    weight_total = 0.0
    for name, weight in _WEIGHTS.items():
        score = _cp_score(checkpoints.get(name))
        if score is not None:
            weighted_sum += score * weight
            weight_total += weight

    if weight_total > 0:
        overall_score = max(0, min(100, round(weighted_sum / weight_total * 100)))
    else:
        overall_score = 0

    return {
        "session_id": session_id,
        "deviation_scores": deviation_scores,
        "overlay_path": f"/overlay/{session_id}",
        "sport_type": sport_type,
        "overall_score": overall_score,
        "keypoints_list": smoothed_keypoints,
        "angles_list": angles_list,
    }
