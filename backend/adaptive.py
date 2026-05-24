"""
Detect joints that have been repeatedly problematic across a user's past sessions.
Used to give Gemini context about recurring issues so coaching escalates instead of repeating.
"""

from sqlalchemy.orm import Session
from backend import db

# A joint counts as "flagged" in a session if its severity exceeds this threshold
_SEVERITY_THRESHOLD = 0.5

# A joint is "recurring" if flagged in this many of the last N sessions
_MIN_FLAGGED_SESSIONS = 2
_LOOK_BACK = 4


def get_recurring_issues(
    user_id: int,
    sport_type: str,
    sqlite_db: Session,
    last_n: int = _LOOK_BACK,
) -> list[str]:
    """
    Return joint names flagged (severity > 0.5) in at least 2 of the last `last_n`
    sessions for this user and sport. Returns [] if fewer than 2 past sessions exist.
    """
    sessions = (
        sqlite_db.query(db.AnalysisSession)
        .filter(
            db.AnalysisSession.user_id == user_id,
            db.AnalysisSession.sport_type == sport_type,
        )
        .order_by(db.AnalysisSession.created_at.desc())
        .limit(last_n)
        .all()
    )

    if len(sessions) < _MIN_FLAGGED_SESSIONS:
        return []

    flag_count: dict[str, int] = {}
    for session in sessions:
        for dev in session.deviations:
            if dev.severity_score is not None and dev.severity_score > _SEVERITY_THRESHOLD:
                flag_count[dev.joint_name] = flag_count.get(dev.joint_name, 0) + 1

    return [joint for joint, count in flag_count.items() if count >= _MIN_FLAGGED_SESSIONS]
