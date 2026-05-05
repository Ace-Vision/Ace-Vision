"""
backend/main.py — FastAPI entry point.
"""

import asyncio
import os
import shutil
import tempfile
from typing import List, Optional

from fastapi import FastAPI, File, Form, UploadFile, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from backend.schemas import AnalyseResponse, UserCreate, UserRead, SessionRead
from backend import pipeline, llm, db, schemas

app = FastAPI(title="Ace Vision API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def startup_event():
    db.init_db()

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
    user_id: Optional[int] = Form(None),
    sqlite_db: Session = Depends(db.get_db),
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

    coaching = await asyncio.to_thread(llm.get_coaching, result["deviation_scores"], skill_level)

    # Save to Database
    db_session = db.AnalysisSession(
        id=result["session_id"],
        user_id=user_id,
        sport_type=sport_type,
        video_path=result["overlay_path"],
        overall_score=result["overall_score"],
        coaching_feedback=coaching
    )
    sqlite_db.add(db_session)
    
    # Save deviations
    deviations = result["deviation_scores"].get("deviations", {})
    for joint_name, data in deviations.items():
        db_deviation = db.DeviationResult(
            session_id=result["session_id"],
            joint_name=joint_name,
            player_angle=data["player_angle"],
            expert_mean=data["expert_mean"],
            deviation_deg=data["deviation_deg"],
            severity_score=data["severity_score"]
        )
        sqlite_db.add(db_deviation)
    
    sqlite_db.commit()

    return AnalyseResponse(
        session_id=result["session_id"],
        deviation_scores=result["deviation_scores"],
        overlay_path=result["overlay_path"],
        sport_type=sport_type,
        overall_score=result["overall_score"],
        coaching=coaching,
    )

@app.post("/users", response_model=UserRead)
def create_user(user: UserCreate, sqlite_db: Session = Depends(db.get_db)):
    db_user = db.User(name=user.name, skill_level=user.skill_level)
    sqlite_db.add(db_user)
    sqlite_db.commit()
    sqlite_db.refresh(db_user)
    return db_user

@app.get("/users", response_model=List[UserRead])
def list_users(sqlite_db: Session = Depends(db.get_db)):
    return sqlite_db.query(db.User).all()

@app.get("/users/{user_id}/history", response_model=List[SessionRead])
def get_user_history(user_id: int, sqlite_db: Session = Depends(db.get_db)):
    return sqlite_db.query(db.AnalysisSession).filter(db.AnalysisSession.user_id == user_id).all()

@app.get("/sessions/{session_id}", response_model=SessionRead)
def get_session(session_id: str, sqlite_db: Session = Depends(db.get_db)):
    session = sqlite_db.query(db.AnalysisSession).filter(db.AnalysisSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session
