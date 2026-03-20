"""
SkillPathForge AI — LLM Client
---------------------------------
Supports both Claude (Anthropic) and Gemini (Google).
Automatically detects which key is available and uses it.

Priority:
  1. Claude API  (if CLAUDE_API_KEY is set and valid)
  2. Gemini API  (if GEMINI_API_KEY is set and valid)
  3. Fallback    (if neither key works)

To switch:
  Set CLAUDE_API_KEY in .env  → uses Claude
  Set GEMINI_API_KEY in .env  → uses Gemini
  Set neither / dummy key     → uses fallback
"""

import json
import os
from typing import Optional

from dotenv import load_dotenv

load_dotenv()


# ── Config ────────────────────────────────────────────────────────

CLAUDE_MODEL:  str = "claude-sonnet-4-6"
GEMINI_MODEL:  str = "gemini-1.5-flash"
MAX_TOKENS:    int = 2048
TEMPERATURE:   float = 0.1


# ── Exceptions ────────────────────────────────────────────────────

class ClaudeAPIError(Exception):
    """Raised when LLM API call fails."""
    pass

class ClaudeParseError(Exception):
    """Raised when response cannot be parsed."""
    pass

class ClaudeRateLimitError(Exception):
    """Raised when API rate limit is hit."""
    pass


# ── Detect available provider ─────────────────────────────────────

def _get_provider() -> str:
    """
    Detects which LLM provider to use based on
    environment variables.

    Returns:
        "claude"   → valid Claude key found
        "gemini"   → valid Gemini key found
        "fallback" → no valid key found
    """
    claude_key = os.getenv("CLAUDE_API_KEY", "")
    gemini_key = os.getenv("GEMINI_API_KEY", "")

    # Check Claude key is real (not dummy)
    if (
        claude_key and
        claude_key != "your_claude_api_key_here" and
        claude_key != "dummy_key_for_testing" and
        claude_key.startswith("sk-ant-")
    ):
        return "claude"

    # Check Gemini key is real
    if (
        gemini_key and
        gemini_key != "your_gemini_api_key_here" and
        len(gemini_key) > 10
    ):
        return "gemini"

    return "fallback"


# ── Claude caller ─────────────────────────────────────────────────

def _call_claude(
    system_prompt: str,
    user_message:  str,
    max_tokens:    int = MAX_TOKENS,
) -> str:
    """
    Calls Claude API (Anthropic).

    Args:
        system_prompt: system instructions
        user_message:  user message
        max_tokens:    max response tokens

    Returns:
        raw text response
    """
    import anthropic

    api_key = os.getenv("CLAUDE_API_KEY")
    client  = anthropic.Anthropic(api_key=api_key)

    response = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=max_tokens,
        temperature=TEMPERATURE,
        system=system_prompt,
        messages=[
            {
                "role":    "user",
                "content": user_message,
            }
        ],
    )

    return response.content[0].text


# ── Gemini caller ─────────────────────────────────────────────────

def _call_gemini(
    system_prompt: str,
    user_message:  str,
) -> str:
    """
    Calls Gemini API (Google).
    Free tier — no credit card needed.

    Get free key at:
    https://aistudio.google.com/apikey

    Args:
        system_prompt: system instructions
        user_message:  user message

    Returns:
        raw text response
    """
    import google.generativeai as genai

    api_key = os.getenv("GEMINI_API_KEY")
    genai.configure(api_key=api_key)

    model = genai.GenerativeModel(
        model_name=GEMINI_MODEL,
        system_instruction=system_prompt,
    )

    response = model.generate_content(user_message)
    return response.text


# ── Main call function ────────────────────────────────────────────

def call_claude(
    system_prompt: str,
    user_message:  str,
    max_tokens:    int = MAX_TOKENS,
) -> str:
    """
    Main LLM caller — auto-selects provider.

    Tries Claude first, then Gemini, then raises
    error so generator.py can use fallback.

    Args:
        system_prompt: system instructions
        user_message:  user message
        max_tokens:    max tokens

    Returns:
        raw text response string

    Raises:
        ClaudeAPIError: if all providers fail
    """
    provider = _get_provider()

    if provider == "claude":
        try:
            return _call_claude(
                system_prompt=system_prompt,
                user_message=user_message,
                max_tokens=max_tokens,
            )
        except Exception as e:
            raise ClaudeAPIError(
                f"Claude API failed: {str(e)}"
            )

    elif provider == "gemini":
        try:
            return _call_gemini(
                system_prompt=system_prompt,
                user_message=user_message,
            )
        except Exception as e:
            raise ClaudeAPIError(
                f"Gemini API failed: {str(e)}"
            )

    else:
        # No valid key — trigger fallback in generator.py
        raise ClaudeAPIError(
            "No valid API key found — using fallback"
        )


# ── JSON parser ───────────────────────────────────────────────────

def parse_claude_json(raw_text: str) -> dict:
    """
    Parses LLM response as JSON.
    Handles markdown code blocks.

    Args:
        raw_text: raw response text

    Returns:
        parsed dict

    Raises:
        ClaudeParseError: if JSON parsing fails
    """
    if not raw_text or not raw_text.strip():
        raise ClaudeParseError("Empty response from LLM")

    text = raw_text.strip()

    # Remove markdown code blocks
    if text.startswith("```json"):
        text = text[7:]
    elif text.startswith("```"):
        text = text[3:]

    if text.endswith("```"):
        text = text[:-3]

    text = text.strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        raise ClaudeParseError(
            f"Failed to parse JSON: {e}\n"
            f"Raw: {raw_text[:200]}"
        )


# ── Combined call + parse ─────────────────────────────────────────

def call_claude_json(
    system_prompt: str,
    user_message:  str,
    max_tokens:    int = MAX_TOKENS,
) -> dict:
    """
    Calls LLM and parses response as JSON.

    Args:
        system_prompt: system instructions
        user_message:  user message
        max_tokens:    max tokens

    Returns:
        parsed dict

    Raises:
        ClaudeAPIError:    on API failures
        ClaudeParseError:  on JSON failures
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
    Checks which LLM provider is active.

    Returns:
        dict with status and provider info
    """
    provider = _get_provider()

    if provider == "fallback":
        return {
            "status":   "fallback",
            "model":    "rule-based",
            "provider": "none",
            "message":  (
                "No API key found — "
                "fallback mode active"
            ),
        }

    try:
        response = call_claude(
            system_prompt="You are a health check assistant.",
            user_message="Reply with exactly: OK",
            max_tokens=10,
        )
        return {
            "status":   "healthy",
            "model":    (
                CLAUDE_MODEL if provider == "claude"
                else GEMINI_MODEL
            ),
            "provider": provider,
            "message":  response.strip(),
        }

    except Exception as e:
        return {
            "status":   "unhealthy",
            "model":    "unknown",
            "provider": provider,
            "message":  str(e),
        }