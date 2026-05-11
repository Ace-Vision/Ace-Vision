"""
backend/main.py — FastAPI entry point.
"""

import asyncio
import os
import sys
import shutil
import tempfile
from datetime import datetime, timedelta
from typing import List, Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI, File, Form, UploadFile, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from jose import JWTError, jwt
from passlib.context import CryptContext

from backend.schemas import (
    AnalyseResponse, UserCreate, UserRead, SessionRead,
    UserRegister, UserLogin, TokenResponse,
)
from backend import pipeline, vlm, db

# ── JWT config ────────────────────────────────────────────────────────────────
SECRET_KEY = os.getenv("SECRET_KEY", "ace-vision-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 days

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)

# ── App ───────────────────────────────────────────────────────────────────────
API_KEY = "AIzaSyDxZjxpnb0JIotRIFVVplb_GmOtdHO9Enk"
gemini = vlm.gemini_model(API_KEY)

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

# ── Auth helpers ──────────────────────────────────────────────────────────────

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)

def create_access_token(data: dict) -> str:
    payload = data.copy()
    payload["exp"] = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def get_current_user(token: str = Depends(oauth2_scheme), sqlite_db: Session = Depends(db.get_db)):
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: int = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
    user = sqlite_db.query(db.User).filter(db.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user

# ── Auth endpoints ────────────────────────────────────────────────────────────

@app.post("/auth/register", response_model=TokenResponse)
def register(body: UserRegister, sqlite_db: Session = Depends(db.get_db)):
    if sqlite_db.query(db.User).filter(db.User.email == body.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")
    user = db.User(
        name=body.name,
        email=body.email,
        hashed_password=hash_password(body.password),
        skill_level=body.skill_level,
    )
    sqlite_db.add(user)
    sqlite_db.commit()
    sqlite_db.refresh(user)
    token = create_access_token({"sub": user.id})
    return TokenResponse(access_token=token, user_id=user.id, name=user.name, email=user.email)

@app.post("/auth/login", response_model=TokenResponse)
def login(body: UserLogin, sqlite_db: Session = Depends(db.get_db)):
    user = sqlite_db.query(db.User).filter(db.User.email == body.email).first()
    if not user or not verify_password(body.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    token = create_access_token({"sub": user.id})
    return TokenResponse(access_token=token, user_id=user.id, name=user.name, email=user.email)

@app.get("/auth/me", response_model=UserRead)
def me(current_user: db.User = Depends(get_current_user)):
    return current_user

# ── Overlay ───────────────────────────────────────────────────────────────────

@app.get("/overlay/{session_id}")
async def get_overlay(session_id: str):
    path = os.path.join("uploads", f"{session_id}_overlay.mp4")
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Overlay not found")
    return FileResponse(path, media_type="video/mp4")

# ── Analysis ──────────────────────────────────────────────────────────────────

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

    actual_video_path = os.path.join("uploads", f"{result['session_id']}_overlay.mp4")
    coaching = await asyncio.to_thread(gemini.get_coaching, result["deviation_scores"], actual_video_path, skill_level)

    db_session = db.AnalysisSession(
        id=result["session_id"],
        user_id=user_id,
        sport_type=sport_type,
        video_path=result["overlay_path"],
        overall_score=result["overall_score"],
        coaching_feedback=coaching,
    )
    sqlite_db.add(db_session)

    deviations = result["deviation_scores"].get("deviations", {})
    for joint_name, data in deviations.items():
        sqlite_db.add(db.DeviationResult(
            session_id=result["session_id"],
            joint_name=joint_name,
            player_angle=data["player_angle"],
            expert_mean=data["expert_mean"],
            deviation_deg=data["deviation_deg"],
            severity_score=data["severity_score"],
        ))

    sqlite_db.commit()

    return AnalyseResponse(
        session_id=result["session_id"],
        deviation_scores=result["deviation_scores"],
        overlay_path=result["overlay_path"],
        sport_type=sport_type,
        overall_score=result["overall_score"],
        coaching=coaching,
    )

# ── Users ─────────────────────────────────────────────────────────────────────

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
