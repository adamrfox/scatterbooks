import base64
import json
import re

import httpx

from app.schemas.cover_identification import IdentifyCoverResult

ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_VERSION = "2023-06-01"
MODEL = "claude-haiku-4-5-20251001"
REQUEST_TIMEOUT = 20.0

PROMPT = (
    "You are looking at a photo of a book cover. Identify the book's title and "
    "author. Respond with ONLY a JSON object of the form "
    '{"title": "...", "author": "..."} and no other text. If you cannot '
    'confidently identify the book, respond with {"title": null, "author": null}.'
)


class CoverIdentificationError(Exception):
    pass


async def identify_book_from_photo(image_bytes: bytes, api_key: str) -> IdentifyCoverResult:
    encoded = base64.b64encode(image_bytes).decode("ascii")
    payload = {
        "model": MODEL,
        "max_tokens": 300,
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {"type": "base64", "media_type": "image/jpeg", "data": encoded},
                    },
                    {"type": "text", "text": PROMPT},
                ],
            }
        ],
    }
    headers = {
        "x-api-key": api_key,
        "anthropic-version": ANTHROPIC_VERSION,
        "content-type": "application/json",
    }

    async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
        response = await client.post(ANTHROPIC_API_URL, headers=headers, json=payload)
    response.raise_for_status()
    data = response.json()

    try:
        text = data["content"][0]["text"]
    except (KeyError, IndexError, TypeError) as exc:
        raise CoverIdentificationError("Unexpected response shape from Claude") from exc

    parsed = _parse_json_response(text)
    title = parsed.get("title") or None
    author = parsed.get("author") or None
    return IdentifyCoverResult(title=title, author=author)


def _parse_json_response(text: str) -> dict:
    # Models sometimes wrap JSON in a markdown code fence despite instructions
    # not to -- strip one off if present before parsing.
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip())
    try:
        result = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise CoverIdentificationError("Could not parse Claude's response") from exc
    if not isinstance(result, dict):
        raise CoverIdentificationError("Unexpected response shape from Claude")
    return result
