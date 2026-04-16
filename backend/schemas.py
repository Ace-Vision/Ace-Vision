"""
backend/schemas.py — Pydantic models for request/response validation.

Defines all data shapes used by the API and internal pipeline:
- AnalyseRequest / AnalyseResponse (video upload + results)
- CoachingRequest / CoachingResponse (LLM coaching flow)
- DeviationResult (per-joint deviation data)
- CorrectionItem (single coaching correction from LLM)
- CoachingOutput (full LLM response shape)

Key responsibilities:
- Validate incoming API request bodies
- Serialise outgoing API responses
- Enforce field types, ranges, and enums (e.g. skill_level)
- Provide JSON-serialisable models for internal pipeline data
"""

from typing import Literal
from pydantic import BaseModel

# SportType is not a class — it's just a name for a type.
# Using Literal means Pydantic will reject anything that isn't one of these two strings.
SportType = Literal["badminton", "tennis_serve"]


class AnalyseRequest(BaseModel):
    """
    Sent by the frontend when the user clicks Analyse.

    Fields:
        sport_type  — which sport's baselines to score against.
        skill_level — player's self-reported level ("beginner", "intermediate", "advanced").
    """
    sport_type: SportType
    skill_level: str


class AnalyseResponse(BaseModel):
    """
    Returned after the full pipeline has run.

    Fields:
        session_id       — unique ID for this analysis run.
        deviation_scores — dict produced by scorer.score_deviations().
        overlay_path     — path to the rendered overlay video.
        sport_type       — echoed back so the frontend knows which sport these results belong to.
        overall_score    — 0-100 score derived from average severity (100 = perfect form).
    """
    session_id: str
    deviation_scores: dict
    overlay_path: str
    sport_type: SportType
    overall_score: int
