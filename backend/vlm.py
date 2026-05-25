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
Using Gemini API for video analysis. This version uses gemini-2.0-flash,
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
                    model="gemini-2.0-flash",
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

    _CLASSIFY_BATCH_SIZE = 5

    _BADMINTON_VISUAL_CUES = """
FOREHAND_CLEAR:
  - Player's body is turned SIDEWAYS — non-dominant shoulder points toward the shuttle
  - Hitting arm draws back with a HIGH ELBOW (elbow at or above shoulder, racket behind the head)
  - Clear body ROTATION: hips and shoulders uncoil through the swing
  - Contact point is ABOVE and slightly in front of the dominant shoulder at full arm extension
  - Long sweeping follow-through that crosses the body downward

SMASH:
  - Same high-elbow backswing setup as forehand clear
  - Swing is visibly faster and the racket angle is more DOWNWARD at contact
  - Body leans FORWARD aggressively into the shot
  - May be a JUMP SMASH — player leaves the ground before or at contact
  - Follow-through is sharp and abbreviated compared to a clear

BACKHAND:
  - Hitting arm CROSSES the body's centre line (right arm swings to the left side or vice versa)
  - OR the player's DOMINANT shoulder is CLOSER to the shuttle than the non-dominant shoulder at setup
  - Elbow often leads, arm comes from the non-dominant side of the body
  - Body rotation direction is OPPOSITE to a forehand shot
  - Contact point tends to be more in front of the body, not at full overhead extension

OTHER:
  - Net shots, low defensive clears, drives, serves, or any clip where a clear overhead swing is not visible
"""

    _TENNIS_VISUAL_CUES = """
FOREHAND_CLEAR (overhead smash or serve):
  - High ball toss in front of dominant shoulder
  - Full trophy position with high elbow
  - Clear upward extension to contact

SMASH:
  - Opponent lob → player reaches overhead aggressively downward

BACKHAND:
  - Two-handed or one-handed backhand grip and swing

OTHER:
  - Groundstrokes, volleys, or unclear clips
"""

    def _classify_batch(self, uploaded_batch: list, global_offset: int,
                        sport_type: str) -> list[dict]:
        """
        Classify a small batch of already-uploaded clips, with retry on 503.
        Returns list of {"index": <global>, "shot_type": <str>}.
        """
        n = len(uploaded_batch)
        cues = self._BADMINTON_VISUAL_CUES if sport_type == "badminton" else self._TENNIS_VISUAL_CUES

        prompt = f"""You are classifying {n} badminton shot clips.

The clips are presented in order. Within this batch they are numbered 0 to {n - 1}.

Use these visual criteria to decide:
{cues}

Rules:
- Output exactly {n} classifications, one per clip, in order (index 0, 1, 2 …).
- Be decisive — choose the closest match even if the clip is ambiguous.
- Do NOT skip any clip.
"""

        schema = {
            "type": "object",
            "properties": {
                "classifications": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "index":     {"type": "integer"},
                            "shot_type": {"type": "string",
                                          "enum": ["forehand_clear", "smash", "backhand", "other"]},
                        },
                        "required": ["index", "shot_type"],
                    },
                },
            },
            "required": ["classifications"],
        }

        config = types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=schema,
        )

        for attempt in range(4):
            try:
                response = self.client.models.generate_content(
                    model="gemini-2.0-flash",
                    contents=[*uploaded_batch, prompt],
                    config=config,
                )
                data = json.loads(response.text)
                results = []
                for item in data.get("classifications", []):
                    local_idx = item.get("index", 0)
                    results.append({
                        "index":     global_offset + local_idx,
                        "shot_type": item.get("shot_type", "other"),
                    })
                return results
            except Exception as e:
                if "503" in str(e) and attempt < 3:
                    wait = (attempt + 1) * 15
                    print(f"  503 on batch, retrying in {wait}s…")
                    time.sleep(wait)
                    continue
                raise

    def get_match_coaching(self, clip_paths: list[str],
                           sport_type: str = "badminton") -> dict | None:
        """
        1. Upload all clips.
        2. Classify in batches of CLASSIFY_BATCH_SIZE (small enough for accurate labelling).
        3. One coaching call across all clips for the key advice.
        """
        if not clip_paths:
            return None

        sport_label = "badminton overhead shot" if sport_type == "badminton" else "tennis serve"
        patterns    = self._BADMINTON_PATTERNS if sport_type == "badminton" else self._TENNIS_SERVE_PATTERNS
        shot_count  = len(clip_paths)

        uploaded = []
        try:
            for path in clip_paths:
                uploaded.append(self._upload_and_wait(path))

            # ── Step 1: classify in small batches ──────────────────────────
            all_classifications = []
            for start in range(0, len(uploaded), self._CLASSIFY_BATCH_SIZE):
                batch = uploaded[start:start + self._CLASSIFY_BATCH_SIZE]
                print(f"Classifying clips {start}–{start + len(batch) - 1}…")
                try:
                    results = self._classify_batch(batch, start, sport_type)
                    all_classifications.extend(results)
                    print(f"  → {[r['shot_type'] for r in results]}")
                except Exception as e:
                    print(f"  Batch classification failed: {e} — marking as 'other'")
                    for i in range(len(batch)):
                        all_classifications.append({"index": start + i, "shot_type": "other"})
                # brief pause between batches to avoid rate limiting
                if start + self._CLASSIFY_BATCH_SIZE < len(uploaded):
                    time.sleep(5)

            # ── Step 2: coaching across all clips ──────────────────────────
            coaching_prompt = f"""You are an expert {sport_label} coach reviewing {shot_count} overhead shot clips from a match.

Each clip: backswing → contact → follow-through.

Watch ALL clips. Identify the single most important thing this player needs to fix.
Reference patterns:
{patterns}

Output:
  advice:          Max 60 words. What they do wrong, why it matters in a match, one fix cue. End with one positive.
  pattern_id:      Number 1–5 matching the main pattern.
  highlight_joint: Joint needing the most work.

If fewer than 2 clips show a clear overhead, set advice to "Not enough clear overhead shots to identify trends."
"""

            coaching_schema = {
                "type": "object",
                "properties": {
                    "advice":          {"type": "string"},
                    "pattern_id":      {"type": "integer"},
                    "highlight_joint": {"type": "string", "enum": HIGHLIGHT_JOINTS},
                },
                "required": ["advice", "pattern_id", "highlight_joint"],
            }

            config = types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=coaching_schema,
            )

            for attempt in range(3):
                try:
                    print(f"Coaching attempt {attempt + 1}…")
                    response = self.client.models.generate_content(
                        model="gemini-2.0-flash",
                        contents=[*uploaded, coaching_prompt],
                        config=config,
                    )
                    data = json.loads(response.text)
                    return {
                        "clips":           all_classifications,
                        "advice":          data.get("advice", "").strip(),
                        "pattern_id":      data.get("pattern_id"),
                        "highlight_joint": data.get("highlight_joint"),
                    }
                except Exception as e:
                    if "503" in str(e) and attempt < 2:
                        time.sleep((attempt + 1) * 10)
                        continue
                    raise

        except Exception as e:
            print(f"get_match_coaching failed: {e}")
            return None
        finally:
            for f in uploaded:
                try:
                    self.client.files.delete(name=f.name)
                except Exception:
                    pass

    def get_rally_coaching(self, session_data: dict) -> str | None:
        """
        Text-only coaching feedback for a match, based on rally tags + user notes.
        No video upload needed.
        """
        user_wins     = session_data.get("user_wins", 0)
        opp_wins      = session_data.get("opponent_wins", 0)
        total         = session_data.get("total_rallies", 0)
        opponent_name = (session_data.get("opponent_name") or "").strip()
        match_comment = (session_data.get("match_comment") or "").strip()
        sport_type    = session_data.get("sport_type", "badminton")
        loss_tags     = session_data.get("loss_tags", {})
        rally_notes   = session_data.get("rally_notes", {})

        swing_miss   = sum(1 for v in loss_tags.values() if v == "swing_miss")
        bad_footwork = sum(1 for v in loss_tags.values() if v == "bad_footwork")
        other_tag    = sum(1 for v in loss_tags.values() if v == "other")
        untagged     = max(0, opp_wins - swing_miss - bad_footwork - other_tag)

        notes_lines = [
            f"  Rally {int(i)+1}: {n.strip()}"
            for i, n in sorted(rally_notes.items(), key=lambda x: int(x[0]))
            if n.strip()
        ]
        notes_block = "\n".join(notes_lines) if notes_lines else "  (none)"

        sport_label = "badminton" if sport_type == "badminton" else "tennis"

        prompt = f"""You are an expert {sport_label} coach reviewing a match.

MATCH RESULT:
  Score: {user_wins} wins – {opp_wins} losses ({total} rallies total)
{"  Opponent: " + opponent_name if opponent_name else ""}
{"  Player's own thoughts: " + match_comment if match_comment else ""}

LOSS BREAKDOWN ({opp_wins} points lost):
  Swing miss:    {swing_miss}
  Bad footwork:  {bad_footwork}
  Other:         {other_tag}
  Untagged:      {untagged}

PLAYER NOTES ON INDIVIDUAL RALLIES:
{notes_block}

Write coaching feedback that will genuinely help this player grow. Follow this structure exactly:
- Paragraph 1 (2–3 sentences): Name the single most important pattern from the loss data. Be specific — what is the player doing wrong and why does it cost them points?
- Paragraph 2 (1–2 sentences): Give one concrete drill or cue to fix it.
- Final sentence: Acknowledge one positive from the match, then set a clear goal for the next session.

Be direct, warm, and specific. 100–140 words total. No bullet points."""

        response = self.client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[prompt],
        )
        text = (response.text or "").strip()
        return text if text else None

    def get_opponent_coaching(self, data: dict) -> str | None:
        """
        Tactical scouting advice for a specific opponent, based on:
        - Aggregated loss tags across all matches vs. that opponent
        - Court zone analysis (where the opponent pushes the user)
        - User's own match comments
        """
        opponent_name  = (data.get("opponent_name") or "this opponent").strip()
        sport_type     = data.get("sport_type", "badminton")
        total_matches  = data.get("total_matches", 0)
        total_wins     = data.get("total_wins", 0)
        total_losses   = data.get("total_losses", 0)
        mistake_counts = data.get("mistake_counts", {})
        zone_info      = (data.get("zone_description") or "").strip()
        comments       = [c for c in (data.get("comments") or []) if c and c.strip()]

        sport_label  = "badminton" if sport_type == "badminton" else "tennis"
        swing_miss   = mistake_counts.get("swing_miss", 0)
        bad_footwork = mistake_counts.get("bad_footwork", 0)
        other        = mistake_counts.get("other", 0)
        total_tagged = swing_miss + bad_footwork + other

        comments_block = "\n".join(f'  - "{c.strip()}"' for c in comments) or "  (none)"
        zone_block     = zone_info if zone_info else "  No significant zone pattern detected."

        prompt = f"""You are an expert {sport_label} coach preparing a player for their next match against a specific opponent.

OPPONENT: {opponent_name}
HEAD-TO-HEAD RECORD: {total_wins}W – {total_losses}L across {total_matches} matches

MISTAKES IN MATCHES AGAINST {opponent_name.upper()} ({total_tagged} tagged losses):
  Swing miss:   {swing_miss}
  Bad footwork: {bad_footwork}
  Other:        {other}

COURT ZONE PATTERN (where {opponent_name} tends to push the player):
{zone_block}

PLAYER'S NOTES FROM PAST MATCHES VS {opponent_name.upper()}:
{comments_block}

Write a targeted scouting report and tactical advice. Follow this structure exactly:
- Paragraph 1 (2–3 sentences): Identify the main pattern {opponent_name} exploits, based on the mistake data and zone info. Be specific.
- Paragraph 2 (1–2 sentences): Give one concrete tactical adjustment or drill to counter it.
- Final sentence: Set a clear goal for the next match against {opponent_name}.

Be direct, warm, and specific. 100–140 words total. No bullet points."""

        response = self.client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[prompt],
        )
        text = (response.text or "").strip()
        return text if text else None
