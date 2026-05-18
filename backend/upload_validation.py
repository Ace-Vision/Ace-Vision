"""Upload size, type, and duration checks for /analyse."""

import os

import cv2

MAX_BYTES = int(os.getenv("MAX_UPLOAD_BYTES", 100 * 1024 * 1024))
MAX_DURATION_SEC = float(os.getenv("MAX_VIDEO_DURATION_SEC", 30))
ALLOWED_SUFFIXES = {".mp4", ".mov", ".webm", ".avi", ".mkv"}
ALLOWED_CONTENT_TYPES = {
    "video/mp4",
    "video/quicktime",
    "video/webm",
    "video/x-msvideo",
    "video/x-matroska",
    "application/octet-stream",
}


def validate_upload_metadata(
    filename: str | None,
    content_type: str | None,
    size_bytes: int,
) -> str:
    """Validate extension, content type, and size. Returns normalised suffix."""
    suffix = (os.path.splitext(filename or "")[1] or ".mp4").lower()
    if suffix not in ALLOWED_SUFFIXES:
        raise ValueError(
            f"Unsupported file type '{suffix}'. Use mp4, mov, webm, or avi."
        )
    if content_type and content_type not in ALLOWED_CONTENT_TYPES:
        raise ValueError(f"Unsupported content type '{content_type}'.")
    if size_bytes > MAX_BYTES:
        max_mb = MAX_BYTES // (1024 * 1024)
        got_mb = size_bytes // (1024 * 1024)
        raise ValueError(f"File too large ({got_mb} MB). Maximum is {max_mb} MB.")
    return suffix


def validate_video_duration(path: str) -> None:
    """Reject videos that are too long or too short to analyse."""
    cap = cv2.VideoCapture(path)
    try:
        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        frames = cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0
        duration = frames / fps if fps > 0 else 0
        if duration > MAX_DURATION_SEC:
            raise ValueError(
                f"Video too long ({duration:.1f}s). "
                f"Maximum is {MAX_DURATION_SEC:.0f}s."
            )
        if duration < 0.5:
            raise ValueError("Video is too short to analyse.")
    finally:
        cap.release()
