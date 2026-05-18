import os
import tempfile

import cv2
import numpy as np
import pytest

from backend.upload_validation import (
    MAX_BYTES,
    validate_upload_metadata,
    validate_video_duration,
)


def test_rejects_unknown_extension():
    with pytest.raises(ValueError, match="Unsupported file type"):
        validate_upload_metadata("clip.xyz", "video/mp4", 1000)


def test_rejects_oversized_file():
    with pytest.raises(ValueError, match="too large"):
        validate_upload_metadata("clip.mp4", "video/mp4", MAX_BYTES + 1)


def test_accepts_valid_metadata():
    suffix = validate_upload_metadata("serve.mp4", "video/mp4", 1024)
    assert suffix == ".mp4"


def test_rejects_long_video():
    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp:
        path = tmp.name
    try:
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        writer = cv2.VideoWriter(path, fourcc, 30.0, (64, 64))
        for _ in range(31 * 30):  # 31 seconds at 30 fps
            writer.write(np.zeros((64, 64, 3), dtype=np.uint8))
        writer.release()

        with pytest.raises(ValueError, match="too long"):
            validate_video_duration(path)
    finally:
        os.unlink(path)
