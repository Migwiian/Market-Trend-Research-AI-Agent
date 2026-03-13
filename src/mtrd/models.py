from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class SourceMeta(BaseModel):
    source_id: str
    title: str
    url: Optional[str] = None
    source_type: str
    collected_at: datetime
    published_at: Optional[datetime] = None
    content_hash: str
    tier: str = Field(default="unverified", description="verified | self-reported | unverified")


class EvidenceItem(BaseModel):
    claim: str
    source_ids: List[str]
    confidence: float = Field(ge=0.0, le=1.0)
    staleness_days: Optional[int] = None


class BriefSection(BaseModel):
    heading: str
    bullets: List[str]


class MarketBrief(BaseModel):
    topic: str
    audience: str
    lens: str
    generated_at: datetime
    executive_summary: List[str]
    sections: List[BriefSection]
    key_risks: List[str]
    key_opportunities: List[str]
    signals: List[EvidenceItem]
    assumptions: List[str]
    citations: List[SourceMeta]
    decision_summary: str
