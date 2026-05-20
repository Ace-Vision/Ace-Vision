import json
import os
import time
from google import genai
from google.genai import types
import requests

HIGHLIGHT_JOINTS = [
    "right_elbow", "left_elbow",
    "right_shoulder", "left_shoulder",
    "right_wrist", "left_wrist",
    "right_knee", "left_knee",
    "right_hip", "left_hip",
    "nose",
]

""""
Using Gemini API for video analysis. This version uses gemini-2.5-flash,
which is smaller and but offers more free usage than the larger gemini-2.5-pro.
Usually it takes a few attempts to generate since it is often busy.
"""

# 1. Input API key and choose video path
#API_KEY = "AIzaSyDxZjxpnb0JIotRIFVVplb_GmOtdHO9Enk" 
#video_path = r"C:\Users\ldahl\Downloads\user_clear.mp4"
#video_path_0 = r"C:\Users\ldahl\Videos\WIN_20260429_16_56_29_Pro.mp4"

class gemini_model:
    """
    VLM module to get coaching advice from a video using a Gemini Video Model.

    The get_coaching function uploads the video to Gemini, waits for it to be processed,
    and then sends a prompt asking for coaching advice based on the video's content.
    The response is returned as plain text.

    Note: This implementation assumes the video contains the necessary visual information
    for the model to analyze and provide feedback. Does not process with respect to any
    numerical deviation scores.

    Also, this implementation does not currently integrate with the VectorDatabase for contextual search,
    but that could be added in future iterations by including relevant text from the database in the prompt.
    """

    def __init__(self, api_key: str):
        self.client = genai.Client(api_key=api_key)

    def _format_checkpoint(self, name: str, data: dict | None) -> str:
        if data is None:
            return f"=== {name.upper()} ===\n  (not detected in video)\n"

        lines = [f"=== {name.upper()} (frame {data['frame']}) ==="]
        for joint, info in data["deviations"].items():
            label = joint.replace("_", " ")
            lines.append(
                f"  {label}: {info['angle']:.1f}° "
                f"({info['deviation_deg']:.1f}° off, {info['direction'].replace('_', ' ')}, "
                f"severity {info['severity_score']:.2f})"
            )
        return "\n".join(lines)

    def _upload_and_wait(self, video_path: str):
        """Upload a single video to Gemini Files API and wait until ACTIVE."""
        print(f"Uploading: {video_path}")
        f = self.client.files.upload(file=video_path)
        print(f"  Processing {f.name}", end="", flush=True)
        while f.state.name == "PROCESSING":
            print(".", end="", flush=True)
            time.sleep(2)
            f = self.client.files.get(name=f.name)
        print()
        if f.state.name != "ACTIVE":
            raise ValueError(f"File {f.name} failed to reach ACTIVE: {f.state.name}")
        return f

    def analyze_video(self, video_path: str, prompt: str, response_schema: dict | None = None) -> str:
        """Analyse a single video file."""
        video_file = self._upload_and_wait(video_path)

        config = None
        if response_schema:
            config = types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=response_schema,
            )

        max_retries = 3
        for attempt in range(max_retries):
            try:
                print(f"Analysis Attempt {attempt + 1}...")
                response = self.client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=[video_file, prompt],
                    config=config,
                )
                self.client.files.delete(name=video_file.name)
                return response.text

            except Exception as e:
                if "503" in str(e) and attempt < max_retries - 1:
                    wait = (attempt + 1) * 10
                    print(f"Server busy. Waiting {wait}s...")
                    time.sleep(wait)
                    continue
                self.client.files.delete(name=video_file.name)
                raise e
            

    _BADMINTON_PATTERNS = """
1. **Late positioning / low contact point**
   Player is still moving when they swing; contact happens below ideal height.
   → "You're hitting the shuttle too late and too low — get your feet set early so you can reach up and make contact at full arm extension above your head."

2. **Arm-only swing (no kinetic chain)**
   Shoulders stay square; power comes only from the arm, not the body.
   → "You're swinging with just your arm — turn your shoulders sideways during the backswing, then rotate into the shot to transfer your body weight into the hit."

3. **Collapsed backswing**
   Elbow drops too low or racket barely drawn back before the forward swing.
   → "Your backswing is too short — draw the racket back behind your ear with the elbow high before you swing forward."

4. **Body stays facing the net**
   Hips and shoulders remain square throughout; no sideways stance.
   → "You're facing the net the whole time — step sideways so your non-dominant shoulder points at the net, then uncoil into the shot."

5. **Swing stops at contact (no follow-through)**
   Arm decelerates right at the moment of impact; swing is blocked or tense.
   → "You're braking your swing at impact — let the racket follow all the way down across your body after you hit the shuttle."
"""

    _TENNIS_SERVE_PATTERNS = """
1. **Ball toss too far forward or to the side**
   Player must lunge or reach awkwardly to make contact.
   → "Your toss is landing too far in front / to the side — practice tossing straight up to just in front of your hitting shoulder so you can swing naturally into it."

2. **No leg drive (flat-footed trophy position)**
   Knees barely bend; all power comes from the arm.
   → "You're not using your legs — bend your knees deeply in the trophy position, then push up and extend fully as you swing so your whole body drives the serve."

3. **Elbow drops at racket drop ('waiter's tray')**
   Elbow falls below shoulder level during the racket drop phase.
   → "Your elbow is dropping too low before you swing — keep your elbow up near shoulder height during the racket drop so you can snap forward with full power."

4. **No shoulder rotation (arm-only serve)**
   Shoulders stay parallel to the baseline; no coil-and-uncoil.
   → "Your shoulders aren't rotating — turn your back shoulder toward the back fence in the trophy position, then unwind into the serve to generate real power."

5. **Early arm extension (no wrist snap at contact)**
   Arm fully extends before contact; wrist stays locked through impact.
   → "You're reaching for the ball too early — stay loose, let the wrist snap forward at the very last moment of contact rather than pushing through with a stiff arm."
"""

    def get_coaching(self, deviation_scores: dict, video_path: str,
                     skill_level: str = "intermediate",
                     sport_type: str = "badminton") -> dict | None:

        checkpoints = deviation_scores.get("checkpoints", {})

        if sport_type == "badminton":
            sport_label = "badminton clear (overhead shot)"
            checkpoint_data = "\n\n".join([
                self._format_checkpoint("Backswing",      checkpoints.get("backswing")),
                self._format_checkpoint("Contact",        checkpoints.get("contact")),
                self._format_checkpoint("Follow Through", checkpoints.get("follow_through")),
            ])
            patterns = self._BADMINTON_PATTERNS
        else:
            sport_label = "tennis serve"
            checkpoint_data = "\n\n".join([
                self._format_checkpoint("Trophy Position", checkpoints.get("trophy")),
                self._format_checkpoint("Racket Drop",     checkpoints.get("racket_drop")),
                self._format_checkpoint("Contact",         checkpoints.get("contact")),
            ])
            patterns = self._TENNIS_SERVE_PATTERNS

        prompt = f"""You are an expert {sport_label} coach. The player's skill level is: {skill_level}.

STEP 1 — WATCH THE VIDEO FIRST.
Look at the player's actual movement. Trust what you see. Your visual observation is the primary source of truth.

STEP 2 — SUPPLEMENTARY DATA (use only to confirm or add nuance to what you observed — do not let numbers override your visual judgment):
{checkpoint_data}
(severity_score: 0.0 = no deviation, 1.0 = maximum deviation from reference — treat as a rough hint, not a verdict)

STEP 3 — IDENTIFY THE ROOT CAUSE using these common beginner mistake patterns:
{patterns}

STEP 4 — WRITE YOUR COACHING FEEDBACK following this exact structure:
- Sentence 1: State the single most important thing to fix, concretely and observably. Describe what the player IS doing vs. what they SHOULD be doing (e.g. "At contact your elbow is bent — you need your arm fully extended above your head"). Do not be vague.
- Sentence 2–3: Explain why it matters and give one concrete cue or drill to fix it.
- Final sentence: Name one thing the player did well.

Maximum 90 words. Be direct — a player should finish reading and know exactly what to work on next session.

Also output:
- highlight_joint: the single joint from the list that needs the most correction
- pattern_id: the number (1–5) of the pattern that best matches what you saw

If the video is too dark, too short, or clearly not {sport_label}, set advice to "Video unclear, unable to provide advice.", pick any joint, and set pattern_id to 1.
"""

        schema = {
            "type": "object",
            "properties": {
                "advice": {"type": "string"},
                "highlight_joint": {"type": "string", "enum": HIGHLIGHT_JOINTS},
                "pattern_id": {"type": "integer"},
            },
            "required": ["advice", "highlight_joint", "pattern_id"],
        }

        try:
            raw = self.analyze_video(video_path, prompt, response_schema=schema)
            data = json.loads(raw)
            return {
                "advice": data.get("advice", "").strip(),
                "highlight_joint": data.get("highlight_joint"),
                "pattern_id": data.get("pattern_id"),
            }
        except Exception:
            return None

    def get_match_coaching(self, clip_paths: list[str],
                           sport_type: str = "badminton") -> dict | None:
        """
        Analyse multiple individual shot clips from a match in one Gemini request.
        Each clip is uploaded separately so the model sees them as distinct shots.
        """
        if not clip_paths:
            return None

        if sport_type == "badminton":
            sport_label = "badminton overhead shot"
        else:
            sport_label = "tennis serve"

        shot_count = len(clip_paths)

        if sport_type == "badminton":
            patterns = self._BADMINTON_PATTERNS
        else:
            patterns = self._TENNIS_SERVE_PATTERNS

        prompt = f"""You are an expert {sport_label} coach reviewing {shot_count} overhead shot clips extracted from a match.

Each clip shows one shot: backswing → contact → follow-through.

Watch ALL clips first. Then identify the single most important thing this player needs to fix.
Use these common patterns to anchor your diagnosis:
{patterns}

Output:
  advice:          One focused coaching note (max 60 words). State what the player IS doing wrong, why it costs them in a match, and one concrete fix cue. End with one thing they do well.
  pattern_id:      The number (1–5) of the pattern that best matches what you saw.
  highlight_joint: The single joint from the list that needs the most work.

If fewer than 2 clips show a clear overhead shot, set advice to "Not enough clear overhead shots to identify trends."
"""

        schema = {
            "type": "object",
            "properties": {
                "advice":          {"type": "string"},
                "pattern_id":      {"type": "integer"},
                "highlight_joint": {"type": "string", "enum": HIGHLIGHT_JOINTS},
            },
            "required": ["advice", "pattern_id", "highlight_joint"],
        }

        uploaded = []
        try:
            # Upload all clips in parallel sequence, wait for each to be ACTIVE
            for path in clip_paths:
                uploaded.append(self._upload_and_wait(path))

            config = types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=schema,
            )

            max_retries = 3
            for attempt in range(max_retries):
                try:
                    print(f"Match analysis attempt {attempt + 1} ({shot_count} clips)…")
                    response = self.client.models.generate_content(
                        model="gemini-2.5-flash",
                        contents=[*uploaded, prompt],
                        config=config,
                    )
                    data = json.loads(response.text)
                    return {
                        "advice":          data.get("advice", "").strip(),
                        "pattern_id":      data.get("pattern_id"),
                        "highlight_joint": data.get("highlight_joint"),
                    }
                except Exception as e:
                    if "503" in str(e) and attempt < max_retries - 1:
                        time.sleep((attempt + 1) * 10)
                        continue
                    raise
        except Exception:
            return None
        finally:
            for f in uploaded:
                try:
                    self.client.files.delete(name=f.name)
                except Exception:
                    pass
