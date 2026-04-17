"""
streamlit_app.py — Ace Vision frontend.

A simple Streamlit UI that lets the user:
1. Choose a sport (Badminton Clear or Tennis Serve)
2. Pick their skill level
3. Click Analyse to run the ML pipeline via the FastAPI backend
4. See each joint's deviation score, colour-coded by severity
"""

import time
from pathlib import Path

import requests
import streamlit as st

# The FastAPI backend URL — change this if you run the backend on a different port
BACKEND_URL = "http://127.0.0.1:8000"


def get_severity_colour(severity_score: float) -> str:
    """
    Return a colour name based on how severe the deviation is.
    Green = good, Orange = needs work, Red = significant issue.
    """
    if severity_score < 0.3:
        return "green"
    elif severity_score < 0.6:
        return "orange"
    else:
        return "red"


def format_joint_name(joint_key: str) -> str:
    """Turn 'right_elbow_flexion' into 'Right Elbow Flexion'."""
    return joint_key.replace("_", " ").title()


def wait_for_output_file(file_path: Path, timeout_seconds: int = 10) -> bool:
    """
    Wait briefly for the renderer output file to appear.
    This helps when the backend responds just before the file is fully visible.
    """
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        if file_path.exists() and file_path.stat().st_size > 0:
            return True
        time.sleep(0.4)
    return False


# ── Page setup ──────────────────────────────────────────────────────────────

st.set_page_config(page_title="Ace Vision", page_icon="🎾", layout="centered")

st.title("Ace Vision")
st.caption("Choose a sport, pick your skill level, and get technique feedback.")

st.divider()

# ── Step 1: Sport selection ──────────────────────────────────────────────────

st.subheader("Choose a sport")

# Two side-by-side buttons for sport selection
col1, col2 = st.columns(2)

with col1:
    badminton_selected = st.button("🏸  Badminton Clear", use_container_width=True)

with col2:
    tennis_selected = st.button("🎾  Tennis Serve", use_container_width=True)

# Session state lets Streamlit remember the selected sport between reruns
if badminton_selected:
    st.session_state.sport_type = "badminton"

if tennis_selected:
    st.session_state.sport_type = "tennis_serve"

# Show which sport is currently active
if "sport_type" in st.session_state:
    selected_label = "Badminton Clear" if st.session_state.sport_type == "badminton" else "Tennis Serve"
    st.success(f"Selected: **{selected_label}**")
else:
    st.info("Select a sport above to continue.")

st.divider()

# ── Step 2: Skill level ──────────────────────────────────────────────────────

st.subheader("Skill level")

skill_level = st.selectbox(
    label="Your current level",
    options=["beginner", "intermediate", "advanced"],
    index=1,  # default to intermediate
)

st.divider()

# ── Step 3: Analyse button ───────────────────────────────────────────────────

sport_chosen = "sport_type" in st.session_state
analyse_clicked = st.button("Analyse", disabled=not sport_chosen, type="primary", use_container_width=True)

if analyse_clicked:
    with st.spinner("Running analysis... this may take a moment."):
        try:
            # POST to the FastAPI backend
            response = requests.post(
                f"{BACKEND_URL}/analyse",
                json={
                    "sport_type": st.session_state.sport_type,
                    "skill_level": skill_level,
                },
                timeout=120,  # give the pipeline up to 2 minutes
            )
            response.raise_for_status()
            result = response.json()

            # Save results to session state so they stay visible after rerun
            st.session_state.results = result
            st.session_state.last_overlay_path = result.get("overlay_path")

        except requests.exceptions.ConnectionError:
            st.error("Could not connect to the backend. Make sure uvicorn is running on port 8000.")
        except requests.exceptions.HTTPError as e:
            st.error(f"Backend error: {e.response.status_code} — {e.response.text}")
        except Exception as e:
            st.error(f"Something went wrong: {e}")

# ── Step 4: Results ──────────────────────────────────────────────────────────

if "results" in st.session_state:
    result = st.session_state.results

    st.divider()
    sport_label = "Badminton Clear" if result["sport_type"] == "badminton" else "Tennis Serve"
    st.subheader(f"Results — {sport_label}")

    # Human-readable labels for each checkpoint key
    CHECKPOINT_LABELS = {
        "trophy":      "Trophy Position",
        "racket_drop": "Racket Drop",
        "contact":     "Contact (Ball Strike)",
    }

    checkpoints = result["deviation_scores"].get("checkpoints", {})

    if not checkpoints:
        st.warning("No checkpoint data returned. Check that your video has a visible player.")
    else:
        # Show one collapsible section per checkpoint.
        # Contact is open by default since that's the most important moment.
        for checkpoint_key in ["trophy", "racket_drop", "contact"]:
            label      = CHECKPOINT_LABELS[checkpoint_key]
            is_contact = checkpoint_key == "contact"

            with st.expander(label, expanded=is_contact):
                data = checkpoints.get(checkpoint_key)

                # This checkpoint wasn't detected in the video
                if data is None:
                    st.info(f"Could not detect {label} in this video.")
                    continue

                st.caption(f"Detected at frame {data['frame']}")

                deviations = data.get("deviations", {})
                if not deviations:
                    st.info("No joint data for this checkpoint.")
                else:
                    for joint_key, info in deviations.items():
                        colour     = get_severity_colour(info["severity_score"])
                        joint_name = format_joint_name(joint_key)
                        direction  = info["direction"].replace("_", " ")

                        st.markdown(
                            f":{colour}[**{joint_name}**] &nbsp; "
                            f"`{info['angle']:.1f}°` — "
                            f"{info['deviation_deg']:.1f}° off &nbsp;·&nbsp; {direction}"
                        )

    overlay_path_str = st.session_state.get("last_overlay_path")
    if overlay_path_str:
        st.divider()
        st.subheader("Processed Video")
        output_path = Path(overlay_path_str)
        if output_path.suffix.lower() == ".avi":
            mp4_candidate = output_path.with_suffix(".mp4")
            if mp4_candidate.exists():
                output_path = mp4_candidate
        if wait_for_output_file(output_path):
            mime_type = "video/mp4" if output_path.suffix.lower() == ".mp4" else "video/x-msvideo"
            st.video(output_path.read_bytes(), format=mime_type)
            st.caption(f"Output saved at: {output_path}")
        else:
            st.warning(f"Video is not ready yet at `{output_path}`. Try Analyse again in a moment.")
