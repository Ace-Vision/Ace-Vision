"""
tools/visualize_thresholds.py

Overlay right-wrist and right-elbow height (relative to shoulder, in body-scale units)
on every frame of a video. Use this to decide detection thresholds visually.

Green text = currently above WRIST_THRESHOLD (would trigger detection).
White text = below threshold.

Usage:
    python tools/visualize_thresholds.py <input_video> [output_video]
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import cv2
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

from backend.shot_detector import WRIST_THRESHOLD_RATIO, _body_scale, _wrist_above_shoulder


def elbow_above_shoulder(kp: dict) -> float:
    elbow    = kp.get("right_elbow")
    shoulder = kp.get("right_shoulder")
    if not elbow or not shoulder:
        return 0.0
    return shoulder["y"] - elbow["y"]


def run(input_path: str, output_path: str):
    base_options = python.BaseOptions(model_asset_path="models/pose_landmarker.task")
    options = vision.PoseLandmarkerOptions(
        base_options=base_options,
        running_mode=vision.RunningMode.VIDEO,
        min_pose_detection_confidence=0.5,
        min_pose_presence_confidence=0.5,
        min_tracking_confidence=0.5,
    )
    landmarker = vision.PoseLandmarker.create_from_options(options)

    cap    = cv2.VideoCapture(input_path)
    fps    = cap.get(cv2.CAP_PROP_FPS) or 30.0
    w      = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h      = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    total  = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out    = cv2.VideoWriter(output_path, fourcc, fps, (w, h))

    frame_idx = 0
    stride = 1  # process every frame for smooth display

    print(f"Processing {total} frames at {fps:.1f}fps → {output_path}")

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image  = mp.Image(image_format=mp.ImageFormat.SRGB, data=frame_rgb)
        timestamp = int(frame_idx / fps * 1000)
        result    = landmarker.detect_for_video(mp_image, timestamp)

        kp = {}
        if result.pose_landmarks:
            for idx, lm in enumerate(result.pose_landmarks[0]):
                name = vision.PoseLandmark(idx).name.lower()
                kp[name] = {"x": lm.x, "y": lm.y, "z": lm.z, "visibility": lm.visibility}

        scale         = _body_scale(kp) if kp else 0.25
        wrist_above   = _wrist_above_shoulder(kp) if kp else 0.0
        elbow_above   = elbow_above_shoulder(kp) if kp else 0.0
        threshold     = WRIST_THRESHOLD_RATIO * scale
        triggered     = wrist_above > threshold

        # normalise by body scale so values are comparable across distances
        wrist_norm = wrist_above / scale if scale else 0.0
        elbow_norm = elbow_above / scale if scale else 0.0

        color = (0, 255, 80) if triggered else (220, 220, 220)

        lines = [
            f"wrist above shoulder: {wrist_norm:+.2f}  (thresh={WRIST_THRESHOLD_RATIO:.2f})",
            f"elbow above shoulder: {elbow_norm:+.2f}",
            f"{'>>> TRIGGERED <<<' if triggered else ''}",
        ]

        font  = cv2.FONT_HERSHEY_SIMPLEX
        scale_f = 0.55
        thick   = 1
        pad     = 8
        x, y    = 10, 30

        for line in lines:
            if not line:
                continue
            cv2.putText(frame, line, (x, y), font, scale_f, (0, 0, 0), thick + 2, cv2.LINE_AA)
            cv2.putText(frame, line, (x, y), font, scale_f, color,     thick,     cv2.LINE_AA)
            y += 22

        out.write(frame)

        if frame_idx % 300 == 0:
            print(f"  {frame_idx}/{total} ({frame_idx/total*100:.0f}%)")
        frame_idx += 1

    cap.release()
    out.release()
    print("Done.")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python tools/visualize_thresholds.py <input> [output]")
        sys.exit(1)
    inp = sys.argv[1]
    out = sys.argv[2] if len(sys.argv) > 2 else inp.rsplit(".", 1)[0] + "_debug.mp4"
    run(inp, out)
