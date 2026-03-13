from __future__ import annotations

import json
from datetime import datetime
from typing import List, Optional

from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIChatModel

from mtrd.config import AppConfig
from mtrd.lenses import get_lens_definition
from mtrd.models import BriefSection, EvidenceItem, MarketBrief, SourceMeta
from mtrd.rag.index import load_index


def _build_context(nodes, max_chars: int) -> str:
    chunks = []
    total = 0
    for idx, node in enumerate(nodes, start=1):
        meta = node.metadata or {}
        title = meta.get("title", "Untitled")
        url = meta.get("url", "")
        snippet = node.get_text()
        block = f"[Source {idx}] {title} {url}\n{snippet}\n"
        if total + len(block) > max_chars:
            remaining = max_chars - total
            if remaining <= 0:
                break
            block = block[:remaining]
        chunks.append(block)
        total += len(block)
        if total >= max_chars:
            break
    return "\n".join(chunks).strip()


def _sources_from_nodes(nodes) -> List[SourceMeta]:
    sources: List[SourceMeta] = []
    for node in nodes:
        meta = node.metadata or {}
        try:
            sources.append(SourceMeta(**meta))
        except Exception:
            continue
    return sources


def _extract_json_block(raw: str) -> Optional[str]:
    if not raw:
        return None
    start = raw.find("{")
    end = raw.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None
    return raw[start : end + 1]


def _extractive_fallback(
    topic: str, audience: str, lens: str, sources: List[SourceMeta], context: str
) -> MarketBrief:
    now = datetime.utcnow()
    lines = [line.strip() for line in context.splitlines() if line.strip()]
    quotes = []
    for line in lines:
        if len(quotes) >= 3:
            break
        if len(line) > 20:
            quotes.append(line[:240])
    signals: List[EvidenceItem] = []
    for idx, quote in enumerate(quotes):
        source_id = sources[idx].source_id if idx < len(sources) else "none"
        signals.append(
            EvidenceItem(
                claim="Extracted evidence (fallback mode)",
                source_ids=[source_id],
                confidence=0.1,
            )
        )
    if not signals:
        signals = [
            EvidenceItem(
                claim="No evidence extracted (fallback mode)",
                source_ids=[sources[0].source_id] if sources else ["none"],
                confidence=0.0,
            )
        ]
    sections = [
        BriefSection(
            heading="Top Evidence",
            bullets=quotes or ["No sources available"],
        )
    ]
    return MarketBrief(
        topic=topic,
        audience=audience,
        lens=lens,
        generated_at=now,
        executive_summary=["Evidence unavailable for synthesis; see top sources below."],
        sections=sections,
        key_risks=[],
        key_opportunities=[],
        signals=signals,
        assumptions=["Extractive fallback used; manual review required."],
        citations=sources,
        decision_summary="Manual completion required.",
    )


def generate_brief(topic: str, audience: str, lens: str, config: AppConfig) -> MarketBrief:
    index = load_index(config)
    retriever = index.as_retriever(similarity_top_k=config.top_k)
    nodes = retriever.retrieve(topic)

    context = _build_context(nodes, max_chars=config.context_max_chars)
    sources = _sources_from_nodes(nodes)

    lens_def = get_lens_definition(lens)
    model = OpenAIChatModel(
        model_name="local",
        base_url=config.llm.openai_base_url,
        api_key=config.llm.openai_api_key,
        provider="openai-chat",
        settings={
            "timeout": config.llm.timeout,
            "max_tokens": config.llm.max_tokens,
            "temperature": config.llm.temperature,
        },
    )

    system_prompt = (
        "You are an evidence-first market research analyst. "
        "Only use the provided sources. If evidence is missing, state it as an assumption. "
        "Return JSON only. Do not include any extra text."
    )

    user_prompt = {
        "task": "Produce a market brief with citations and clear assumptions.",
        "topic": topic,
        "audience": audience,
        "lens": lens,
        "lens_definition": lens_def,
        "context": context,
        "now": datetime.utcnow().isoformat(),
    }

    if config.extractive_only:
        return _extractive_fallback(topic, audience, lens, sources, context)

    try:
        if config.llm.no_tools:
            agent = Agent(model=model, output_type=str, system_prompt=system_prompt)
            raw = agent.run_sync(json.dumps(user_prompt)).output
            try:
                brief = MarketBrief.model_validate_json(raw)
            except Exception:
                extracted = _extract_json_block(raw)
                if not extracted:
                    raise
                brief = MarketBrief.model_validate_json(extracted)
        else:
            agent = Agent(model=model, output_type=MarketBrief, system_prompt=system_prompt)
            brief = agent.run_sync(json.dumps(user_prompt)).output
        brief.citations = sources
        return brief
    except Exception:
        return _extractive_fallback(topic, audience, lens, sources, context)
