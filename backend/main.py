"""
backend/main.py — FastAPI entry point.

Creates the FastAPI application instance and registers route handlers.

Endpoints:
- POST /analyse  — Pick a sport, run the full ML pipeline on the sample video,
                   return overlay video path + deviation scores + session_id.

Key responsibilities:
- Initialise FastAPI app with CORS (so the frontend can talk to it)
- Serve the frontend HTML file
- Define the /analyse route using Pydantic schemas
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from backend.schemas import AnalyseRequest, AnalyseResponse
from backend import pipeline

app = FastAPI(title="Ace Vision API")

# Allow the frontend (running on any origin during development) to call the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve the frontend folder so you can open the UI at http://localhost:8000/
app.mount("/static", StaticFiles(directory="frontend"), name="static")


@app.get("/")
def serve_frontend():
    """Serve the main frontend HTML page."""
    return FileResponse("frontend/index.html")


@app.post("/analyse", response_model=AnalyseResponse)
def analyse(request: AnalyseRequest):
    """
    Run the ML pipeline on the sample video for the chosen sport.

    The frontend sends:
      - sport_type:  "badminton" or "tennis_serve"
      - skill_level: "beginner", "intermediate", or "advanced"

    Returns deviation scores and the path to the rendered overlay video.
    """
    result = pipeline.run_pipeline(request.sport_type, request.skill_level)
    return AnalyseResponse(**result)
