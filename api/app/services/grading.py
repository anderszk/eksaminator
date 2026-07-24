"""Grading: content via LLM, delivery in code. See spec §8.8."""
import json
import logging

from app.services import llm

logger = logging.getLogger(__name__)

FILLERS_NO = {
    "eh", "øh", "ehm", "liksom", "altså", "på en måte", "ikke sant",
    "sånn", "da", "jo", "vel", "egentlig",
}
SOFT_FILLERS = {"altså", "da", "jo", "vel", "egentlig"}


async def grade_turn_content(
    question: dict,
    transcript: str,
    rubric: dict,
    model_answer: str,
    source_chunks: list[str],
) -> dict:
    prompt_template = llm.load_prompt("grade_turn.md")
    prompt = prompt_template.replace("{{question}}", question.get("text", ""))
    prompt = prompt.replace("{{why_asked}}", question.get("why_asked", ""))
    prompt = prompt.replace("{{rubric}}", json.dumps(rubric, ensure_ascii=False))
    prompt = prompt.replace("{{model_answer}}", model_answer or "")
    prompt = prompt.replace("{{transcript}}", transcript)
    prompt = prompt.replace("{{source_chunks}}", "\n\n---\n\n".join(source_chunks))

    schema = """{
  "korrekthet": 0-4,
  "begrunnelse": 0-4,
  "forbehold": 0-4,
  "struktur": 0-4,
  "bluffed": true|false,
  "used_shape": "direkte|utfordre|innrommelse|uklar",
  "missed_points": ["..."],
  "feedback_md": "3-5 sentences Norwegian"
}"""
    result, _, _, _ = await llm.complete_json(
        prompt,
        system="You are an expert academic examiner grading spoken defence answers.",
        schema_hint=schema,
        max_tokens=1500,
    )
    return result


def combine_grades(delivery: dict, content: dict) -> dict:
    return {
        **delivery,
        "scores": {
            "korrekthet": content.get("korrekthet", 0),
            "begrunnelse": content.get("begrunnelse", 0),
            "forbehold": content.get("forbehold", 0),
            "struktur": content.get("struktur", 0),
        },
        "bluffed": content.get("bluffed", False),
        "used_shape": content.get("used_shape", "uklar"),
        "missed_points": content.get("missed_points", []),
        "feedback_md": content.get("feedback_md", ""),
    }
