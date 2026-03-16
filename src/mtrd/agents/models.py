from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field, conlist


class Citation(BaseModel):
    source_id: str
    title: str
    url: Optional[str] = None
    retrieved_at: datetime
    stale_after_days: int = 30


class EvidenceItem(BaseModel):
    claim: str
    quote: str
    source_id: str
    confidence: float = Field(ge=0.0, le=1.0)


class BriefSection(BaseModel):
    heading: str
    bullets: List[str]


class Brief(BaseModel):
    query: str
    lens: str
    tier: str
    created_at: datetime
    executive_summary: List[str]
    evidence: List[EvidenceItem]
    assumptions: List[str]
    judgment: str
    sections: List[BriefSection]
    citations: List[Citation]


class BriefLite(BaseModel):
    query: str
    lens: str
    tier: str
    created_at: datetime
    executive_summary: conlist(str, min_length=1, max_length=3)
    evidence: conlist(EvidenceItem, min_length=1, max_length=2)
    judgment: str
    citations: conlist(Citation, min_length=1, max_length=3)
