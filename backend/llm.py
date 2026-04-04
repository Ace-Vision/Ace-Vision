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
