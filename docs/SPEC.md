# Ace Vision — Technical Spec

## What it does

Analyses a tennis serve from video and gives the player coaching feedback.

**Pipeline:**
```
Video in → Pose extraction → Joint angles → Deviation overlay → LLM coaching advice
```

---

## Scope (MVP only)

- Serve stroke only — no classifier needed, user explicitly uploads a serve
- No ball tracking
- No court detection
- Offline processing (not real-time)

---

## Stack

- **Pose:** MediaPipe
- **CV / overlay:** OpenCV
- **Backend:** FastAPI + PostgreSQL
- **LLM:** Local Model / Claude API (claude-sonnet-4-6)
- **Mobile:** React Native (Phase 4 — not MVP)

---

## Folder structure

```
ace-vision/
├── ml/
│   ├── extractor.py       # MediaPipe pose extraction → per-frame JSON
│   ├── smoother.py        # Gaussian smoothing on keypoint time series
│   ├── normaliser.py      # Hip-centred, scale-free normalisation
│   ├── calculator.py      # Joint angle computation (arccos dot product)
│   ├── scorer.py          # Compare angles vs expert baselines → deviation scores
│   └── renderer.py        # Draw skeleton + colour-coded overlay on video
├── backend/
│   ├── main.py            # FastAPI entry point
│   ├── pipeline.py        # Chains all ml/ modules in order
│   ├── llm.py             # Claude API call → structured coaching JSON
│   ├── schemas.py         # Pydantic models
│   └── db.py              # SQLAlchemy models: User, Session, DeviationResult
├── data/
│   ├── reference/
│   │   └── expert_baselines.json   # Expert joint angle distributions
│   └── samples/                    # Test videos (gitignored)
├── tests/
├── .env.example
└── requirements.txt
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

## Expert baselines (`expert_baselines.json`)

Hardcode these values to start. Replace with THETIS-derived values later.

```json
{
  "right_elbow_flexion":     { "mean": 118, "std": 8  },
  "right_shoulder_abduction":{ "mean": 90,  "std": 10 },
  "trunk_lateral_tilt":      { "mean": 15,  "std": 5  },
  "left_knee_flexion":       { "mean": 45,  "std": 8  }
}
```

---

## Deviation scoring

For each joint:

```python
deviation_deg   = abs(player_angle - expert_mean)
severity_score  = min(deviation_deg / (2 * expert_std), 1.0)
direction       = "too_high" if player_angle > expert_mean else "too_low"
```

Also compute: `hip_leads_shoulder` (bool) — True if peak hip rotation precedes peak shoulder rotation by > 3 frames.

---

## Overlay (renderer.py)

Draw on each frame in this order:

1. White skeleton lines (MediaPipe POSE_CONNECTIONS, 60% opacity)
2. Colour-coded joint dots for the 9 serve joints:
   - Green `#4CAF50` — severity < 0.3
   - Amber `#FF9800` — severity 0.3–0.6
   - Red `#F44336` — severity > 0.6
3. Small angle arc at each joint (radius 30px, matching colour)
4. HUD top-right: top 3 deviations with joint name + degrees off

---

## API endpoints

**`POST /analyse`**
- Input: video file (mp4), skill_level (string)
- Runs the full pipeline
- Returns: overlay video + deviation scores JSON + session_id

**`POST /coaching`**
- Input: session_id, deviation_scores, skill_level
- Calls LLM
- Returns: coaching JSON (2 corrections + summary)

---

## LLM system prompt (do not change)

```
You are a professional tennis biomechanics coach.
You will receive joint angle deviation data from a player's serve.

Rules:
1. Every correction must reference a specific field from the JSON by name.
2. No generic advice. "Keep your eye on the ball" is forbidden.
3. Address highest severity_score first.
4. Maximum 2 corrections. One drill each.
5. If hip_leads_shoulder is false, address kinetic chain first.
6. Return only valid JSON. No preamble.

Output schema:
{
  "corrections": [
    { "joint": "", "deviation_deg": 0, "impact": "", "drill": "" }
  ],
  "summary": ""
}
```

---

## Environment variables

```bash
ANTHROPIC_API_KEY=sk-ant-...
DATABASE_URL=postgresql://localhost:5432/ace_vision
REFERENCE_BASELINES_PATH=./data/reference/expert_baselines.json
```

---

## Dependencies

```
mediapipe==0.10.14
opencv-python==4.10.0.84
numpy==1.26.4
scipy==1.13.1
fastapi==0.115.0
uvicorn==0.30.6
python-multipart==0.0.9
sqlalchemy==2.0.35
psycopg2-binary==2.9.9
pydantic==2.8.2
anthropic==0.34.2
fastdtw==0.3.4
python-dotenv==1.0.1
pytest==8.3.3
```
