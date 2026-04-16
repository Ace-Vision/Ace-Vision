"""
backend/llm.py — Claude API integration for coaching feedback.

Sends deviation scores to Claude (claude-sonnet-4-6) with a biomechanics
coaching system prompt and returns structured coaching JSON.

LLM rules (enforced by system prompt):
- Every correction references a specific JSON field by name
- No generic advice
- Address highest severity_score first
- Maximum 2 corrections, one drill each
- If hip_leads_shoulder is false, address kinetic chain first
- Return only valid JSON

Key responsibilities:
- Build the system prompt and user message from deviation data
- Call the Anthropic API via the anthropic Python SDK
- Parse and validate the LLM response as JSON
- Return coaching dict with corrections list and summary string
"""

import os
import json
import anthropic


def get_coaching(deviation_scores: dict, skill_level: str) -> dict:
    """
    Call Claude to generate targeted coaching feedback from deviation scores.

    Args:
        deviation_scores (dict): Output from scorer.score_deviations().
        skill_level (str): Player's self-reported level.

    Returns:
        dict: {"corrections": [...], "summary": "..."}
    """
    client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

    deviations_text = json.dumps(deviation_scores, indent=2)

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        system="""You are an expert sports biomechanics coach. Analyse the joint deviation scores provided and return coaching feedback as valid JSON only.

Rules:
- Address the 2 joints with the highest severity_score only
- Each correction must reference the exact joint field name from the data
- No generic advice — every sentence must be specific to the deviation values given
- If hip_leads_shoulder is false, address kinetic chain timing first
- Return ONLY valid JSON in this exact format, no other text:
{
  "corrections": [
    {
      "joint": "<exact joint field name>",
      "deviation_deg": <number>,
      "impact": "<specific biomechanical consequence of this deviation>",
      "drill": "<specific corrective drill with a measurable target angle or rep count>"
    }
  ],
  "summary": "<1-2 sentence overall assessment tailored to the skill level>"
}""",
        messages=[
            {
                "role": "user",
                "content": f"Skill level: {skill_level}\n\nDeviation scores:\n{deviations_text}"
            }
        ]
    )

    raw = message.content[0].text.strip()
    return json.loads(raw)
