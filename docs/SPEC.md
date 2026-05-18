# Ace Vision — Technical Spec

## What it does

Analyses a tennis serve or badminton overhead from video and gives biomechanics feedback plus AI coaching.

**Pipeline:**
```
Video in → Pose extraction → Smooth → Normalise → Joint angles → Deviation scoring → Overlay → Gemini coaching
```

---

## Scope (MVP)

- User uploads or records a serve/clear — no stroke classifier
- Sports: `badminton`, `tennis_serve`
- No ball tracking or court detection
- Offline batch processing (not real-time)

---

## Stack

- **Pose:** MediaPipe (`models/pose_landmarker.task`)
- **CV / overlay:** OpenCV
- **Backend:** FastAPI + SQLite (SQLAlchemy)
- **Frontend:** React + Tailwind (built to `frontend/build`, served by FastAPI)
- **Coaching:** Google Gemini 2.5 Flash (`backend/vlm.py`)
- **Experimental (optional):** Ollama + RAG + Streamlit — see `requirements-experimental.txt`

---

## Folder structure

```
ace-vision/
├── ml/
│   ├── extractor.py       # MediaPipe pose extraction → per-frame JSON
│   ├── smoother.py        # Gaussian smoothing (scipy)
│   ├── normaliser.py      # Hip-centred, scale-free normalisation
│   ├── calculator.py      # Joint angle computation (arccos dot product)
│   ├── scorer.py          # Compare angles vs expert baselines → deviation scores
│   └── renderer.py        # Skeleton + colour-coded overlay on video
├── backend/
│   ├── main.py            # FastAPI entry point, auth, static frontend
│   ├── pipeline.py        # Chains all ml/ modules in order
│   ├── vlm.py             # Gemini coaching (structured JSON)
│   ├── upload_validation.py  # Upload size, type, duration limits
│   ├── schemas.py         # Pydantic models
│   ├── db.py              # SQLAlchemy models: User, Session, DeviationResult
│   ├── llm.py             # (experimental) Ollama coaching
│   └── vector_db.py       # (experimental) RAG over PDFs
├── frontend/              # React app
├── data/
│   ├── reference/         # Expert baseline JSON per sport
│   └── samples/           # Reference/sample videos (gitignored)
├── uploads/               # Generated overlays and frames (gitignored)
├── streamlit_app.py       # (experimental) alternate UI
├── requirements.txt
├── requirements-experimental.txt
└── tests/
```

---

## The 9 joints to analyse (serve-specific)

| Joint                    | Keypoints used                             |
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

Angle formula: `θ = arccos(dot(v1, v2) / (|v1| × |v2|))` where v1 and v2 point away from the vertex joint.

---

## Expert baselines

Per-sport JSON under `data/reference/`:

- `tennis_baselines.json`
- `badminton_baselines.json`

---

## Deviation scoring

For each joint at each checkpoint:

```python
deviation_deg   = abs(player_angle - expert_mean)
severity_score  = min(deviation_deg / (2 * expert_std), 1.0)
direction       = "too_high" if player_angle > expert_mean else "too_low"
```

Overall score uses weighted checkpoint averages (contact weighted highest). See `backend/pipeline.py`.

Overlay colours: **green** (< 0.3) · **amber** (0.3–0.6) · **red** (> 0.6)

---

## Overlay (renderer.py)

Draw on each frame:

1. White skeleton lines (MediaPipe connections)
2. Colour-coded joint dots by severity
3. Optional highlight pass for the worst joint (after Gemini coaching)

---

## API endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/auth/register` | Register; returns JWT |
| POST | `/auth/login` | Login; returns JWT |
| GET | `/auth/me` | Current user (Bearer token) |
| POST | `/analyse` | Upload video + `sport_type` + `skill_level`; runs full pipeline + coaching |
| GET | `/overlay/{session_id}` | Overlay MP4 |
| GET | `/frame/{session_id}/{checkpoint}` | Checkpoint JPEG |
| GET | `/reference/{sport_type}` | Sample reference video |
| GET | `/users/{user_id}/history` | Past sessions |
| GET | `/sessions/{session_id}` | Session detail |

### `POST /analyse`

- **Input:** `file` (video), `sport_type` (`badminton` \| `tennis_serve`), `skill_level`, optional `user_id`
- **Limits:** `MAX_UPLOAD_BYTES` (default 100 MB), `MAX_VIDEO_DURATION_SEC` (default 30 s)
- **Returns:** `session_id`, `deviation_scores`, `overlay_path`, `overall_score`, `coaching`, `highlight_applied`

Coaching prompt and JSON schema live in `backend/vlm.py` (single source of truth).

---

## Environment variables

```bash
GEMINI_API_KEY=...              # required
SECRET_KEY=...                  # JWT signing (change in production)
MAX_UPLOAD_BYTES=104857600      # optional, default 100 MB
MAX_VIDEO_DURATION_SEC=30     # optional
```

---

## Dependencies

**Core:** `pip install -r requirements.txt`

**Experimental (Ollama, RAG, Streamlit):** `pip install -r requirements-experimental.txt`

---

## Running tests

```bash
GEMINI_API_KEY=your_key pytest
```
