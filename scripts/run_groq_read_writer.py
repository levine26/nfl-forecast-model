from __future__ import annotations

"""Generate one Sunday Signal editorial response with Groq's free-tier writer.

The model is allowed to research and write prose only. Existing deterministic
composition and validation continue to own every LevLine number, pick, source
gate, T-120 lock, and publication decision.
"""

import argparse
import os
from pathlib import Path
import re
import time

import requests

API_URL = "https://api.groq.com/openai/v1/chat/completions"
DEFAULT_MODEL = "openai/gpt-oss-120b"


def build_payload(prompt: str, model: str = DEFAULT_MODEL) -> dict:
    return {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.6,
        "top_p": 1,
        # A one-game response is intentionally compact: headline + 55-100 word
        # matchup paragraph + 18-40 word rationale + two direct source records.
        # Keeping this bounded materially reduces free-tier TPM pressure.
        "max_completion_tokens": 1600,
        "stream": False,
        # Browser search is server-side on Groq. We deliberately do not request
        # structured output because Groq does not support structured outputs and
        # browser search in the same request. The downstream JSON extractor and
        # publication validator remain the fail-closed schema boundary.
        "tool_choice": "required",
        "tools": [{"type": "browser_search"}],
        "citation_options": "disabled",
    }


def _retry_delay(response: requests.Response, attempt: int) -> float:
    raw = response.headers.get("Retry-After", "").strip()
    try:
        delay = float(raw)
        if delay >= 0:
            # Groq's free tier is constrained primarily by tokens/minute. Honor
            # the server's reset window instead of retrying too aggressively.
            return min(delay, 120.0)
    except (TypeError, ValueError):
        pass
    return min(2.0 ** attempt, 20.0)


def isolate_final_json(text: str) -> str:
    """Drop browser-search preamble while leaving schema repair to validators.

    Groq browser search may prepend research snippets to message.content even when
    the requested final answer is JSON. Sunday Signal accepts only the last object
    whose root begins with a `games` key; everything else is discarded before the
    existing strict validator sees the candidate.
    """
    raw = str(text or "").strip()
    matches = list(re.finditer(r'\{\s*"games"\s*:', raw))
    if not matches:
        return raw
    start = matches[-1].start()
    end = raw.rfind("}")
    if end <= start:
        return raw[start:]
    return raw[start:end + 1].strip()


def generate(
    prompt: str,
    *,
    api_key: str,
    model: str = DEFAULT_MODEL,
    attempts: int = 3,
    timeout: float = 120.0,
) -> str:
    if not api_key.strip():
        raise ValueError("GROQ_API_KEY is required")

    payload = build_payload(prompt, model=model)
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    last_error = "unknown Groq failure"

    for attempt in range(1, attempts + 1):
        try:
            response = requests.post(API_URL, headers=headers, json=payload, timeout=timeout)
        except requests.RequestException as exc:
            last_error = f"network error: {exc}"
            if attempt < attempts:
                time.sleep(min(2.0 ** attempt, 20.0))
                continue
            break

        if response.status_code == 200:
            try:
                data = response.json()
                content = data["choices"][0]["message"]["content"]
            except (ValueError, KeyError, IndexError, TypeError) as exc:
                raise RuntimeError(f"Groq returned an invalid completion payload: {exc}") from exc
            if not isinstance(content, str) or not content.strip():
                raise RuntimeError("Groq returned an empty completion")
            return isolate_final_json(content)

        body = response.text.strip().replace("\n", " ")[:1200]
        last_error = f"HTTP {response.status_code}: {body}"
        retryable = response.status_code == 429 or 500 <= response.status_code < 600
        if retryable and attempt < attempts:
            time.sleep(_retry_delay(response, attempt))
            continue
        break

    raise RuntimeError(f"Groq writer failed after {attempts} attempt(s): {last_error}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--prompt-file", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--model", default=os.getenv("GROQ_MODEL", DEFAULT_MODEL))
    parser.add_argument("--attempts", type=int, default=3)
    args = parser.parse_args()

    api_key = os.getenv("GROQ_API_KEY", "")
    if not api_key.strip():
        raise SystemExit("GROQ_API_KEY is not configured; refusing to generate unvalidated fallback prose")

    prompt = Path(args.prompt_file).read_text(encoding="utf-8")
    try:
        content = generate(prompt, api_key=api_key, model=args.model, attempts=max(1, args.attempts))
    except Exception as exc:
        raise SystemExit(str(exc)) from exc

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(content + "\n", encoding="utf-8")
    print(f"Groq Read writer completed with {args.model} -> {output}")


if __name__ == "__main__":
    main()
