from collections.abc import Generator
from datetime import UTC, datetime

from palimpsest.llm import LLM

PROMPTS = {
    "modified": """You are analyzing a change to an SEC filing's {label} section.

PREVIOUS VERSION:
{from_text}

CURRENT VERSION:
{to_text}

In one sentence, state what substantively changed. If only figures, dates or period wording were updated, answer exactly "routine update". Do not speculate about motives.""",
    "added": """You are analyzing an SEC filing's {label} section.

The following paragraph is new in this filing and did not appear in the previous one:

{to_text}

In one sentence, state what this newly disclosed paragraph says. Do not speculate about motives.""",
    "removed": """You are analyzing an SEC filing's {label} section.

The following paragraph appeared in the previous filing and has been removed:

{from_text}

In one sentence, state what disclosure was dropped. Do not speculate about why.""",
}


def summarize_label_changes(llm_client: LLM, changes: list[tuple]) -> Generator[tuple]:
    for text_hash, label, change_type, from_text, to_text in changes:
        template = PROMPTS.get(change_type)
        if template is None:
            continue
        prompt = template.format(label=label, from_text=from_text, to_text=to_text)
        completion = llm_client.complete(prompt)
        yield (text_hash, completion.text, completion.model, datetime.now(tz=UTC))
