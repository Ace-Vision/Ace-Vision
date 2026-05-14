"""
backend/schemas.py — Pydantic models for request/response validation.
"""

from typing import Literal, Optional, List, Dict, Any
from pydantic import BaseModel, ConfigDict, EmailStr
from datetime import datetime

SportType = Literal["badminton", "tennis_serve"]

# ── Auth ──────────────────────────────────────────────────────────────────────

class UserRegister(BaseModel):
    name: str
    email: EmailStr
    password: str
    skill_level: str = "beginner"

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: int
    name: str
    email: str

# ── User ──────────────────────────────────────────────────────────────────────

class UserBase(BaseModel):
    name: str
    skill_level: str

class UserCreate(UserBase):
    pass

class UserRead(UserBase):
    id: int
    email: str
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

# ── Sessions / Deviations ─────────────────────────────────────────────────────

class DeviationResultBase(BaseModel):
    joint_name: str
    player_angle: float
    expert_mean: float
    deviation_deg: float
    severity_score: float

class DeviationResult(DeviationResultBase):
    id: int
    session_id: str
    model_config = ConfigDict(from_attributes=True)

class SessionBase(BaseModel):
    sport_type: SportType
    overall_score: int
    coaching_feedback: Optional[Dict[str, Any]] = None

class SessionCreate(SessionBase):
    id: str
    user_id: Optional[int] = None
    video_path: str

class SessionRead(SessionBase):
    id: str
    user_id: Optional[int]
    video_path: str
    created_at: datetime
    deviations: List[DeviationResultBase]
    model_config = ConfigDict(from_attributes=True)

class AnalyseResponse(BaseModel):
    session_id: str
    deviation_scores: dict
    overlay_path: str
    sport_type: SportType
    overall_score: int
    coaching: Optional[dict] = None
    model_config = ConfigDict(from_attributes=True)
