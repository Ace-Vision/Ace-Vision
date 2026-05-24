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
import os
import sys
import shutil
import tempfile
import cv2
from datetime import datetime, timedelta
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
    AnalyseResponse, MatchAnalyseResponse, UserCreate, UserRead, SessionRead,
    UserRegister, UserLogin, TokenResponse,
)
from backend import pipeline, vlm, db, court_tracker, score_recognizer
from ml import renderer

SECRET_KEY = os.getenv("SECRET_KEY", "ace-vision-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)

API_KEY = os.environ.get("GEMINI_API_KEY", "")
if not API_KEY:
    raise RuntimeError("GEMINI_API_KEY environment variable is not set")
gemini = vlm.gemini_model(API_KEY)

app = FastAPI(title="Ace Vision API")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

_FRONTEND_BUILD = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend", "build")
if os.path.isdir(_FRONTEND_BUILD):
    app.mount("/static", StaticFiles(directory=os.path.join(_FRONTEND_BUILD, "static")), name="static")


@app.on_event("startup")
def startup_event():
    db.init_db()


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
        sub = payload.get("sub")
        if sub is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        user_id = int(sub)
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
    user = sqlite_db.query(db.User).filter(db.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user


@app.post("/auth/register", response_model=TokenResponse)
def register(body: UserRegister, sqlite_db: Session = Depends(db.get_db)):
    if sqlite_db.query(db.User).filter(db.User.email == body.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")
    user = db.User(
        name=body.name, email=body.email,
        hashed_password=hash_password(body.password), skill_level=body.skill_level,
    )
    sqlite_db.add(user); sqlite_db.commit(); sqlite_db.refresh(user)
    token = create_access_token({"sub": str(user.id)})
    return TokenResponse(access_token=token, user_id=user.id, name=user.name, email=user.email)

@app.post("/auth/login", response_model=TokenResponse)
def login(body: UserLogin, sqlite_db: Session = Depends(db.get_db)):
    user = sqlite_db.query(db.User).filter(db.User.email == body.email).first()
    if not user or not verify_password(body.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    token = create_access_token({"sub": str(user.id)})
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
    coaching = await asyncio.to_thread(
        gemini.get_coaching, result["deviation_scores"], actual_video_path, skill_level, sport_type,
    )

    highlight_joint = coaching.get("highlight_joint") if coaching else None
    if highlight_joint:
        try:
            highlighted_tmp = await asyncio.to_thread(
                renderer.render_video, tmp_path,
                result["keypoints_list"], result["deviation_scores"], result["angles_list"], highlight_joint,
            )
            os.replace(highlighted_tmp, actual_video_path)
        except Exception:
            pass

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

    return AnalyseResponse(
        session_id=result["session_id"], deviation_scores=result["deviation_scores"],
        overlay_path=result["overlay_path"], sport_type=sport_type,
        overall_score=result["overall_score"], coaching=coaching,
    )


@app.post("/analyse_match", response_model=MatchAnalyseResponse)
async def analyse_match(
    file: UploadFile = File(...),
    sport_type: str = Form(...),
):
    if sport_type not in ("badminton", "tennis_serve"):
        raise HTTPException(status_code=422, detail="sport_type must be badminton or tennis_serve")

    suffix = os.path.splitext(file.filename)[1] or ".mp4"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = tmp.name

    try:
        result = await asyncio.to_thread(pipeline.run_match_pipeline, tmp_path, sport_type)
    except Exception as exc:
        os.unlink(tmp_path)
        import traceback; traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(exc))
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)

    coaching = None
    if result["clip_paths"]:
        coaching = await asyncio.to_thread(
            gemini.get_match_coaching,
            result["clip_paths"], sport_type,
        )

    clip_filenames = [os.path.basename(p) for p in result["clip_paths"]]

    return MatchAnalyseResponse(
        session_id=result["session_id"],
        sport_type=sport_type,
        shot_count=result["shot_count"],
        shots=result["shots"],
        clip_filenames=clip_filenames,
        coaching=coaching,
    )


@app.get("/clips/{session_id}/{filename}")
async def get_clip(session_id: str, filename: str):
    path = os.path.join("data", "results", session_id, filename)
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Clip not found")
    return FileResponse(path, media_type="video/mp4")


@app.post("/analyse_movement")
async def analyse_movement(
    file: UploadFile = File(...),
    sport_type: str = Form("badminton"),
    court_corners: str = Form(...),
    final_my_score:  Optional[int] = Form(None),
    final_opp_score: Optional[int] = Form(None),
):
    import json
    try:
        corners = json.loads(court_corners)
    except Exception:
        raise HTTPException(status_code=422, detail="court_corners must be valid JSON")
    if len(corners) != 4:
        raise HTTPException(status_code=422, detail="court_corners must have exactly 4 points")

    suffix = os.path.splitext(file.filename)[1] or ".mp4"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = tmp.name

    # 1) Court movement analysis
    try:
        court_result = await asyncio.to_thread(
            court_tracker.run_court_analysis, tmp_path, corners
        )
    except Exception as exc:
        import traceback; traceback.print_exc()
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise HTTPException(status_code=500, detail=str(exc))

    session_id = court_result["session_id"]

    # 2) Score recognition — movement result is returned even if this fails
    try:
        final_score = (final_my_score, final_opp_score) if final_my_score is not None and final_opp_score is not None else None
        score_result = await asyncio.to_thread(
            score_recognizer.run_score_analysis, tmp_path, "small", "en", session_id, final_score
        )
        rallies       = score_result["rallies"]
        rally_summary = score_result["summary"]
    except Exception:
        import traceback; traceback.print_exc()
        rallies       = []
        rally_summary = {"user_wins": 0, "opponent_wins": 0, "total_rallies": 0}
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)

    # 3) Heatmap — other results are returned even if this fails
    try:
        await asyncio.to_thread(
            court_tracker.generate_heatmap,
            court_result["_positions"],
            court_result["_H"],
            court_result["_video_w"],
            court_result["_video_h"],
            court_result["_fps"],
            rallies,
            session_id,
        )
    except Exception:
        import traceback; traceback.print_exc()

    return {
        "session_id":      session_id,
        "sport_type":      sport_type,
        "total_positions": court_result["total_positions"],
        "duration_s":      court_result["duration_s"],
        "rallies":         rallies,
        "rally_summary":   rally_summary,
        "phase_analysis":  court_result.get("phase_analysis"),
    }


@app.get("/phase_heatmap/{session_id}/{phase_num}")
async def get_phase_heatmap(session_id: str, phase_num: int):
    if phase_num not in (1, 2, 3):
        raise HTTPException(status_code=422, detail="phase_num must be 1, 2, or 3")
    path = os.path.join("data", "results", session_id, f"heatmap_phase_{phase_num}.png")
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Phase heatmap not found")
    return FileResponse(path, media_type="image/png")


@app.get("/movement/{session_id}")
async def get_movement_video(session_id: str):
    path = os.path.join("data", "results", session_id, "movement.mp4")
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Movement video not found")
    return FileResponse(path, media_type="video/mp4")

@app.get("/heatmap/{session_id}/{which}")
async def get_heatmap(session_id: str, which: str):
    if which not in ("win", "loss"):
        raise HTTPException(status_code=422, detail="which must be 'win' or 'loss'")
    path = os.path.join("data", "results", session_id, f"heatmap_{which}.png")
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Heatmap not found")
    return FileResponse(path, media_type="image/png")

@app.get("/debug/{session_id}")
async def get_debug_video(session_id: str):
    path = os.path.join("data", "results", session_id, "debug.mp4")
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Debug video not found")
    return FileResponse(path, media_type="video/mp4")

@app.get("/court_positions/{session_id}")
async def get_court_positions(session_id: str):
    import json as _json
    path = os.path.join("data", "results", session_id, "positions.json")
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Position data not found")
    with open(path) as f:
        return _json.load(f)

@app.post("/rally_coaching")
async def get_rally_coaching(body: dict):
    import json as _json
    session_id = body.get("session_id")
    if not session_id:
        raise HTTPException(status_code=422, detail="session_id required")

    # Return cached feedback if available
    cache_path = os.path.join("data", "results", session_id, "coaching.json")
    if os.path.exists(cache_path):
        with open(cache_path) as f:
            return _json.load(f)

    try:
        feedback = await asyncio.to_thread(gemini.get_rally_coaching, body)
    except Exception as exc:
        err = str(exc)
        if "429" in err or "RESOURCE_EXHAUSTED" in err or "quota" in err.lower():
            raise HTTPException(status_code=429, detail="quota_exceeded")
        raise HTTPException(status_code=503, detail="LLM unavailable")

    if feedback is None:
        raise HTTPException(status_code=503, detail="LLM unavailable")

    result = {"feedback": feedback}
    os.makedirs(os.path.join("data", "results", session_id), exist_ok=True)
    with open(cache_path, "w") as f:
        _json.dump(result, f)
    return result


@app.post("/analyse_score")
async def analyse_score(
    file: UploadFile = File(...),
    model_size: str = Form("medium"),
    language: str = Form("en"),
):
    """
    Recognise scores from a video and return per-rally clips.

    Returns:
        { session_id, rallies: [{index, start_s, end_s, my_score, opponent_score,
                                 rally_winner, clip_filename}], summary }
    """
    suffix = os.path.splitext(file.filename)[1] or ".mp4"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = tmp.name

    try:
        result = await asyncio.to_thread(
            score_recognizer.run_score_analysis,
            tmp_path, model_size, language,
        )
    except Exception as exc:
        import traceback; traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(exc))
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)

    return result


@app.get("/rally_clip/{session_id}/{filename}")
async def get_rally_clip(session_id: str, filename: str):
    path = os.path.join("data", "results", session_id, filename)
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Clip not found")
    return FileResponse(path, media_type="video/mp4")


@app.post("/rally_label")
async def set_rally_label(body: dict):
    import json as _json
    session_id  = body.get("session_id")
    rally_index = body.get("rally_index")
    label       = body.get("label")

    if not session_id or rally_index is None:
        raise HTTPException(status_code=422, detail="session_id and rally_index required")

    labels_path = os.path.join("data", "results", session_id, "labels.json")
    labels: dict = {}
    if os.path.exists(labels_path):
        with open(labels_path) as f:
            labels = _json.load(f)

    if label is None:
        labels.pop(str(rally_index), None)
    else:
        labels[str(rally_index)] = label

    with open(labels_path, "w") as f:
        _json.dump(labels, f)

    return {"ok": True}


@app.get("/rally_labels/{session_id}")
async def get_rally_labels(session_id: str):
    import json as _json
    labels_path = os.path.join("data", "results", session_id, "labels.json")
    if not os.path.exists(labels_path):
        return {"labels": {}}
    with open(labels_path) as f:
        return {"labels": _json.load(f)}


@app.post("/recognise_scores")
async def recognise_scores(
    file: UploadFile = File(...),
    model_size: str = Form("medium"),
    language: str = Form("en"),
    include_transcript: bool = Form(False),
):
    """
    Recognise spoken scores from a video and return rally winners.

    Returns:
        {
            "rallies": [{"timestamp", "my_score", "opponent_score", "rally_winner"}, ...],
            "summary": {"user_wins", "opponent_wins", "total_rallies"},
            "segments": [...],   # only when include_transcript=True
        }
    """
    suffix = os.path.splitext(file.filename)[1] or ".mp4"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = tmp.name

    try:
        if include_transcript:
            result = await asyncio.to_thread(
                score_recognizer.recognize_scores_with_transcript,
                tmp_path, model_size, language,
            )
        else:
            scores = await asyncio.to_thread(
                score_recognizer.recognize_scores,
                tmp_path, model_size, language,
            )
            result = {"scores": scores}
    except Exception as exc:
        import traceback; traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(exc))
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)

    return result


@app.post("/match_sessions", status_code=201)
def save_match_session(body: dict, current_user: db.User = Depends(get_current_user), sqlite_db: Session = Depends(db.get_db)):
    session_id = body.get("session_id")
    if not session_id:
        raise HTTPException(status_code=422, detail="session_id required")
    if sqlite_db.query(db.MatchSession).filter(db.MatchSession.id == session_id).first():
        return {"ok": True, "session_id": session_id}

    rallies = body.get("rallies") or []
    rally_summary = body.get("rally_summary") or {}
    last_rally = rallies[-1] if rallies else None
    my_score  = last_rally.get("my_score")       if last_rally else rally_summary.get("user_wins", 0)
    opp_score = last_rally.get("opponent_score")  if last_rally else rally_summary.get("opponent_wins", 0)

    sqlite_db.add(db.MatchSession(
        id=session_id,
        user_id=current_user.id,
        sport_type=body.get("sport_type", "badminton"),
        opponent_name=body.get("opponent_name") or None,
        match_comment=body.get("match_comment") or None,
        my_score=my_score,
        opp_score=opp_score,
        rallies=rallies,
        rally_summary=rally_summary,
        phase_analysis=body.get("phase_analysis"),
    ))
    sqlite_db.commit()
    return {"ok": True, "session_id": session_id}


@app.get("/match_sessions/{session_id}")
def get_match_session(session_id: str, sqlite_db: Session = Depends(db.get_db)):
    ms = sqlite_db.query(db.MatchSession).filter(db.MatchSession.id == session_id).first()
    if not ms:
        raise HTTPException(status_code=404, detail="Match session not found")
    return {
        "session_id":   ms.id,
        "sport_type":   ms.sport_type,
        "opponent_name": ms.opponent_name,
        "match_comment": ms.match_comment,
        "my_score":     ms.my_score,
        "opp_score":    ms.opp_score,
        "rallies":      ms.rallies or [],
        "rally_summary": ms.rally_summary or {},
        "phase_analysis": ms.phase_analysis,
        "created_at":   ms.created_at.isoformat(),
    }


@app.get("/users/me/match_history")
def get_my_match_history(current_user: db.User = Depends(get_current_user), sqlite_db: Session = Depends(db.get_db)):
    sessions = (
        sqlite_db.query(db.MatchSession)
        .filter(db.MatchSession.user_id == current_user.id)
        .order_by(db.MatchSession.created_at.desc())
        .all()
    )
    return [
        {
            "session_id":   ms.id,
            "sport_type":   ms.sport_type,
            "opponent_name": ms.opponent_name,
            "my_score":     ms.my_score,
            "opp_score":    ms.opp_score,
            "created_at":   ms.created_at.isoformat(),
        }
        for ms in sessions
    ]


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


if os.path.isdir(_FRONTEND_BUILD):
    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_frontend(full_path: str):
        return FileResponse(os.path.join(_FRONTEND_BUILD, "index.html"))
