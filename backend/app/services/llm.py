from __future__ import annotations

import json
import logging

import httpx

logger = logging.getLogger(__name__)


def call_llm(
    prompt: str,
    system_prompt: str = "",
    api_key: str = "",
    base_url: str = "https://api.deepseek.com",
    model: str = "deepseek-chat",
    temperature: float = 0.7,
    max_tokens: int = 2000,
) -> str:
    """Call an OpenAI-compatible LLM API (DeepSeek, OpenAI, etc.).

    Returns the assistant message content as a string.
    Raises RuntimeError on API errors.
    """
    if not api_key:
        raise ValueError("AI_API_KEY is required for LLM calls")

    url = f"{base_url.rstrip('/')}/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }

    with httpx.Client(timeout=60) as client:
        resp = client.post(url, headers=headers, json=payload)

    if resp.status_code != 200:
        logger.error("LLM API error %d: %s", resp.status_code, resp.text[:500])
        raise RuntimeError(f"LLM API returned status {resp.status_code}: {resp.text[:200]}")

    data = resp.json()
    try:
        return data["choices"][0]["message"]["content"]
    except (KeyError, IndexError) as e:
        raise RuntimeError(f"Unexpected LLM response format: {e}") from e


def call_llm_json(
    prompt: str,
    system_prompt: str = "",
    api_key: str = "",
    base_url: str = "https://api.deepseek.com",
    model: str = "deepseek-chat",
    temperature: float = 0.3,
    max_tokens: int = 2000,
) -> dict:
    """Call LLM and parse the response as JSON.

    The prompt should instruct the model to return valid JSON.
    Falls back to extracting JSON from markdown code blocks.
    """
    text = call_llm(
        prompt=prompt,
        system_prompt=system_prompt,
        api_key=api_key,
        base_url=base_url,
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
    )

    # Try direct JSON parse
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Try extracting from ```json ... ``` block
    import re
    m = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(1).strip())
        except json.JSONDecodeError:
            pass

    # Try finding first { ... } block
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(0))
        except json.JSONDecodeError:
            pass

    raise RuntimeError(f"Failed to parse LLM response as JSON: {text[:200]}")
