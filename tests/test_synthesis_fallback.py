from mtrd.agents.engine import generate_brief


def test_fallback_on_exception(sample_context, sample_citations):
    def failing_llm(prompt: str, tier: str) -> str:
        raise RuntimeError("LLM failed")

    brief = generate_brief(
        query="Fallback test",
        lens="risk",
        context=sample_context,
        citations=sample_citations,
        tier="fast",
        llm_call=failing_llm,
    )

    assert brief.tier == "fallback"
    assert "Manual" in brief.judgment
    assert len(brief.citations) == len(sample_citations)
