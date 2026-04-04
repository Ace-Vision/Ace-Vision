"""
backend/db.py — SQLAlchemy models and database setup.

Defines the PostgreSQL-backed data models and provides engine/session
factory for the application.

Tables:
- User        — player profile (id, name, skill_level, created_at)
- Session     — one analysis run (id, user_id, video_path, created_at)
- DeviationResult — per-joint scores for a session (session_id, joint_name,
                    player_angle, expert_mean, deviation_deg, severity_score,
                    direction)

Key responsibilities:
- Configure SQLAlchemy engine from DATABASE_URL env var
- Define ORM models with relationships (User → Sessions → DeviationResults)
- Provide session factory and dependency injection helper for FastAPI
- Create tables on first run via Base.metadata.create_all
"""
