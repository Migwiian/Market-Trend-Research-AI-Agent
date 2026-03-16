from __future__ import annotations

from datetime import datetime

import pytest

from mtrd.agents.models import Citation


@pytest.fixture()
def sample_citations():
    return [
        Citation(
            source_id="src-1",
            title="FakeCo Case Study",
            url="https://example.com/case-study",
            retrieved_at=datetime.utcnow(),
            stale_after_days=30,
        ),
        Citation(
            source_id="src-2",
            title="Industry Report",
            url="https://example.com/report",
            retrieved_at=datetime.utcnow(),
            stale_after_days=30,
        ),
    ]


@pytest.fixture()
def sample_context():
    return (
        "[Source 1] FakeCo Case Study\n"
        "Deployed in 14 days for a mid-market client with 2,000 seats. "
        "Implementation included SSO, audit logging, and role-based controls. "
        "Customer cited faster onboarding as the primary reason for switching. "
        "Pricing was discounted for a three-year commitment.\n"
        "\n"
        "[Source 2] Industry Report\n"
        "Analyst note: FakeCo accelerated mid-market adoption in Q1, but enterprise "
        "procurement cycles remained flat. Competitive pricing pressure increased "
        "in regulated industries, with buyers requesting stronger compliance evidence. "
        "Report mentions gaps in advanced governance features.\n"
        "\n"
        "[Source 3] Customer Call Notes\n"
        "Two customers reported that FakeCo onboarding was fast but required manual "
        "workarounds for integrations. Security documentation was described as "
        "\"good enough\" for mid-market, but not sufficient for enterprise risk review. "
        "Support response times were inconsistent.\n"
        "\n"
        "[Source 4] Pricing Page Snapshot\n"
        "Public pricing lists per-seat tiers with enterprise negotiations. "
        "A new \"launch\" tier appears to target mid-market buyers with quicker time "
        "to value. Pricing stability is uncertain due to recent discounts.\n"
    )
