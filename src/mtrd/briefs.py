from __future__ import annotations

from mtrd.models import MarketBrief


def brief_to_markdown(brief: MarketBrief) -> str:
    lines = [f"# {brief.topic}", ""]
    lines.append(f"Audience: {brief.audience}")
    lines.append(f"Lens: {brief.lens}")
    lines.append("")
    lines.append("## Executive Summary")
    for item in brief.executive_summary:
        lines.append(f"- {item}")
    lines.append("")
    for section in brief.sections:
        lines.append(f"## {section.heading}")
        for bullet in section.bullets:
            lines.append(f"- {bullet}")
        lines.append("")
    lines.append("## Key Risks")
    for item in brief.key_risks:
        lines.append(f"- {item}")
    lines.append("")
    lines.append("## Key Opportunities")
    for item in brief.key_opportunities:
        lines.append(f"- {item}")
    lines.append("")
    lines.append("## Signals")
    for sig in brief.signals:
        staleness = ""
        if sig.staleness_days is not None:
            staleness = f", staleness {sig.staleness_days}d"
        lines.append(f"- {sig.claim} (confidence {sig.confidence}{staleness})")
    lines.append("")
    lines.append("## Assumptions")
    for item in brief.assumptions:
        lines.append(f"- {item}")
    lines.append("")
    lines.append("## Decision Summary")
    lines.append(brief.decision_summary)
    lines.append("")
    lines.append("## Citations")
    for cite in brief.citations:
        lines.append(f"- {cite.title} | {cite.url}")
    return "\n".join(lines)
