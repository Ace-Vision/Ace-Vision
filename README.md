# Ace Vision

AI-powered tennis serve analysis. Upload a video of your serve, get biomechanics feedback and coaching advice.

## How it works

```
Video in → Pose extraction → Joint angles → Deviation overlay → LLM coaching advice
```

1. **Pose extraction** — MediaPipe detects 33 body landmarks per frame
2. **Smoothing & normalisation** — Gaussian filter removes jitter; hip-centred scaling makes results size-independent
3. **Angle calculation** — Measures 9 serve-specific joint angles (elbows, shoulders, knees, trunk, hips, wrist)
4. **Deviation scoring** — Compares your angles against expert baselines and scores severity
5. **Overlay rendering** — Draws a colour-coded skeleton on your video (green/amber/red by severity)
6. **Coaching** — Claude analyses deviations and returns 2 targeted corrections with drills

## Project structure

```
ace-vision/
├── ml/
│   ├── extractor.py          # MediaPipe pose extraction
│   ├── smoother.py           # Gaussian smoothing on keypoints
│   ├── normaliser.py         # Hip-centred, scale-free normalisation
│   ├── calculator.py         # Joint angle computation
│   ├── scorer.py             # Deviation scoring vs expert baselines
│   └── renderer.py           # Skeleton overlay + colour-coded joints
├── backend/
│   ├── main.py               # FastAPI routes
│   ├── pipeline.py           # Chains ml/ modules end-to-end
│   ├── llm.py                # LLM Model for coaching feedback
│   ├── schemas.py            # Pydantic models
│   └── db.py                 # SQLAlchemy models (PostgreSQL)
├── data/
│   ├── reference/
│   │   └── expert_baselines.json
│   └── samples/              # Test videos (gitignored)
├── tests/
├── .env.example
└── requirements.txt
```

## Setup

```bash
# Clone and install
git clone <repo-url> && cd ace-vision
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt


# Start the server
uvicorn backend.main:app --reload
```

### Prerequisites

- Python 3.10+
- PostgreSQL
- Anthropic API key

## API

### `POST /analyse`

Upload a serve video for analysis.

- **Input:** video file (mp4), `skill_level` (string)
- **Returns:** overlay video, deviation scores JSON, `session_id`

### `POST /coaching`

Get LLM-powered coaching from deviation data.

- **Input:** `session_id`, `deviation_scores`, `skill_level`
- **Returns:** coaching JSON (2 corrections with drills + summary)

## Joints analysed

| Joint                    | Keypoints                                  |
| ------------------------ | ------------------------------------------ |
| Right elbow flexion      | right_shoulder → right_elbow → right_wrist |
| Left elbow flexion       | left_shoulder → left_elbow → left_wrist    |
| Right shoulder abduction | right_elbow → right_shoulder → right_hip   |
| Left shoulder abduction  | left_elbow → left_shoulder → left_hip      |
| Right knee flexion       | right_hip → right_knee → right_ankle       |
| Left knee flexion        | left_hip → left_knee → left_ankle          |
| Trunk lateral tilt       | left_shoulder → mid_spine → right_shoulder |
| Hip-shoulder separation  | left_hip → right_hip → right_shoulder      |
| Wrist extension          | right_elbow → right_wrist → right_index    |

## Scoring

```
deviation_deg   = abs(player_angle - expert_mean)
severity_score  = min(deviation_deg / (2 * expert_std), 1.0)
```

Overlay colours: **green** (< 0.3) · **amber** (0.3–0.6) · **red** (> 0.6)

## Stack

- **Pose:** MediaPipe
- **CV / overlay:** OpenCV
- **Backend:** FastAPI + PostgreSQL
- **LLM:** Claude (claude-sonnet-4-6) via Anthropic API

## Running tests

```bash
pytest
```

## License

All rights reserved.
