"""
backend/main.py — FastAPI entry point.

Endpoints:
- POST /analyse  — Upload a video file, run the full ML pipeline,
                   return deviation scores + overall score + session_id.
"""

import asyncio
import os
import shutil
import tempfile
import sys

# Ensure project root is in Python path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI, File, Form, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from backend.schemas import AnalyseResponse
from backend import pipeline, vlm
from ml import renderer

API_KEY = os.environ.get("GEMINI_API_KEY", "")
if not API_KEY:
    raise RuntimeError("GEMINI_API_KEY environment variable is not set")
gemini = vlm.gemini_model(API_KEY)

app = FastAPI(title="Ace Vision API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

_FRONTEND_BUILD = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend", "build")
if os.path.isdir(_FRONTEND_BUILD):
    app.mount("/static", StaticFiles(directory=os.path.join(_FRONTEND_BUILD, "static")), name="static")


@app.get("/overlay/{session_id}")
async def get_overlay(session_id: str):
    path = os.path.join("uploads", f"{session_id}_overlay.mp4")
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Overlay not found")
    return FileResponse(path, media_type="video/mp4")


@app.post("/analyse", response_model=AnalyseResponse)
async def analyse(
    file: UploadFile = File(...),
    sport_type: str = Form(...),
    skill_level: str = Form(...),
):
    valid_sports = ("badminton", "tennis_serve")
    if sport_type not in valid_sports:
        raise HTTPException(status_code=422, detail=f"sport_type must be one of {valid_sports}")

    suffix = os.path.splitext(file.filename)[1] or ".mp4"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = tmp.name

    try:
        result = await asyncio.to_thread(pipeline.run_pipeline, tmp_path, sport_type, skill_level)
    except Exception as exc:
        os.unlink(tmp_path)
        import traceback; traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(exc))

    actual_video_path = os.path.join("uploads", f"{result['session_id']}_overlay.mp4")
    coaching = await asyncio.to_thread(gemini.get_coaching, result["deviation_scores"], actual_video_path, skill_level)

    # Re-render overlay with highlight joint from VLM structured output
    highlight_joint = coaching.get("highlight_joint") if coaching else None
    if highlight_joint:
        try:
            highlighted_tmp = await asyncio.to_thread(
                renderer.render_video,
                tmp_path,
                result["keypoints_list"],
                result["deviation_scores"],
                result["angles_list"],
                highlight_joint,
            )
            os.replace(highlighted_tmp, actual_video_path)
        except Exception:
            pass  # fallback: keep original overlay

    os.unlink(tmp_path)

    return AnalyseResponse(
        session_id=result["session_id"],
        deviation_scores=result["deviation_scores"],
        overlay_path=result["overlay_path"],
        sport_type=sport_type,
        overall_score=result["overall_score"],
        coaching=coaching,
    )


# Catch-all: serve React SPA for all non-API routes (must be last)
if os.path.isdir(_FRONTEND_BUILD):
    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_frontend(full_path: str):
        return FileResponse(os.path.join(_FRONTEND_BUILD, "index.html"))
