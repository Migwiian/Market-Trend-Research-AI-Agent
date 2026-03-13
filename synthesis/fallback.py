from __future__ import annotations

from datetime import datetime
from typing import List

import re

from synthesis.models import Brief, BriefLite, BriefSection, Citation, EvidenceItem


def _extract_quotes(context: str, max_items: int = 2) -> list[str]:
    if not context:
        return []
    # Split on source markers; take first sentence/fragment from each block.
    blocks = re.split(r"\\[Source \\d+\\]", context)
    quotes: list[str] = []
    for block in blocks:
        block = block.strip()
        if not block:
            continue
        sentence = block.split(".")[0].strip()
        if sentence:
            quotes.append(sentence)
        if len(quotes) >= max_items:
            break
    return quotes


def fallback_brief(
    query: str,
    lens: str,
    citations: List[Citation],
    context: str | None = None,
    lite: bool = True,
) -> Brief | BriefLite:
    now = datetime.utcnow()
    quotes = _extract_quotes(context or "", max_items=2)
    evidence_items = [
        EvidenceItem(
            claim="Extracted evidence snippet",
            quote=quote,
            source_id=citations[i].source_id if i < len(citations) else "none",
            confidence=0.2,
        )
        for i, quote in enumerate(quotes)
    ]
    if not evidence_items:
        evidence_items = [
            EvidenceItem(
                claim="No extracted evidence available",
                quote="",
                source_id=citations[0].source_id if citations else "none",
                confidence=0.0,
            )
        ]
    summary = [
        "Automated synthesis failed; returning outline with citations.",
        "Review evidence and complete judgment manually.",
    ]
    if lite:
        return BriefLite(
            query=query,
            lens=lens,
            tier="fallback",
            created_at=now,
            executive_summary=summary[:2],
            evidence=evidence_items[:2],
            judgment="Manual completion required.",
            citations=citations[:3],
        )

    sections = [
        BriefSection(
            heading="Evidence Outline",
            bullets=[f"Source: {c.title}" for c in citations] or ["No sources available"],
        )
    ]
    return Brief(
        query=query,
        lens=lens,
        tier="fallback",
        created_at=now,
        executive_summary=summary,
        evidence=evidence_items,
        assumptions=["Synthesis failed; manual review required."],
        judgment="Manual completion required.",
        sections=sections,
        citations=citations,
    )


def extractive_fallback(
    query: str, lens: str, citations: List[Citation], context: str
) -> Brief:
    now = datetime.utcnow()
    lines = [line.strip() for line in context.splitlines() if line.strip()]
    quotes = []
    for line in lines:
        if len(quotes) >= 3:
            break
        if len(line) > 20:
            quotes.append(line[:240])
    evidence_items: List[EvidenceItem] = []
    for idx, quote in enumerate(quotes):
        source_id = citations[idx].source_id if idx < len(citations) else "none"
        evidence_items.append(
            EvidenceItem(
                claim="Extracted evidence (fallback mode)",
                quote=quote,
                source_id=source_id,
                confidence=0.1,
            )
        )
    if not evidence_items:
        evidence_items = [
            EvidenceItem(
                claim="No evidence extracted (fallback mode)",
                quote="",
                source_id=citations[0].source_id if citations else "none",
                confidence=0.0,
            )
        ]
    sections = [
        BriefSection(
            heading="Top Evidence",
            bullets=[item.quote for item in evidence_items if item.quote]
            or ["No sources available"],
        )
    ]
    return Brief(
        query=query,
        lens=lens,
        tier="fallback",
        created_at=now,
        executive_summary=[
            "Evidence unavailable for synthesis; see top sources below."
        ],
        evidence=evidence_items,
        assumptions=["Extractive fallback used; manual review required."],
        judgment="Manual completion required.",
        sections=sections,
        citations=citations,
    )
