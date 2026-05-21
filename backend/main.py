"""
backend/main.py — FastAPI entry point.

Endpoints:
- POST /auth/register   — Register a new user, returns JWT token
- POST /auth/login      — Login, returns JWT token
- GET  /auth/me         — Current user info
- GET  /overlay/{id}    — Serve overlay video
- GET  /frame/{id}/{cp} — Serve checkpoint frame JPEG
- POST /analyse         — Upload video, run ML pipeline, return results + store in DB
- GET  /users           — List users
- GET  /users/{id}/history — User's analysis history
- GET  /sessions/{id}   — Session detail
"""

import asyncio
import logging
import os
import sys
import shutil
import tempfile
import cv2
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from typing import List, Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI, File, Form, UploadFile, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from jose import JWTError, jwt
from passlib.context import CryptContext

from backend.schemas import (
    AnalyseResponse, UserCreate, UserRead, SessionRead,
    UserRegister, UserLogin, TokenResponse,
)
from backend import pipeline, vlm, db, vector_db
from backend.upload_validation import validate_upload_metadata, validate_video_duration, MAX_BYTES
from ml import renderer

logger = logging.getLogger(__name__)

SECRET_KEY = os.getenv("SECRET_KEY", "ace-vision-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)

API_KEY = os.environ.get("GEMINI_API_KEY", "")
if not API_KEY:
    raise RuntimeError("GEMINI_API_KEY environment variable is not set")
gemini = vlm.gemini_model(API_KEY)

_FRONTEND_BUILD = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend", "build")


@asynccontextmanager
async def lifespan(app: FastAPI):
    db.init_db()
    yield


app = FastAPI(title="Ace Vision API", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

if os.path.isdir(_FRONTEND_BUILD):
    app.mount("/static", StaticFiles(directory=os.path.join(_FRONTEND_BUILD, "static")), name="static")


def backfill_vector_db() -> None:
    """Index any AnalysisSession rows not yet present in the vector DB."""
    vdb = vector_db.get_vlm_vector_db()
    sqlite_db = db.SessionLocal()
    try:
        sessions = (
            sqlite_db.query(db.AnalysisSession)
            .filter(db.AnalysisSession.coaching_feedback.isnot(None))
            .all()
        )
        new_entries = 0
        for session in sessions:
            if session.id in vdb._indexed_session_ids:
                continue
            coaching = session.coaching_feedback
            coaching_text = coaching.get("advice", str(coaching)) if isinstance(coaching, dict) else str(coaching)
            joint_scores = {dev.joint_name: dev.severity_score for dev in session.deviations}
            joint_scores["overall"] = float(session.overall_score)
            vdb.add_vlm_output(
                vlm_feedback=coaching_text,
                scores=joint_scores,
                session_id=session.id,
                sport=session.sport_type,
                user_id=session.user_id,
            )
            new_entries += 1
        if new_entries:
            vector_db.save_vlm_vector_db()
            print(f"Vector DB: backfilled {new_entries} session(s).")
    finally:
        sqlite_db.close()

@app.on_event("startup")
def startup_event():
    db.init_db()
    vector_db.get_vlm_vector_db()  # load persisted vector DB from disk
    backfill_vector_db()

@app.on_event("shutdown")
def shutdown_event():
    vector_db.save_vlm_vector_db()


def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)

def create_access_token(data: dict) -> str:
    payload = data.copy()
    payload["exp"] = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
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


async def _save_upload(file: UploadFile) -> tuple[str, int]:
    """Stream upload to a temp file with size cap. Returns (path, bytes_written)."""
    suffix = (os.path.splitext(file.filename or "")[1] or ".mp4").lower()
    bytes_written = 0

    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        while chunk := await file.read(1024 * 1024):
            bytes_written += len(chunk)
            if bytes_written > MAX_BYTES:
                tmp_path = tmp.name
                os.unlink(tmp_path)
                raise HTTPException(
                    status_code=413,
                    detail=f"Upload exceeds maximum size ({MAX_BYTES // (1024 * 1024)} MB).",
                )
            tmp.write(chunk)
        return tmp.name, bytes_written


@app.post("/auth/register", response_model=TokenResponse)
def register(body: UserRegister, sqlite_db: Session = Depends(db.get_db)):
    if sqlite_db.query(db.User).filter(db.User.email == body.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")
    user = db.User(
        name=body.name, email=body.email,
        hashed_password=hash_password(body.password), skill_level=body.skill_level,
    )
    sqlite_db.add(user); sqlite_db.commit(); sqlite_db.refresh(user)
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


def _save_checkpoint_frames(session_id: str, overlay_path: str, checkpoints: dict):
    cap = cv2.VideoCapture(overlay_path)
    for name, data in checkpoints.items():
        if not data:
            continue
        cap.set(cv2.CAP_PROP_POS_FRAMES, data["frame"])
        ret, frame = cap.read()
        if ret:
            cv2.imwrite(os.path.join("uploads", f"{session_id}_frame_{name}.jpg"), frame)
    cap.release()


@app.get("/reference/{sport_type}")
async def get_reference(sport_type: str):
    paths = {
        "badminton":    "data/samples/badminton/clear_2.mov",
        "tennis_serve": "data/samples/tennis/test_tennis.mp4",
    }
    path = paths.get(sport_type)
    if not path or not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Reference video not found")
    media_type = "video/quicktime" if path.endswith(".mov") else "video/mp4"
    return FileResponse(path, media_type=media_type)


@app.get("/overlay/{session_id}")
async def get_overlay(session_id: str):
    path = os.path.join("uploads", f"{session_id}_overlay.mp4")
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Overlay not found")
    return FileResponse(path, media_type="video/mp4")

@app.get("/frame/{session_id}/{checkpoint}")
async def get_frame(session_id: str, checkpoint: str):
    path = os.path.join("uploads", f"{session_id}_frame_{checkpoint}.jpg")
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Frame not found")
    return FileResponse(path, media_type="image/jpeg")


@app.post("/analyse", response_model=AnalyseResponse)
async def analyse(
    file: UploadFile = File(...),
    sport_type: str = Form(...),
    skill_level: str = Form(...),
    user_id: Optional[int] = Form(None),
    sqlite_db: Session = Depends(db.get_db),
):
    if sport_type not in ("badminton", "tennis_serve"):
        raise HTTPException(status_code=422, detail="sport_type must be badminton or tennis_serve")

    try:
        validate_upload_metadata(file.filename, file.content_type, 0)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    tmp_path = None
    try:
        tmp_path, bytes_written = await _save_upload(file)
        validate_upload_metadata(file.filename, file.content_type, bytes_written)
        validate_video_duration(tmp_path)
    except ValueError as exc:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise HTTPException(status_code=422, detail=str(exc))
    except HTTPException:
        raise
    except Exception:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise

    try:
        result = await asyncio.to_thread(pipeline.run_pipeline, tmp_path, sport_type, skill_level)
    except Exception as exc:
        os.unlink(tmp_path)
        logger.exception("Pipeline failed")
        raise HTTPException(status_code=500, detail=str(exc))

    actual_video_path = os.path.join("uploads", f"{result['session_id']}_overlay.mp4")

    # Query vector DB for similar past feedback to use as RAG context
    vdb = vector_db.get_vlm_vector_db()
    similar = vdb.search(
        query=f"{sport_type} coaching feedback",
        k=3,
        sport=sport_type,
        user_id=user_id,
    )
    rag_context = "\n---\n".join(r["matched_chunk"] for r in similar)

    coaching = await asyncio.to_thread(
        gemini.get_coaching, result["deviation_scores"], actual_video_path, skill_level, sport_type, rag_context,
    )

    highlight_applied = False
    highlight_joint = coaching.get("highlight_joint") if coaching else None
    if highlight_joint:
        try:
            highlighted_tmp = await asyncio.to_thread(
                renderer.render_video, tmp_path,
                result["keypoints_list"], result["deviation_scores"], result["angles_list"], highlight_joint,
            )
            os.replace(highlighted_tmp, actual_video_path)
            highlight_applied = True
        except Exception:
            logger.exception(
                "Highlight re-render failed for session %s joint %s",
                result["session_id"],
                highlight_joint,
            )

    os.unlink(tmp_path)

    await asyncio.to_thread(
        _save_checkpoint_frames, result["session_id"], actual_video_path,
        result["deviation_scores"].get("checkpoints", {}),
    )

    sqlite_db.add(db.AnalysisSession(
        id=result["session_id"], user_id=user_id, sport_type=sport_type,
        video_path=result["overlay_path"], overall_score=result["overall_score"],
        coaching_feedback=coaching,
    ))
    for joint_name, data in result["deviation_scores"].get("deviations", {}).items():
        sqlite_db.add(db.DeviationResult(
            session_id=result["session_id"], joint_name=joint_name,
            player_angle=data.get("angle"), expert_mean=None,
            deviation_deg=data.get("deviation_deg"), severity_score=data.get("severity_score"),
        ))
    sqlite_db.commit()

    # Index coaching output in vector DB for future RAG retrieval
    if coaching:
        coaching_text = coaching.get("advice", str(coaching))
        joint_scores = {
            joint: data["severity_score"]
            for joint, data in result["deviation_scores"].get("deviations", {}).items()
        }
        joint_scores["overall"] = float(result["overall_score"])
        vdb.add_vlm_output(
            vlm_feedback=coaching_text,
            scores=joint_scores,
            session_id=result["session_id"],
            sport=sport_type,
            user_id=user_id,
        )
        await asyncio.to_thread(vector_db.save_vlm_vector_db)

    return AnalyseResponse(
        session_id=result["session_id"], deviation_scores=result["deviation_scores"],
        overlay_path=result["overlay_path"], sport_type=sport_type,
        overall_score=result["overall_score"], coaching=coaching,
        highlight_applied=highlight_applied,
    )


@app.post("/users", response_model=UserRead)
def create_user(user: UserCreate, sqlite_db: Session = Depends(db.get_db)):
    db_user = db.User(name=user.name, skill_level=user.skill_level)
    sqlite_db.add(db_user); sqlite_db.commit(); sqlite_db.refresh(db_user)
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


# ── Vector DB endpoints ───────────────────────────────────────────────────────

@app.get("/coaching/search")
def search_coaching(
    q: str,
    sport: Optional[str] = None,
    user_id: Optional[int] = None,
    k: int = 5,
):
    """Semantic search over stored VLM coaching feedback."""
    vdb = vector_db.get_vlm_vector_db()
    results = vdb.search(q, k=k, sport=sport, user_id=user_id)
    return [
        {
            "session_id": r["entry"]["session_id"],
            "sport": r["entry"]["sport"],
            "matched_chunk": r["matched_chunk"],
            "similarity_score": r["similarity_score"],
            "scores": r["entry"]["scores"],
            "created_at": r["entry"]["created_at"],
        }
        for r in results
    ]

@app.get("/users/{user_id}/progress")
def get_user_progress(user_id: int, sport: Optional[str] = None):
    """Return mean deviation scores across all past sessions for a user."""
    vdb = vector_db.get_vlm_vector_db()
    return vdb.aggregate_scores(user_id=user_id, sport=sport)

@app.get("/users/{user_id}/progress/chart")
def get_user_progress_chart(
    user_id: int,
    sport: Optional[str] = None,
    sqlite_db: Session = Depends(db.get_db),
    current_user: db.User = Depends(get_current_user),
):
    """Return per-session overall scores ordered by date, for charting."""
    query = (
        sqlite_db.query(db.AnalysisSession)
        .filter(db.AnalysisSession.user_id == user_id)
    )
    if sport:
        query = query.filter(db.AnalysisSession.sport_type == sport)
    if current_user.id != user_id:
        raise HTTPException(status_code=403, detail="Forbidden")
    sessions = query.order_by(db.AnalysisSession.created_at).all()
    return [
        {
            "session_id": s.id,
            "date": s.created_at.isoformat(),
            "overall_score": s.overall_score,
            "sport_type": s.sport_type,
        }
        for s in sessions
    ]


if os.path.isdir(_FRONTEND_BUILD):
    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_frontend(full_path: str):
        return FileResponse(os.path.join(_FRONTEND_BUILD, "index.html"))
