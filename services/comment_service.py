"""Structured review-comment suggestions for the hackathon demo."""

import json

from google import genai
from google.genai import types

from config import GEMINI_MODEL, GENAI_LOCATION, PROJECT_ID
from services.prompt_loader import load_prompt


comment_prompt = load_prompt("comment_prompt.txt")
client = genai.Client(vertexai=True, project=PROJECT_ID, location=GENAI_LOCATION)


def suggest_comment(
    *,
    document_name: str,
    category: str,
    page: int,
    from_line: int,
    to_line: int,
    selected_text: str,
    context: str,
    reviewer_note: str = "",
) -> dict:
    """Generate a structured draft that always requires human review."""
    lines = str(from_line) if from_line == to_line else f"{from_line}-{to_line}"
    prompt = (
        comment_prompt.replace("{document}", document_name)
        .replace("{category}", category)
        .replace("{page}", str(page))
        .replace("{lines}", lines)
        .replace("{selected_text}", selected_text)
        .replace("{context}", context)
        .replace("{reviewer_note}", reviewer_note or "None")
    )
    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(response_mime_type="application/json"),
    )
    payload = json.loads(response.text)
    required = {
        "issue",
        "evidence",
        "proposed_comment",
        "proposed_resolution",
        "confidence",
    }
    if not required.issubset(payload):
        raise ValueError("Model response is missing required review fields")
    payload["demo_only"] = True
    payload["requires_human_review"] = True
    return payload
