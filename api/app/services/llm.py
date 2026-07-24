"""OpenAI client with retry, cost logging, and JSON repair."""
import asyncio
import json
import logging
import random
import re
from pathlib import Path

import openai

from app.config import settings

logger = logging.getLogger(__name__)

PROMPTS_DIR = Path(__file__).parent.parent / "prompts"

# gpt-5.6-luna pricing (per 1M tokens)
_INPUT_COST_PER_M = 1.0
_OUTPUT_COST_PER_M = 6.0


def _cost(input_tokens: int, output_tokens: int) -> float:
    return (input_tokens / 1_000_000) * _INPUT_COST_PER_M + (output_tokens / 1_000_000) * _OUTPUT_COST_PER_M


def load_prompt(filename: str) -> str:
    return (PROMPTS_DIR / filename).read_text()


def _get_client() -> openai.OpenAI:
    return openai.OpenAI(api_key=settings.openai_api_key)


async def complete(
    prompt: str,
    system: str = "",
    max_tokens: int | None = None,
) -> tuple[str, int, int, float]:
    """Returns (text, input_tokens, output_tokens, cost_usd)."""
    client = _get_client()
    mt = max_tokens or settings.llm_max_tokens

    for attempt in range(3):
        try:
            def _call():
                messages = []
                if system:
                    messages.append({"role": "system", "content": system})
                messages.append({"role": "user", "content": prompt})
                return client.chat.completions.create(
                    model=settings.llm_model,
                    max_completion_tokens=mt,
                    messages=messages,
                )

            resp = await asyncio.to_thread(_call)
            text = resp.choices[0].message.content
            inp = resp.usage.prompt_tokens
            out = resp.usage.completion_tokens
            cost = _cost(inp, out)
            logger.info("LLM call: %d in / %d out / $%.4f", inp, out, cost)
            return text, inp, out, cost
        except openai.RateLimitError:
            wait = (2 ** attempt) + random.uniform(0, 1)
            logger.warning("Rate limit hit, retrying in %.1fs", wait)
            await asyncio.sleep(wait)
        except openai.APIStatusError as exc:
            if attempt == 2:
                raise
            wait = (2 ** attempt) + random.uniform(0, 1)
            logger.warning("API error %s, retrying in %.1fs", exc.status_code, wait)
            await asyncio.sleep(wait)

    raise RuntimeError("LLM failed after 3 attempts")


def _extract_json(text: str) -> str:
    """Extract first JSON object or array from text."""
    # Try to find a JSON block in markdown code fences
    m = re.search(r"```(?:json)?\s*([\[{].*?)\s*```", text, re.DOTALL)
    if m:
        return m.group(1)
    # Otherwise find first { or [
    for i, ch in enumerate(text):
        if ch in ("{", "["):
            return text[i:]
    return text


async def complete_json(
    prompt: str,
    system: str,
    schema_hint: str,
    max_tokens: int = 4000,
) -> tuple[dict | list, int, int, float]:
    """Returns (parsed_json, input_tokens, output_tokens, cost_usd)."""
    text, inp, out, cost = await complete(prompt, system=system, max_tokens=max_tokens)

    try:
        return json.loads(_extract_json(text)), inp, out, cost
    except json.JSONDecodeError:
        pass

    # One repair attempt
    repair_prompt = (
        f"The following output was not valid JSON. Fix it to match this schema:\n{schema_hint}\n\n"
        f"Broken output:\n{text}\n\n"
        "Return ONLY the corrected JSON, nothing else."
    )
    text2, inp2, out2, cost2 = await complete(repair_prompt, max_tokens=max_tokens)
    try:
        return json.loads(_extract_json(text2)), inp + inp2, out + out2, cost + cost2
    except json.JSONDecodeError as exc:
        raise ValueError(f"JSON repair failed: {exc}\nText: {text2[:500]}") from exc
