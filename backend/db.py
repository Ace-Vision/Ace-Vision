from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, JSON, Boolean
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from sqlalchemy import create_engine
import datetime
import os

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./ace_vision.db")

# Render의 PostgreSQL URL은 postgres://로 시작하는데 SQLAlchemy는 postgresql://이 필요함
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    skill_level = Column(String, default="beginner")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    sessions = relationship("AnalysisSession", back_populates="user")

class AnalysisSession(Base):
    __tablename__ = "sessions"

    id = Column(String, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    sport_type = Column(String)
    video_path = Column(String)
    overall_score = Column(Integer)
    coaching_feedback = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    user = relationship("User", back_populates="sessions")
    deviations = relationship("DeviationResult", back_populates="session")

class DeviationResult(Base):
    __tablename__ = "deviations"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String, ForeignKey("sessions.id"))
    joint_name = Column(String)
    player_angle = Column(Float)
    expert_mean = Column(Float)
    deviation_deg = Column(Float)
    severity_score = Column(Float)

    session = relationship("AnalysisSession", back_populates="deviations")

def init_db():
    Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()