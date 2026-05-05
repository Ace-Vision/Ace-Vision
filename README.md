# Ace Vision

AI-powered tennis serve / badminton analysis. Upload a video, get biomechanics feedback and coaching advice.

## How it works

```
Video in → Pose extraction → Joint angles → Deviation overlay → Coaching advice
```

1. **Pose extraction** — MediaPipe detects 33 body landmarks per frame
2. **Smoothing & normalisation** — Gaussian filter removes jitter; hip-centred scaling makes results size-independent
3. **Angle calculation** — Measures 9 serve-specific joint angles (elbows, shoulders, knees, trunk, hips, wrist)
4. **Deviation scoring** — Compares your angles against expert baselines and scores severity
5. **Overlay rendering** — Draws a colour-coded skeleton on your video (green/amber/red by severity)
6. **Coaching** — Local Ollama LLM analyses deviations and returns targeted corrections (optional — works without it)

## Prerequisites

- Python 3.10+
- Node.js 18+
- [Ollama](https://ollama.com) *(optional — coaching feedback only)*

## Setup

```bash
# 1. Clone and create a virtual environment
git clone <repo-url> && cd ace-vision
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

# 2. Install Python dependencies
pip install -r requirements.txt

# 3. Install frontend dependencies
cd frontend && npm install && cd ..
```

## Running the app

Open two terminal tabs from the project root.

**Terminal 1 — backend:**
```bash
source .venv/bin/activate        # Windows: .venv\Scripts\activate
uvicorn backend.main:app --reload
```

**Terminal 2 — frontend:**
```bash
cd frontend && npm start
```

Then open http://localhost:3000 in your browser.
The API is available at http://localhost:8000 (docs at http://localhost:8000/docs).

> **Note:** You'll need your own `.mp4` video file to test the app. Sample videos are gitignored and not included in the repo. Any tennis serve or badminton smash clip works — just upload it via the UI.

## Coaching feedback (optional)

Coaching is powered by a local [Ollama](https://ollama.com) model. If Ollama is not running, the analysis still works — coaching advice is simply omitted.

To enable it:
```bash
# Install Ollama from https://ollama.com, then:
ollama pull gemma3
ollama serve
```

You can override the model via environment variables (see `.env.example`).

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
│   ├── llm.py                # Ollama coaching feedback (optional)
│   ├── schemas.py            # Pydantic models
│   └── db.py                 # SQLAlchemy models (not yet wired up)
├── frontend/                 # React app
├── data/
│   ├── reference/
│   │   └── expert_baselines.json
│   └── samples/              # Test videos (gitignored)
├── tests/
├── .env.example
└── requirements.txt
```

## API

### `POST /analyse`

Upload a serve video for analysis.

- **Input:** video file (mp4), `sport_type` (`tennis_serve` or `badminton`), `skill_level` (string)
- **Returns:** overlay video path, deviation scores JSON, `session_id`, `overall_score`, `coaching`

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
- **Backend:** FastAPI
- **Frontend:** React
- **Coaching (optional):** Ollama (gemma3)

## Running tests

```bash
pytest
```

## License

All rights reserved.
