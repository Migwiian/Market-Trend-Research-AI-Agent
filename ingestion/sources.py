from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

from storage.models import SourceSnapshot


@dataclass
class RawSource:
    text: str
    metadata: Dict[str, str]
    source_type: str
    url: Optional[str] = None
    stale_after_days: int = 30


def _hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def load_text_file(path: Path) -> RawSource:
    text = path.read_text(encoding="utf-8", errors="ignore").strip()
    return RawSource(
        text=text,
        metadata={"title": path.stem, "path": str(path)},
        source_type="file",
        url=str(path),
    )


def load_pdf_file(path: Path) -> RawSource:
    try:
        from pypdf import PdfReader
    except Exception as exc:
        raise RuntimeError("Install pypdf for PDF support") from exc

    try:
        reader = PdfReader(str(path))
        text = "\n".join(page.extract_text() or "" for page in reader.pages)
    except Exception as exc:
        raise RuntimeError(f"PDF read failed: {path}") from exc
    text = text.strip()
    return RawSource(
        text=text,
        metadata={"title": path.stem, "path": str(path)},
        source_type="file",
        url=str(path),
    )


def ingest_files(root: Path) -> List[RawSource]:
    sources: List[RawSource] = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        suffix = path.suffix.lower()
        if suffix in {".txt", ".md"}:
            sources.append(load_text_file(path))
        elif suffix == ".pdf":
            sources.append(load_pdf_file(path))
    return sources


def to_snapshot(raw: RawSource) -> SourceSnapshot:
    content_hash = _hash_text(raw.text)
    snapshot_id = f"{raw.source_type}:{content_hash[:12]}"
    return SourceSnapshot(
        snapshot_id=snapshot_id,
        content_hash=content_hash,
        content_text=raw.text,
        metadata=raw.metadata,
        retrieved_at=_now_utc(),
        source_type=raw.source_type,
        url=raw.url,
        stale_after_days=raw.stale_after_days,
    )
