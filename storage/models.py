from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Optional


@dataclass
class SourceSnapshot:
    snapshot_id: str
    content_hash: str
    content_text: str
    metadata: Dict[str, Any]
    retrieved_at: datetime
    source_type: str
    url: Optional[str]
    stale_after_days: int = 30

    @staticmethod
    def now_utc() -> datetime:
        return datetime.now(timezone.utc)
