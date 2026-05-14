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

    def analyze_video(self, video_path: str, prompt: str, response_schema: dict | None = None) -> str:
        print(f"Uploading: {video_path}")
        video_file = self.client.files.upload(file=video_path)

        print(f"Processing (ID: {video_file.name})", end="")
        while video_file.state.name == "PROCESSING":
            print(".", end="", flush=True)
            time.sleep(2)
            video_file = self.client.files.get(name=video_file.name)

        if video_file.state.name != "ACTIVE":
            raise ValueError(f"Video failed to reach ACTIVE state: {video_file.state.name}")

        config = None
        if response_schema:
            config = types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=response_schema,
            )

        max_retries = 3
        for attempt in range(max_retries):
            try:
                print(f"\nAnalysis Attempt {attempt + 1}...")
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
            

    def get_coaching(self, deviation_scores: dict, video_path: str,
                     skill_level: str = "intermediate",
                     sport_type: str = "badminton") -> dict | None:

        checkpoints = deviation_scores.get("checkpoints", {})

        if sport_type == "badminton":
            prompt_body = "\n\n".join([
                self._format_checkpoint("Backswing",      checkpoints.get("backswing")),
                self._format_checkpoint("Contact",        checkpoints.get("contact")),
                self._format_checkpoint("Follow Through", checkpoints.get("follow_through")),
            ])
        else:
            prompt_body = "\n\n".join([
                self._format_checkpoint("Trophy Position", checkpoints.get("trophy")),
                self._format_checkpoint("Racket Drop",     checkpoints.get("racket_drop")),
                self._format_checkpoint("Contact",         checkpoints.get("contact")),
            ])

        prompt = f"""You are an expert badminton coach analyzing a clear overhead shot.
            The player's skill level is: {skill_level}.

            Joint deviation data at 3 key moments (backswing, contact, followthrough):
            {prompt_body}
            (severity_score: 0.0 = perfect, 1.0 = maximum deviation from pro baseline)

            ---

            COMMON BEGINNER MISTAKE PATTERNS — use these to identify ROOT CAUSE, not just symptoms:

            1. **Late positioning / low contact point**
            Signs: contact-frame right_shoulder_abduction low, right_elbow_flexion too bent at contact, trunk_lateral_tilt minimal
            → Don't say "elbow not extended." Say: "You may be getting into position too late — focus on early footwork and positioning before the shuttle arrives."

            2. **Wrist-only swing (no kinetic chain)**
            Signs: wrist_extension deviation high, but right_shoulder_abduction and hip_shoulder_separation are near normal
            → Don't say "fix your wrist." Say: "You're relying too much on wrist snap — engage your shoulder and elbow first, then let the wrist follow through naturally."

            3. **Backswing too large or too small**
            Signs: backswing-frame right_elbow_flexion or right_shoulder_abduction highly deviated
            → Say: "Your backswing preparation is off — aim for a compact but full arm draw before swinging forward."

            4. **Body facing forward (no rotation)**
            Signs: hip_shoulder_separation low at backswing, trunk_lateral_tilt near zero throughout
            → Say: "Your body is facing the net too early — turn sideways first and use your body rotation to generate power."

            5. **Stopping at contact (no follow-through)**
            Signs: followthrough-frame wrist_extension and right_elbow_flexion heavily deviated
            → Say: "You're stopping your swing at impact — commit to a full follow-through to maximize power and control."

            ---

            Using the deviation data AND the video, identify which pattern above best matches. 
            Give 1 coaching correction focused on the ROOT CAUSE of the issue, not the symptom.
            Also mention briefly what the player did well.
            Be concise, practical, and encouraging. Maximum 100 words.

            Also select the single body part (highlight_joint) from the provided list that needs the most correction.

            If the video is unclear or is not badminton/tennis, set advice to "Video unclear, unable to provide advice." and pick any joint for highlight_joint.
            """

        schema = {
            "type": "object",
            "properties": {
                "advice": {"type": "string"},
                "highlight_joint": {"type": "string", "enum": HIGHLIGHT_JOINTS},
            },
            "required": ["advice", "highlight_joint"],
        }

        try:
            raw = self.analyze_video(video_path, prompt, response_schema=schema)
            data = json.loads(raw)
            return {
                "advice": data.get("advice", "").strip(),
                "highlight_joint": data.get("highlight_joint"),
            }
        except Exception:
            return None
    
        #print(f"Analyzing video for coaching advice with skill level '{skill_level}'...")
        #print(self.analyze_video(video_path, prompt))

"""
my_vlm = gemini_model(API_KEY)
my_vlm.get_coaching(video_path, skill_level="intermediate")
"""
