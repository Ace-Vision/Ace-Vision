"""
backend/main.py — FastAPI entry point.

Creates the FastAPI application instance and registers route handlers.

Endpoints:
- POST /analyse  — Upload a serve video, run the full ML pipeline, return
                   overlay video + deviation scores JSON + session_id.
- POST /coaching — Given a session_id and deviation scores, call the LLM
                   and return structured coaching JSON (2 corrections + summary).

Key responsibilities:
- Initialise FastAPI app with CORS and metadata
- Define request/response routes using Pydantic schemas
- Handle video file upload and temporary file management
- Return JSON responses and video file downloads
"""
