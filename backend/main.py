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

from backend.schemas import AnalyseResponse
from backend import pipeline, vlm

API_KEY = "AIzaSyDxZjxpnb0JIotRIFVVplb_GmOtdHO9Enk"
gemini = vlm.gemini_model(API_KEY)

app = FastAPI(title="Ace Vision API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


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
    else:
        os.unlink(tmp_path)

    actual_video_path = os.path.join("uploads", f"{result['session_id']}_overlay.mp4")
    coaching = await asyncio.to_thread(gemini.get_coaching, result["deviation_scores"], actual_video_path, skill_level)

    return AnalyseResponse(
        session_id=result["session_id"],
        deviation_scores=result["deviation_scores"],
        overlay_path=result["overlay_path"],
        sport_type=sport_type,
        overall_score=result["overall_score"],
        coaching=coaching,
    )
