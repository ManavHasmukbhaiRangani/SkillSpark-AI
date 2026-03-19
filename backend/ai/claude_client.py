"""
SkillPathForge AI — Claude API Client
---------------------------------------
Anthropic SDK setup and API call wrapper.

Responsibilities:
  - Load API key from environment
  - Initialise Anthropic client
  - Make structured API calls
  - Handle rate limits and timeouts
  - Parse and validate responses

Claude is called ONLY from this file.
All other files import from here.
"""

import json
import os
from typing import Optional

import anthropic
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


# ── Config ────────────────────────────────────────────────────────

MODEL_NAME:    str = "claude-sonnet-4-6"
MAX_TOKENS:    int = 2048
TEMPERATURE:   float = 0.1    # low = consistent, predictable output
TIMEOUT:       int = 30       # seconds


# ── Exceptions ────────────────────────────────────────────────────

class ClaudeAPIError(Exception):
    """Raised when Claude API call fails."""
    pass


class ClaudeParseError(Exception):
    """Raised when Claude response cannot be parsed."""
    pass


class ClaudeRateLimitError(Exception):
    """Raised when API rate limit is hit."""
    pass


# ── Client setup ──────────────────────────────────────────────────

def _get_client() -> anthropic.Anthropic:
    """
    Creates and returns Anthropic client.

    Reads API key from environment variable.

    Returns:
        Anthropic client instance

    Raises:
        ClaudeAPIError: if API key not found
    """
    api_key = os.getenv("CLAUDE_API_KEY")

    if not api_key:
        raise ClaudeAPIError(
            "CLAUDE_API_KEY not found in environment. "
            "Check your .env file."
        )

    return anthropic.Anthropic(api_key=api_key)


# ── Main call function ────────────────────────────────────────────

def call_claude(
    system_prompt:  str,
    user_message:   str,
    max_tokens:     int = MAX_TOKENS,
    temperature:    float = TEMPERATURE,
) -> str:
    """
    Makes a single Claude API call.

    Args:
        system_prompt: system instructions for Claude
        user_message:  user message content
        max_tokens:    maximum response tokens
        temperature:   response randomness (0.0-1.0)

    Returns:
        raw response text string from Claude

    Raises:
        ClaudeAPIError:       on API failures
        ClaudeRateLimitError: on rate limit
    """
    try:
        client = _get_client()

        response = client.messages.create(
            model=MODEL_NAME,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system_prompt,
            messages=[
                {
                    "role":    "user",
                    "content": user_message,
                }
            ],
        )

        # Extract text from response
        if not response.content:
            raise ClaudeAPIError("Empty response from Claude")

        raw_text = response.content[0].text

        return raw_text

    except anthropic.RateLimitError as e:
        raise ClaudeRateLimitError(
            f"Claude rate limit hit: {str(e)}"
        )

    except anthropic.APITimeoutError as e:
        raise ClaudeAPIError(
            f"Claude API timeout after {TIMEOUT}s: {str(e)}"
        )

    except anthropic.APIConnectionError as e:
        raise ClaudeAPIError(
            f"Claude API connection error: {str(e)}"
        )

    except anthropic.APIStatusError as e:
        raise ClaudeAPIError(
            f"Claude API error {e.status_code}: {str(e)}"
        )

    except Exception as e:
        raise ClaudeAPIError(
            f"Unexpected error calling Claude: {str(e)}"
        )


# ── JSON response parser ──────────────────────────────────────────

def parse_claude_json(raw_text: str) -> dict:
    """
    Parses Claude response as JSON.

    Claude sometimes wraps JSON in markdown code blocks.
    This function handles both cases:
      - Raw JSON
      - JSON wrapped in ```json ... ```

    Args:
        raw_text: raw text response from Claude

    Returns:
        parsed dict

    Raises:
        ClaudeParseError: if JSON parsing fails
    """
    if not raw_text or not raw_text.strip():
        raise ClaudeParseError("Empty response from Claude")

    # Clean up response text
    text = raw_text.strip()

    # Remove markdown code blocks if present
    if text.startswith("```json"):
        text = text[7:]
    elif text.startswith("```"):
        text = text[3:]

    if text.endswith("```"):
        text = text[:-3]

    text = text.strip()

    # Parse JSON
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        raise ClaudeParseError(
            f"Failed to parse Claude response as JSON: {e}\n"
            f"Raw response: {raw_text[:200]}..."
        )


# ── Call with JSON parsing ────────────────────────────────────────

def call_claude_json(
    system_prompt: str,
    user_message:  str,
    max_tokens:    int = MAX_TOKENS,
) -> dict:
    """
    Makes Claude API call and parses response as JSON.

    Combines call_claude() and parse_claude_json()
    into single convenience function.

    Args:
        system_prompt: system instructions
        user_message:  user message content
        max_tokens:    maximum response tokens

    Returns:
        parsed dict from Claude response

    Raises:
        ClaudeAPIError:    on API failures
        ClaudeParseError:  on JSON parse failures
        ClaudeRateLimitError: on rate limit
    """
    raw_text = call_claude(
        system_prompt=system_prompt,
        user_message=user_message,
        max_tokens=max_tokens,
    )

    return parse_claude_json(raw_text)


# ── Health check ──────────────────────────────────────────────────

def check_claude_health() -> dict:
    """
    Verifies Claude API is reachable and responding.
    Called on FastAPI startup.

    Returns:
        dict with status and model info
    """
    try:
        response = call_claude(
            system_prompt="You are a health check assistant.",
            user_message="Reply with exactly: OK",
            max_tokens=10,
        )

        return {
            "status":  "healthy",
            "model":   MODEL_NAME,
            "message": response.strip(),
        }

    except ClaudeRateLimitError:
        return {
            "status":  "rate_limited",
            "model":   MODEL_NAME,
            "message": "Rate limit hit — will retry",
        }

    except ClaudeAPIError as e:
        return {
            "status":  "unhealthy",
            "model":   MODEL_NAME,
            "message": str(e),
        }