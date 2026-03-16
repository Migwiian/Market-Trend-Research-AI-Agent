from __future__ import annotations

LENS_DEFINITIONS = {
    "growth": "Emphasize expansion signals, demand growth, and positioning opportunities.",
    "risk": "Emphasize threats, downside scenarios, and uncertainty signals.",
}

SYSTEM_PROMPT = (
    "You are an evidence-first market research analyst. "
    "Only use the provided context. "
    "If evidence is missing, state it as an assumption. "
    "Be concise and avoid filler. "
    "Return JSON that matches the provided schema exactly."
)


def user_prompt(query: str, lens: str, context: str, tier: str = "fast") -> str:
    lens_def = LENS_DEFINITIONS.get(lens, "")
    compact_note = ""
    if tier == "fast":
        compact_note = (
            "Brief-Lite output constraints (fast tier): "
            "Return only fields in this schema: "
            "query, lens, tier, created_at, executive_summary (max 3), "
            "evidence (max 2), assumptions (max 3), judgment, citations. "
        )
    return (
        f"Task: Produce a structured market brief.\n"
        f"Query: {query}\n"
        f"Lens: {lens} ({lens_def})\n"
        f"{compact_note}"
        "Context:\n"
        f"{context}\n"
        "Return JSON only."
    )
