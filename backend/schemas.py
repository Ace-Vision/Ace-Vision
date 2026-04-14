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
