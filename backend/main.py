"""
backend/main.py — FastAPI entry point.

Endpoints:
- POST /analyse  — Upload a video file, run the full ML pipeline,
                   return deviation scores + overall score + session_id.
"""

import os
import shutil
import tempfile

from fastapi import FastAPI, File, Form, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from backend.schemas import AnalyseResponse
from backend import pipeline

app = FastAPI(title="Ace Vision API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


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
        result = pipeline.run_pipeline(tmp_path, sport_type, skill_level)
    finally:
        os.unlink(tmp_path)

    return AnalyseResponse(
        session_id=result["session_id"],
        deviation_scores=result["deviation_scores"],
        overlay_path=result["overlay_path"],
        sport_type=sport_type,
        overall_score=result["overall_score"],
    )
