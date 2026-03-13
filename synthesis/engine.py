from __future__ import annotations

import json
from datetime import datetime
from typing import Callable, List, Optional

from pydantic_ai import Agent

import os

from synthesis.client import LLMConfig, build_model
from synthesis.fallback import extractive_fallback
from synthesis.models import Brief, BriefLite, Citation
from synthesis.prompts import SYSTEM_PROMPT, user_prompt


LLMCall = Callable[[str, str], str]


def _extract_json_block(raw: str) -> Optional[str]:
    if not raw:
        return None
    start = raw.find("{")
    end = raw.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None
    return raw[start : end + 1]


def _default_llm_call(prompt: str, tier: str, config: LLMConfig) -> str:
    model = build_model(tier, config)
    no_tools = os.getenv("LLM_NO_TOOLS", "0") == "1"
    fast_compact = os.getenv("LLM_FAST_COMPACT", "1") == "1"

    def run_with_tools() -> str:
        if tier == "fast":
            output_type = BriefLite if fast_compact else Brief
        else:
            output_type = Brief
        agent = Agent(model=model, output_type=output_type, system_prompt=SYSTEM_PROMPT)
        result = agent.run_sync(prompt)
        return result.output.model_dump_json()

    def run_no_tools() -> str:
        agent = Agent(model=model, output_type=str, system_prompt=SYSTEM_PROMPT)
        result = agent.run_sync(prompt)
        return result.output

    if no_tools:
        return run_no_tools()

    try:
        return run_with_tools()
    except Exception as exc:
        message = str(exc)
        if "does not support tools" in message or "not support tools" in message:
            return run_no_tools()
        raise


def generate_brief(
    query: str,
    lens: str,
    context: str,
    citations: List[Citation],
    tier: str = "fast",
    llm_call: Optional[LLMCall] = None,
    config: Optional[LLMConfig] = None,
) -> Brief:
    cfg = config or LLMConfig()
    prompt = user_prompt(query=query, lens=lens, context=context, tier=tier)

    try:
        if llm_call:
            raw = llm_call(prompt, tier)
        else:
            raw = _default_llm_call(prompt, tier, cfg)
        fast_compact = os.getenv("LLM_FAST_COMPACT", "1") == "1"

        def parse_or_raise(payload: str) -> Brief | BriefLite:
            if tier == "fast" and fast_compact:
                return BriefLite.model_validate_json(payload)
            return Brief.model_validate_json(payload)

        try:
            brief = parse_or_raise(raw)
        except Exception:
            extracted = _extract_json_block(raw) if isinstance(raw, str) else None
            if extracted:
                brief = parse_or_raise(extracted)
            else:
                raise
        if not brief.citations:
            brief.citations = citations
        if not brief.created_at:
            brief.created_at = datetime.utcnow()
        return brief
    except Exception:
        return extractive_fallback(
            query=query, lens=lens, citations=citations, context=context
        )
