# Ace Vision

AI-powered tennis serve / badminton analysis. Upload or record a video, get biomechanics feedback and Gemini coaching advice.

## How it works

```
Video in → Pose extraction → Joint angles → Deviation scoring → Overlay rendering → Gemini coaching
```

1. **Pose extraction** — MediaPipe detects 33 body landmarks per frame
2. **Angle calculation** — Measures 9 serve-specific joint angles (elbows, shoulders, knees, trunk, hips, wrist)
3. **Deviation scoring** — Compares angles against expert baselines and scores severity
4. **Overlay rendering** — Draws a colour-coded skeleton on your video (green/amber/red by severity)
5. **Coaching** — Gemini 2.5 Flash analyses the overlay video + deviation data and returns targeted feedback, highlighting the worst joint

## Prerequisites

- Python 3.10+
- Node.js 18+
- A [Gemini API key](https://aistudio.google.com/app/apikey) (free tier works)

## Setup

```bash
# 1. Clone and create a virtual environment
git clone <repo-url> && cd ace-vision
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# 2. Install Python dependencies
pip install -r requirements.txt

# 3. Install frontend dependencies
cd frontend && npm install && cd ..

# 4. Set your Gemini API key
cp .env.example .env
# Edit .env and set GEMINI_API_KEY=your_key_here
```

## Running the app

Build the React frontend once, then start the backend — everything runs on a single port.

```bash
# Build frontend (only needed once, or after frontend changes)
cd frontend && npm run build && cd ..

# Start the server
source venv/bin/activate
GEMINI_API_KEY=your_key_here uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

Open **http://localhost:8000** in your browser.

> Tip: export GEMINI_API_KEY in your shell profile so you don't need to prefix every command.

## Mobile access (same Wi-Fi)

To use the app on your phone (required for camera recording):

```bash
# Install ngrok
brew install ngrok/ngrok/ngrok
ngrok config add-authtoken <your_ngrok_token>

# Start the server as above, then in a separate terminal:
ngrok http 8000
```

Open the `https://...ngrok-free.app` URL on your phone.

## Project structure

```
ace-vision/
├── ml/
│   ├── extractor.py      # MediaPipe pose extraction
│   ├── calculator.py     # Joint angle computation
│   ├── scorer.py         # Deviation scoring vs expert baselines
│   └── renderer.py       # Skeleton overlay + colour-coded joints
├── backend/
│   ├── main.py           # FastAPI routes + React static serving
│   ├── pipeline.py       # Chains ml/ modules end-to-end
│   ├── vlm.py            # Gemini coaching (structured output)
│   └── schemas.py        # Pydantic models
├── frontend/             # React app (build output gitignored)
├── data/
│   └── reference/        # Expert baseline JSON files
├── models/               # MediaPipe pose model
├── uploads/              # Generated overlay videos (gitignored)
├── .env.example
└── requirements.txt
```

## API

### `POST /analyse`

Upload a serve video for analysis.

- **Input:** video file (mp4/mov), `sport_type` (`tennis_serve` or `badminton`), `skill_level` (string)
- **Returns:** overlay video path, deviation scores, `session_id`, `overall_score`, `coaching`

### `GET /overlay/{session_id}`

Returns the rendered overlay MP4 for a given session.

## Scoring

```
deviation_deg   = abs(player_angle - expert_mean)
severity_score  = min(deviation_deg / (2 * expert_std), 1.0)
overall_score   = round((1 - mean_severity) * 100)
```

Overlay colours: **green** (< 0.3) · **amber** (0.3–0.6) · **red** (> 0.6)

## Stack

- **Pose:** MediaPipe
- **CV / overlay:** OpenCV
- **Backend:** FastAPI
- **Frontend:** React + Tailwind
- **Coaching:** Gemini 2.5 Flash (`google-genai`)

## Running tests

```bash
pytest
```

## License

All rights reserved.
