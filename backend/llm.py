"""
backend/llm.py — Local LLM coaching feedback via Ollama.

Formats the 3-checkpoint deviation scores into a prompt and sends it
to a locally running Ollama model, returning plain-text coaching advice.
"""

import os
import requests

OLLAMA_URL   = os.environ.get("OLLAMA_URL",   "http://localhost:11434/api/generate")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "gemma3")


def _format_checkpoint(name: str, data: dict | None) -> str:
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


def get_coaching(deviation_scores: dict, skill_level: str = "intermediate") -> dict | None:
    """
    Ask the local Ollama LLM for coaching advice based on 3-checkpoint deviation data.

    Returns {"advice": "<text>"} or None if Ollama is unreachable.
    """
    checkpoints = deviation_scores.get("checkpoints", {})

    prompt_body = "\n\n".join([
        _format_checkpoint("Trophy Position", checkpoints.get("trophy")),
        _format_checkpoint("Racket Drop",     checkpoints.get("racket_drop")),
        _format_checkpoint("Contact",         checkpoints.get("contact")),
    ])

    prompt = f"""You are an expert sports biomechanics coach.
Below are joint deviation scores at 3 key moments of a serve.
severity_score is 0.0 (perfect) to 1.0 (maximum deviation).
The player's skill level is: {skill_level}.

{prompt_body}

Give 2-3 specific coaching corrections targeting the joints with the highest severity scores.
For each correction: state which checkpoint it affects, what the problem is biomechanically, and a concrete drill to fix it.
Be concise and practical. Do not repeat the numbers back — focus on actionable advice."""

    try:
        response = requests.post(
            OLLAMA_URL,
            json={"model": OLLAMA_MODEL, "prompt": prompt, "stream": False},
            timeout=60,
        )
        response.raise_for_status()
        advice = response.json().get("response", "").strip()
        return {"advice": advice} if advice else None
    except (requests.RequestException, KeyError, ValueError):
        return None
