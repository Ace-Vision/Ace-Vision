"""
backend/score_recognizer.py — Extract and parse spoken scores from match video.

Pipeline:
  1. Extract mono 16kHz WAV from video via ffmpeg
  2. Transcribe with Whisper, including word-level timestamps
  3. Match score patterns (e.g. "3-2", "three two") with regex
  4. Filter by avg_logprob confidence threshold

Usage:
    from backend.score_recognizer import recognize_scores
    scores = recognize_scores("match.mp4", model_size="base")
    # -> [{"timestamp": 12.3, "my_score": 3, "opponent_score": 2}, ...]
"""

import os
import re
import subprocess
import tempfile
import uuid
from typing import Optional

# Confidence threshold for Whisper segments.
# Match recordings can drop to -3~-4 due to ambient noise;
# the score regex acts as an additional filter so we keep this loose.
CONFIDENCE_THRESHOLD = -5.0

# Score pattern — separators: "3-2", "3:2", "3 2", and Japanese variants
_SCORE_RE = re.compile(r'\b(\d{1,2})(?:\s*[-ー対:：、,]\s*|\s+)(\d{1,2})\b')

# English number words → Arabic digits (score range 0-30)
_WORD_NUMBERS: dict[str, str] = {
    "zero": "0", "one": "1", "two": "2", "three": "3", "four": "4",
    "five": "5", "six": "6", "seven": "7", "eight": "8", "nine": "9",
    "ten": "10", "eleven": "11", "twelve": "12", "thirteen": "13",
    "fourteen": "14", "fifteen": "15", "sixteen": "16", "seventeen": "17",
    "eighteen": "18", "nineteen": "19", "twenty": "20",
}
_WORD_NUM_RE = re.compile(
    r'\b(' + '|'.join(re.escape(k) for k in _WORD_NUMBERS) + r')\b',
    re.IGNORECASE,
)

def _normalise_numbers(text: str) -> str:
    """Convert English number words to digits: 'one zero' → '1 0', 'two and three' → '2 3'."""
    result = _WORD_NUM_RE.sub(lambda m: _WORD_NUMBERS[m.group(1).lower()], text)
    result = re.sub(r'\s+and\s+', ' ', result, flags=re.IGNORECASE)
    return result


def extract_audio(video_path: str, out_path: str) -> None:
    """Extract mono 16kHz WAV from a video file. Requires ffmpeg."""
    subprocess.run(
        [
            "ffmpeg", "-y", "-i", video_path,
            "-ar", "16000", "-ac", "1",
            "-f", "wav", out_path,
        ],
        check=True,
        capture_output=True,
    )


def _load_model(model_size: str):
    import whisper  # noqa: PLC0415  (lazy import to avoid startup cost)
    return whisper.load_model(model_size)


def transcribe_segments(
    audio_path: str,
    model_size: str = "medium",
    language: str = "en",
) -> list[dict]:
    """
    Transcribe audio with Whisper and return segment-level results.

    Returns:
        [{"start": float, "end": float, "text": str, "avg_logprob": float}, ...]
    """
    model = _load_model(model_size)
    result = model.transcribe(
        audio_path,
        language=language,
        word_timestamps=True,
        verbose=False,
        temperature=(0, 0.2, 0.4),        # retry with higher temperature if greedy fails → breaks loops
        condition_on_previous_text=False,
        no_speech_threshold=0.3,
        logprob_threshold=-8.0,
        compression_ratio_threshold=2.0,  # detect repetitive segments and trigger retry
        initial_prompt=(
            "Badminton match score announcements. After each rally, the current score is called out as two numbers — "
            "server's score first, then receiver's. Each point goes to one side, so only one number changes at a time. "
            "Scores are spoken as word numbers or digits. For example,  zero zero. one zero. one one. two one. two two. three two. three three."
        ),
    )

    segments = []
    for seg in result["segments"]:
        segments.append({
            "start":       round(seg["start"], 3),
            "end":         round(seg["end"],   3),
            "text":        seg["text"].strip(),
            "avg_logprob": seg.get("avg_logprob", 0.0),
            "words":       seg.get("words", []),
        })
    return segments


def _best_timestamp(seg: dict, match_start: int, match_end: int) -> float:
    """
    Return the start time of the word closest to the matched character position.
    Falls back to segment start if word timestamps are unavailable.
    """
    text = seg["text"]
    words = seg.get("words", [])
    if not words:
        return seg["start"]

    char_pos = 0
    for w in words:
        word_text = w.get("word", "")
        end_pos = char_pos + len(word_text)
        if char_pos <= match_start < end_pos:
            return round(w["start"], 3)
        char_pos = end_pos

    return seg["start"]


_DIGIT_RE = re.compile(r'\d+')

# Fallback for isolated 2-digit strings like "11" or "21" → interpret as score pairs 1-1 / 2-1.
# Handles cases where Whisper transcribes "one one" as "11".
# Only applied when the segment contains nothing but the two digits.
_ISOLATED_2DIGIT_RE = re.compile(r'^\W*(\d)(\d)\W*$')

def _try_match_text(text: str, timestamp: float, out: list[dict]) -> None:
    """Normalise text and extract score patterns, appending matches to out."""
    normalised = _normalise_numbers(text)
    digits = _DIGIT_RE.findall(normalised)

    if len(digits) > 2:
        # Many digits → likely a hallucination; take only the first match.
        m = _SCORE_RE.search(normalised)
        if m:
            out.append({
                "timestamp":      timestamp,
                "my_score":       int(m.group(1)),
                "opponent_score": int(m.group(2)),
            })
        return

    matched = False
    for m in _SCORE_RE.finditer(normalised):
        out.append({
            "timestamp":      timestamp,
            "my_score":       int(m.group(1)),
            "opponent_score": int(m.group(2)),
        })
        matched = True

    if not matched:
        m2 = _ISOLATED_2DIGIT_RE.match(text)
        if m2:
            out.append({
                "timestamp":      timestamp,
                "my_score":       int(m2.group(1)),
                "opponent_score": int(m2.group(2)),
            })


def parse_scores(segments: list[dict]) -> list[dict]:
    """
    Extract score entries from a list of Whisper segments.

    In addition to single-segment matches, adjacent segments are combined
    to catch split announcements like "three" + "three" → "3 3" → (3, 3).

    Returns:
        [{"timestamp": float, "my_score": int, "opponent_score": int}, ...]
    """
    valid = [s for s in segments if s["avg_logprob"] >= CONFIDENCE_THRESHOLD]

    raw: list[dict] = []

    for i, seg in enumerate(valid):
        _try_match_text(seg["text"], seg["start"], raw)

        # Combine adjacent segments: catches scores split across two segments
        if i + 1 < len(valid):
            nxt = valid[i + 1]
            if nxt["start"] - seg["end"] < 2.0:
                combined = seg["text"].rstrip(".,!") + " " + nxt["text"].lstrip()
                _try_match_text(combined, seg["start"], raw)

    # Deduplicate exact (timestamp, score) pairs
    seen: set[tuple] = set()
    deduped: list[dict] = []
    for s in raw:
        key = (s["timestamp"], s["my_score"], s["opponent_score"])
        if key not in seen:
            seen.add(key)
            deduped.append(s)

    deduped.sort(key=lambda s: s["timestamp"])

    # Burst filter: keep only the first detection within any 3-second window.
    # Removes hallucination loops like "3,3,3,3,..." at 101.5s, 101.6s, ...
    MIN_SCORE_GAP = 3.0
    burst_filtered: list[dict] = []
    for s in deduped:
        if not burst_filtered or s["timestamp"] - burst_filtered[-1]["timestamp"] >= MIN_SCORE_GAP:
            burst_filtered.append(s)

    return burst_filtered


def compute_rally_results(scores: list[dict], match_start_s: float = 0.0) -> dict:
    """
    Determine rally winners from a sequence of detected scores.

    Rules:
      - only my_score increases    → "user"     wins the rally
      - only opponent_score increases → "opponent" wins the rally
      - both increase (missed rallies bundled) → "both"
      - score decreases or unchanged → recognition error, entry discarded

    Invalid entries do NOT update last_valid, so subsequent valid scores
    are still compared against the last correct state.

    Returns:
        {
            "rallies": [
                {
                    "timestamp":      float,   # time score was announced
                    "my_score":       int,
                    "opponent_score": int,
                    "rally_winner":   "user" | "opponent" | "both" | None,
                    "prev_my":        int | None,
                    "prev_opp":       int | None,
                },
                ...
            ],
            "summary": {
                "user_wins":     int,
                "opponent_wins": int,
                "total_rallies": int,
            },
        }
    """
    # Sort by timestamp and remove consecutive duplicate scores
    sorted_scores = sorted(scores, key=lambda s: s["timestamp"])
    deduped: list[dict] = []
    for s in sorted_scores:
        if deduped and deduped[-1]["my_score"] == s["my_score"] and deduped[-1]["opponent_score"] == s["opponent_score"]:
            continue  # duplicate score detected (double announcement)
        deduped.append(s)

    # If the first detected score is not 0-0, insert an implicit 0-0 as match start.
    # Placed 1 second before the first detection to avoid zero-length clips.
    if deduped and not (deduped[0]["my_score"] == 0 and deduped[0]["opponent_score"] == 0):
        deduped.insert(0, {"timestamp": match_start_s, "my_score": 0, "opponent_score": 0})

    rallies: list[dict] = []
    user_wins = 0
    opponent_wins = 0

    # last_valid: most recent accepted score; not updated on invalid entries
    last_valid = deduped[0]
    rallies.append({**last_valid, "rally_winner": None, "prev_my": None, "prev_opp": None})

    for entry in deduped[1:]:
        my_diff  = entry["my_score"]       - last_valid["my_score"]
        opp_diff = entry["opponent_score"] - last_valid["opponent_score"]

        if my_diff >= 1 and opp_diff == 0:
            winner = "user"
            user_wins += 1
        elif opp_diff >= 1 and my_diff == 0:
            winner = "opponent"
            opponent_wins += 1
        elif my_diff >= 1 and opp_diff >= 1:
            # Both sides increased — multiple missed rallies bundled into one clip
            winner = "both"
        else:
            # Score decreased or unchanged → recognition error; discard and keep last_valid
            continue

        rallies.append({
            **entry,
            "rally_winner": winner,
            "prev_my":  last_valid["my_score"],
            "prev_opp": last_valid["opponent_score"],
        })
        last_valid = entry

    total = user_wins + opponent_wins
    return {
        "rallies": rallies,
        "summary": {
            "user_wins":     user_wins,
            "opponent_wins": opponent_wins,
            "total_rallies": total,
        },
    }


def recognize_scores(
    video_path: str,
    model_size: str = "medium",
    language: str = "en",
) -> list[dict]:
    """
    Convenience entry point: return raw score list from a video file.

    Args:
        video_path:  path to the input video
        model_size:  Whisper model size ("medium" | "large" | etc.)
        language:    audio language code (default "en")

    Returns:
        [{"timestamp": float, "my_score": int, "opponent_score": int}, ...]
    """
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        audio_path = tmp.name

    try:
        extract_audio(video_path, audio_path)
        segments = transcribe_segments(audio_path, model_size=model_size, language=language)
        scores = parse_scores(segments)
        return compute_rally_results(scores)
    finally:
        if os.path.exists(audio_path):
            os.unlink(audio_path)


def extract_rally_clips(video_path: str, rallies: list[dict], session_id: str) -> list[dict]:
    """
    Cut and save a video clip for each rally.

    Args:
        video_path:  source video path
        rallies:     "rallies" list from compute_rally_results()
        session_id:  output directory identifier

    Returns:
        Entries with a confirmed rally_winner, enriched with
        index / start_s / end_s / clip_filename.
    """
    out_dir = os.path.join("data", "results", session_id)
    os.makedirs(out_dir, exist_ok=True)

    clipped: list[dict] = []
    clip_idx = 0

    for i, rally in enumerate(rallies):
        if rally["rally_winner"] is None:
            continue

        start_s = rallies[i - 1]["timestamp"] if i > 0 else 0.0
        end_s   = rally["timestamp"]
        winner  = rally["rally_winner"]

        # Skip clips shorter than 1 second — ffmpeg crashes on zero-length segments
        if end_s - start_s < 1.0:
            continue

        filename = f"rally_{clip_idx:03d}_{winner}.mp4"
        out_path = os.path.join(out_dir, filename)

        subprocess.run(
            [
                "ffmpeg", "-y",
                "-ss", str(start_s),
                "-to", str(end_s),
                "-i", video_path,
                "-c:v", "libx264", "-preset", "fast",
                "-c:a", "aac",
                "-movflags", "+faststart",
                out_path,
            ],
            check=True,
            capture_output=True,
        )

        clipped.append({
            **rally,
            "index":         clip_idx,
            "start_s":       start_s,
            "end_s":         end_s,
            "clip_filename": filename,
        })
        clip_idx += 1

    return clipped


def _get_video_duration(video_path: str) -> float:
    """Return video duration in seconds via ffprobe."""
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", video_path],
        capture_output=True, text=True,
    )
    try:
        return float(r.stdout.strip())
    except ValueError:
        return 0.0


def run_score_analysis(
    video_path: str,
    model_size: str = "medium",
    language: str = "en",
    session_id: Optional[str] = None,
    final_score: Optional[tuple[int, int]] = None,
    match_start_s: float = 0.0,
) -> dict:
    """
    Full pipeline: speech recognition → rally determination → clip extraction.

    Saves clips into an existing session directory when session_id is provided
    (shared with court_tracker output).

    If final_score is given, it takes priority over Whisper detections:
      1. Detections that exceed final_score are discarded as hallucinations.
      2. final_score is injected as a ground-truth terminal entry.

    Returns:
        {
            "session_id": str,
            "rallies":    [...],  # each entry includes clip_filename
            "summary":    {"user_wins", "opponent_wins", "total_rallies"},
        }
    """
    if session_id is None:
        session_id = uuid.uuid4().hex[:12]

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        audio_path = tmp.name

    try:
        extract_audio(video_path, audio_path)
        segments = transcribe_segments(audio_path, model_size=model_size, language=language)
        scores   = parse_scores(segments)

        if final_score is not None:
            final_my, final_opp = final_score
            # Drop any Whisper detections that exceeded the user-provided final score
            scores = [s for s in scores
                      if s["my_score"] <= final_my and s["opponent_score"] <= final_opp]
            # Inject the final score as a guaranteed terminal entry
            last_ts  = scores[-1]["timestamp"] if scores else 0.0
            duration = _get_video_duration(video_path)
            scores.append({
                "timestamp":      max(last_ts + 1.0, duration - 0.5),
                "my_score":       final_my,
                "opponent_score": final_opp,
            })

        result = compute_rally_results(scores, match_start_s=match_start_s)
    finally:
        if os.path.exists(audio_path):
            os.unlink(audio_path)

    clipped = extract_rally_clips(video_path, result["rallies"], session_id)

    return {
        "session_id": session_id,
        "rallies":    clipped,
        "summary":    result["summary"],
    }


def recognize_scores_with_transcript(
    video_path: str,
    model_size: str = "base",
    language: str = "en",
) -> dict:
    """
    Debug helper: return score list together with raw Whisper transcript.

    Returns:
        {
            "scores": [...],
            "segments": [{"start", "end", "text", "avg_logprob"}, ...],
        }
    """
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        audio_path = tmp.name

    try:
        extract_audio(video_path, audio_path)
        segments = transcribe_segments(audio_path, model_size=model_size, language=language)
        scores = parse_scores(segments)
        rally_result = compute_rally_results(scores)
        clean_segments = [
            {k: v for k, v in seg.items() if k != "words"}
            for seg in segments
        ]
        return {**rally_result, "segments": clean_segments}
    finally:
        if os.path.exists(audio_path):
            os.unlink(audio_path)
