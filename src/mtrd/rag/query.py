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


def _extract_top_evidence(context: str, max_items: int = 3) -> List[str]:
    lines = [line.strip() for line in context.splitlines() if line.strip()]
    quotes: List[str] = []
    for line in lines:
        if len(quotes) >= max_items:
            break
        if len(line) > 20:
            quotes.append(line[:240])
    return quotes


def _staleness_days(meta: SourceMeta) -> int | None:
    if not meta:
        return None
    base = meta.published_at or meta.collected_at
    if not base:
        return None
    delta = datetime.utcnow() - base.replace(tzinfo=None)
    return max(0, delta.days)


def _enforce_brief_constraints(
    brief: MarketBrief,
    topic: str,
    audience: str,
    lens: str,
    sources: List[SourceMeta],
    context: str,
) -> MarketBrief:
    brief.topic = brief.topic or topic
    brief.audience = brief.audience or audience
    brief.lens = brief.lens or lens

    if not brief.executive_summary:
        brief.executive_summary = ["Evidence-first brief generated from available sources."]
    if len(brief.executive_summary) > 3:
        brief.executive_summary = brief.executive_summary[:3]

    if not brief.sections:
        brief.sections = [
            BriefSection(
                heading="Top Evidence",
                bullets=_extract_top_evidence(context) or ["No sources available"],
            )
        ]
    else:
        has_top = any(sec.heading.strip().lower() == "top evidence" for sec in brief.sections)
        if not has_top:
            brief.sections.append(
                BriefSection(
                    heading="Top Evidence",
                    bullets=_extract_top_evidence(context) or ["No sources available"],
                )
            )

    source_map = {s.source_id: s for s in sources}
    if not brief.signals:
        if sources:
            brief.signals = [
                EvidenceItem(
                    claim="Extracted evidence (fallback mode)",
                    source_ids=[sources[0].source_id],
                    confidence=0.1,
                    staleness_days=_staleness_days(sources[0]),
                )
            ]
        else:
            brief.signals = [
                EvidenceItem(
                    claim="No evidence extracted (fallback mode)",
                    source_ids=["none"],
                    confidence=0.0,
                    staleness_days=None,
                )
            ]
    else:
        for sig in brief.signals:
            if sig.staleness_days is None and sig.source_ids:
                meta = source_map.get(sig.source_ids[0])
                if meta:
                    sig.staleness_days = _staleness_days(meta)

    if not brief.citations:
        brief.citations = sources

    if not brief.assumptions:
        brief.assumptions = ["No explicit assumptions provided; verify sources."]

    if not brief.decision_summary:
        brief.decision_summary = "Manual completion required."

    return brief


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
        staleness = _staleness_days(sources[idx]) if idx < len(sources) else None
        signals.append(
            EvidenceItem(
                claim="Extracted evidence (fallback mode)",
                source_ids=[source_id],
                confidence=0.1,
                staleness_days=staleness,
            )
        )
    if not signals:
        signals = [
            EvidenceItem(
                claim="No evidence extracted (fallback mode)",
                source_ids=[sources[0].source_id] if sources else ["none"],
                confidence=0.0,
                staleness_days=_staleness_days(sources[0]) if sources else None,
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


def generate_brief(
    topic: str,
    audience: str,
    lens: str,
    config: AppConfig,
    tier: str | None = None,
) -> MarketBrief:
    index = load_index(config)
    retriever = index.as_retriever(similarity_top_k=config.top_k)
    nodes = retriever.retrieve(topic)

    context = _build_context(nodes, max_chars=config.context_max_chars)
    sources = _sources_from_nodes(nodes)

    lens_def = get_lens_definition(lens)
    selected_tier = (tier or config.llm.default_tier or "fast").lower()
    model_name = config.llm.fast_model if selected_tier == "fast" else config.llm.standard_model
    model = OpenAIChatModel(
        model_name=model_name,
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
        brief = _extractive_fallback(topic, audience, lens, sources, context)
        return _enforce_brief_constraints(brief, topic, audience, lens, sources, context)

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
        return _enforce_brief_constraints(brief, topic, audience, lens, sources, context)
    except Exception:
        brief = _extractive_fallback(topic, audience, lens, sources, context)
        return _enforce_brief_constraints(brief, topic, audience, lens, sources, context)
