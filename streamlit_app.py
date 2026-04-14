"""
streamlit_app.py — Ace Vision frontend.

A simple Streamlit UI that lets the user:
1. Choose a sport (Badminton Clear or Tennis Serve)
2. Pick their skill level
3. Click Analyse to run the ML pipeline via the FastAPI backend
4. See each joint's deviation score, colour-coded by severity
"""

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

    deviations = result["deviation_scores"].get("deviations", {})

    if not deviations:
        st.warning("No deviation data returned. Check that your video has a visible player.")
    else:
        # Show each joint as a coloured line
        for joint_key, info in deviations.items():
            colour = get_severity_colour(info["severity_score"])
            joint_name = format_joint_name(joint_key)
            direction = info["direction"].replace("_", " ")

            st.markdown(
                f":{colour}[**{joint_name}**] &nbsp; "
                f"`{info['angle']:.1f}°` — "
                f"{info['deviation_deg']:.1f}° off &nbsp;·&nbsp; {direction}"
            )
