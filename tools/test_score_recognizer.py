"""
tools/test_score_recognizer.py — Score recognizer のローカルテスト

Usage:
    python tools/test_score_recognizer.py                   # data/samples/voice/ 以下を全部テスト
    python tools/test_score_recognizer.py path/to/video.mp4 # 個別ファイル指定
    python tools/test_score_recognizer.py --model medium    # モデル切り替え
    python tools/test_score_recognizer.py --transcript      # 生トランスクリプトも表示
"""

import sys
import os
import glob
import argparse

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from backend.score_recognizer import recognize_scores_with_transcript, CONFIDENCE_THRESHOLD

VOICE_DIR = "data/samples/voice"


def run(path: str, model: str, show_transcript: bool):
    label = os.path.splitext(os.path.basename(path))[0]
    expected = label if "-" in label else "?"

    print(f"\n{'─' * 50}")
    print(f"  File    : {os.path.basename(path)}")
    print(f"  Expected: {expected}")
    print(f"  Model   : {model}")

    result = recognize_scores_with_transcript(path, model_size=model)
    rallies = result.get("rallies", [])
    summary = result.get("summary", {})

    if rallies:
        for r in rallies:
            mm = r['my_score']
            op = r['opponent_score']
            ts = r['timestamp']
            score_match = "✓" if f"{mm}-{op}" == expected else " "
            winner = r.get("rally_winner")
            if winner == "user":
                rally_str = "  WIN "
            elif winner == "opponent":
                rally_str = "  LOSE"
            else:
                rally_str = "  --- "
            print(f"  {score_match}{rally_str}  t={ts:6.2f}s  {mm}-{op}")
        print(f"\n  Summary: {summary.get('user_wins', 0)}W / {summary.get('opponent_wins', 0)}L  ({summary.get('total_rallies', 0)} rallies)")
    else:
        print("  (no scores detected)")

    if show_transcript:
        print("\n  Transcript segments:")
        for seg in result["segments"]:
            prob = seg['avg_logprob']
            flag = "" if prob >= CONFIDENCE_THRESHOLD else "  [low-conf, skipped]"
            print(f"    [{seg['start']:6.2f}s] logp={prob:.2f}{flag}  {seg['text']!r}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("files", nargs="*", help="動画ファイル (省略時は voice/ 以下を全て)")
    parser.add_argument("--model", default="medium", help="Whisper モデルサイズ (base/medium/large)")
    parser.add_argument("--transcript", action="store_true", help="生トランスクリプトも表示")
    args = parser.parse_args()

    if args.files:
        paths = args.files
    else:
        exts = ["*.mp4", "*.mov", "*.m4a", "*.wav", "*.mp3"]
        paths = []
        for ext in exts:
            paths.extend(sorted(glob.glob(os.path.join(VOICE_DIR, ext))))

    if not paths:
        print(f"No files found in {VOICE_DIR}/")
        print("Usage: python tools/test_score_recognizer.py [file] [--model medium] [--transcript]")
        sys.exit(1)

    for path in paths:
        run(path, model=args.model, show_transcript=args.transcript)

    print(f"\n{'─' * 50}")
    print(f"Done. {len(paths)} file(s) tested.")


if __name__ == "__main__":
    main()
