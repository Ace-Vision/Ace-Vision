"""
backend/score_recognizer.py — Extract and parse spoken scores from match video.

Pipeline:
  1. ffmpeg で動画から mono 16kHz WAV を抽出
  2. Whisper でタイムスタンプ付きトランスクリプト取得
  3. 正規表現でスコアパターン (例: "3-2", "3対2") を抽出
  4. avg_logprob でフィルタリング

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

# Whisper avg_logprob の閾値
# 試合録画は環境音で -3〜-4 まで下がることがある
# スコアパターンの正規表現がフィルタ役を担うため閾値は緩めに設定
CONFIDENCE_THRESHOLD = -5.0

# スコアパターン:
#   セパレータあり: "3-2", "3対2", "3、2" など
#   スペース区切り: "0 0", "15 14", "1 0"
_SCORE_RE = re.compile(r'\b(\d{1,2})(?:\s*[-ー対:：、,]\s*|\s+)(\d{1,2})\b')

# 英語の数字語 → アラビア数字 (スコア範囲 0-30)
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
    """英語の数字語をアラビア数字に変換: 'one zero' → '1 0'"""
    return _WORD_NUM_RE.sub(lambda m: _WORD_NUMBERS[m.group(1).lower()], text)


def extract_audio(video_path: str, out_path: str) -> None:
    """動画から mono 16kHz WAV を抽出する。ffmpeg が必要。"""
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
    Whisper でセグメント単位のトランスクリプトを返す。

    Returns:
        [{"start": float, "end": float, "text": str, "avg_logprob": float}, ...]
    """
    model = _load_model(model_size)
    result = model.transcribe(
        audio_path,
        language=language,
        word_timestamps=True,
        verbose=False,
        temperature=0,                   # greedy decoding → 毎回同じ結果
        condition_on_previous_text=False, # セグメント間の依存を切る → 連鎖ハリュシネーション防止
        no_speech_threshold=0.3,         # default 0.6 → 小声のスコアアナウンスを拾うために緩める
        logprob_threshold=-8.0,          # default -1.0 → スコア正規表現がフィルタするので緩める
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
    マッチした文字位置に最も近い単語の開始時刻を返す。
    word_timestamps がなければセグメント開始時刻にフォールバック。
    """
    text = seg["text"]
    words = seg.get("words", [])
    if not words:
        return seg["start"]

    # マッチ文字列がどの単語を含むか探す
    char_pos = 0
    for w in words:
        word_text = w.get("word", "")
        end_pos = char_pos + len(word_text)
        if char_pos <= match_start < end_pos:
            return round(w["start"], 3)
        char_pos = end_pos

    return seg["start"]


_DIGIT_RE = re.compile(r'\d+')

# "11" や "21" など、孤立した2桁数字を 1-1 / 2-1 のスコアペアとして解釈するフォールバック。
# Whisper が "one one" → "11" と書き起こすケースに対応。
# セグメントに他のテキストがない（スコアアナウンス専用セグメント）前提で使う。
_ISOLATED_2DIGIT_RE = re.compile(r'^\W*(\d)(\d)\W*$')

def _try_match_text(text: str, timestamp: float, out: list[dict]) -> None:
    """テキストを正規化してスコアパターンを探し、out に追記する。"""
    normalised = _normalise_numbers(text)
    # 数字が3つ以上 → Whisper の数字羅列ハリュシネーション → 除外
    if len(_DIGIT_RE.findall(normalised)) > 2:
        return
    matched = False
    for m in _SCORE_RE.finditer(normalised):
        out.append({
            "timestamp":      timestamp,
            "my_score":       int(m.group(1)),
            "opponent_score": int(m.group(2)),
        })
        matched = True

    # フォールバック: Whisper が "one one" を "11" と書き起こした場合
    # 生テキスト（正規化前）に対して適用することで、"eleven" → "11" の誤変換を防ぐ。
    # Whisper が実際にアラビア数字で "11" と書いた場合だけ d0-d1 ペアとして解釈する。
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
    セグメントリストからスコアを抽出する。

    単一セグメントでのマッチに加え、隣接セグメントを結合して
    "one" + "zero" のように分断されたケースも捕捉する。

    Returns:
        [{"timestamp": float, "my_score": int, "opponent_score": int}, ...]
    """
    valid = [s for s in segments if s["avg_logprob"] >= CONFIDENCE_THRESHOLD]

    raw: list[dict] = []

    for seg in valid:
        _try_match_text(seg["text"], seg["start"], raw)

    # (timestamp, my_score, opponent_score) の重複を除去
    seen: set[tuple] = set()
    scores: list[dict] = []
    for s in raw:
        key = (s["timestamp"], s["my_score"], s["opponent_score"])
        if key not in seen:
            seen.add(key)
            scores.append(s)

    return sorted(scores, key=lambda s: s["timestamp"])


def compute_rally_results(scores: list[dict]) -> dict:
    """
    スコア履歴からラリーの勝敗を判定する。

    ルール:
      - my_score が増加   → "user"     (ユーザーがラリー獲得)
      - opponent_score 増加 → "opponent" (相手がラリー獲得)
      - 変化なし or 両方増加 → 重複 or 認識ミスとして除外

    Returns:
        {
            "rallies": [
                {
                    "timestamp":      float,   # スコアが読み上げられた時刻
                    "my_score":       int,
                    "opponent_score": int,
                    "rally_winner":   "user" | "opponent" | None,
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
    # タイムスタンプ順にソートし、連続する重複スコアを除去
    sorted_scores = sorted(scores, key=lambda s: s["timestamp"])
    deduped: list[dict] = []
    for s in sorted_scores:
        if deduped and deduped[-1]["my_score"] == s["my_score"] and deduped[-1]["opponent_score"] == s["opponent_score"]:
            continue  # 同スコアが連続して検出された (読み上げの二重検知)
        deduped.append(s)

    # 最初のスコアが 0-0 でない場合、試合開始点として暗黙の 0-0 を挿入
    # (Whisper が開始アナウンスを聞き逃すケースに対応)
    # 最初の検出スコアより少し前 (最低 1 秒) に配置してゼロ秒クリップを防ぐ
    if deduped and not (deduped[0]["my_score"] == 0 and deduped[0]["opponent_score"] == 0):
        first_ts = deduped[0]["timestamp"]
        implicit_ts = max(0.0, first_ts - 1.0)
        deduped.insert(0, {"timestamp": implicit_ts, "my_score": 0, "opponent_score": 0})

    rallies = []
    user_wins = 0
    opponent_wins = 0

    for i, entry in enumerate(deduped):
        if i == 0:
            # 最初のスコアはラリー判定不可 (比較対象がない)
            rallies.append({**entry, "rally_winner": None})
            continue

        prev = deduped[i - 1]
        my_diff   = entry["my_score"]       - prev["my_score"]
        opp_diff  = entry["opponent_score"] - prev["opponent_score"]

        if my_diff > 0 and opp_diff == 0:
            winner = "user"
            user_wins += 1
        elif opp_diff > 0 and my_diff == 0:
            winner = "opponent"
            opponent_wins += 1
        else:
            # 両方増加 or 減少 → 認識エラーとして winner=None
            winner = None

        rallies.append({**entry, "rally_winner": winner})

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
    メインエントリ: 動画ファイルからスコア一覧を返す。

    Args:
        video_path:  入力動画のパス
        model_size:  Whisper モデルサイズ ("medium" | "large" | etc.)
        language:    音声言語コード (デフォルト "en")

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
    各ラリーに対応する動画クリップを切り出して保存する。

    Args:
        video_path:  元動画のパス
        rallies:     compute_rally_results() の "rallies" リスト
        session_id:  保存先ディレクトリを決める ID

    Returns:
        rally_winner が確定しているラリーのみ、index / start_s / end_s / clip_filename を付加して返す
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

        # 0秒以下のクリップは ffmpeg がクラッシュするのでスキップ
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


def run_score_analysis(
    video_path: str,
    model_size: str = "medium",
    language: str = "en",
    session_id: Optional[str] = None,
) -> dict:
    """
    フルパイプライン: 音声認識 → ラリー判定 → クリップ切り出し。

    session_id を指定すると既存ディレクトリ (court_tracker と同じ) にクリップを保存できる。

    Returns:
        {
            "session_id": str,
            "rallies":    [...],  # clip_filename 付き
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
        result   = compute_rally_results(scores)
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
    スコア一覧 + 生トランスクリプトをまとめて返すデバッグ用関数。

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
