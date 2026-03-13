import json
import os
import time
from datetime import datetime

import pytest
from pydantic_ai import Agent

from synthesis.client import LLMConfig, build_model
from synthesis.engine import generate_brief
from synthesis.models import Brief
from synthesis.prompts import SYSTEM_PROMPT, user_prompt


def test_generate_brief_with_stub(sample_context, sample_citations):
    def stub_llm(prompt: str, tier: str) -> str:
        payload = {
            "query": "Competitive positioning of FakeCo",
            "lens": "growth",
            "tier": tier,
            "created_at": datetime.utcnow().isoformat(),
            "executive_summary": ["FakeCo is fast in mid-market."],
            "evidence": [
                {
                    "claim": "FakeCo deploys in 14 days",
                    "quote": "Deployed in 14 days",
                    "source_id": "src-1",
                    "confidence": 0.8,
                }
            ],
            "assumptions": ["Case studies are representative"],
            "judgment": "Maintain enterprise focus.",
            "sections": [
                {"heading": "Positioning", "bullets": ["Speed advantage"]}
            ],
            "citations": [
                {
                    "source_id": "src-1",
                    "title": "FakeCo Case Study",
                    "url": "https://example.com/case-study",
                    "retrieved_at": datetime.utcnow().isoformat(),
                    "stale_after_days": 30,
                }
            ],
        }
        return json.dumps(payload)

    brief = generate_brief(
        query="Competitive positioning of FakeCo",
        lens="growth",
        context=sample_context,
        citations=sample_citations,
        tier="fast",
        llm_call=stub_llm,
    )

    assert brief.query.startswith("Competitive")
    assert brief.tier == "fast"
    assert len(brief.executive_summary) >= 1
    assert brief.evidence[0].confidence == 0.8


@pytest.mark.integration
def test_generate_brief_end_to_end_timing(sample_context, sample_citations):
    if os.getenv("RUN_LLM", "0") != "1":
        pytest.skip("Set RUN_LLM=1 to run end-to-end timing test with local LLM.")

    cfg = LLMConfig()
    prompt = user_prompt(
        query="Competitive positioning of FakeCo",
        lens="growth",
        context=sample_context,
        tier="fast",
    )

    model_time = None
    model_error = None

    def timed_llm_call(prompt_text: str, tier: str) -> str:
        nonlocal model_time, model_error
        start = time.perf_counter()
        try:
            model = build_model(tier, cfg)
            no_tools = os.getenv("LLM_NO_TOOLS", "0") == "1"

            def run_with_tools() -> str:
                agent = Agent(model=model, output_type=Brief, system_prompt=SYSTEM_PROMPT)
                result = agent.run_sync(prompt_text)
                return result.output.model_dump_json()

            def run_no_tools() -> str:
                agent = Agent(model=model, output_type=str, system_prompt=SYSTEM_PROMPT)
                result = agent.run_sync(prompt_text)
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
        except Exception as exc:  # capture validation or transport errors
            model_error = f"{type(exc).__name__}: {exc}"
            raise
        finally:
            model_time = time.perf_counter() - start

    start_total = time.perf_counter()
    brief = generate_brief(
        query="Competitive positioning of FakeCo",
        lens="growth",
        context=sample_context,
        citations=sample_citations,
        tier="fast",
        llm_call=timed_llm_call,
        config=cfg,
    )
    total_time = time.perf_counter() - start_total

    if model_time is not None:
        print(f"MODEL_TIME_SEC={model_time:.2f}")
    else:
        print("MODEL_TIME_SEC=NA")
    if model_error:
        print(f"MODEL_ERROR={model_error}")
    if brief.tier == "fallback":
        print("FALLBACK_USED=1")
    print(f"TOTAL_TIME_SEC={total_time:.2f}")

    budget = float(os.getenv("MTRD_FAST_BUDGET", "60"))
    if os.getenv("ENFORCE_TIME", "0") == "1":
        assert total_time < budget

    assert brief.tier in {"fast", "fallback"}
