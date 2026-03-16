from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable, List, Optional

import requests
import feedparser
from bs4 import BeautifulSoup

from mtrd.models import SourceMeta
from mtrd.exceptions import IngestError
from storage.models import SourceSnapshot


@dataclass
class RawDocument:
    text: str
    meta: SourceMeta


def _hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _now() -> datetime:
    return datetime.utcnow()


def _clean_text(text: str) -> str:
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def load_file(path: Path, source_type: str = "file") -> RawDocument:
    text = ""
    if path.suffix.lower() in {".txt", ".md"}:
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except (FileNotFoundError, PermissionError) as exc:
            raise IngestError(f"System couldn't access source file: {path}") from exc
    elif path.suffix.lower() == ".pdf":
        try:
            from pypdf import PdfReader

            reader = PdfReader(str(path))
            text = "\n".join(page.extract_text() or "" for page in reader.pages)
        except (FileNotFoundError, PermissionError) as exc:
            raise IngestError(f"System couldn't access source file: {path}") from exc
        except Exception as exc:
            raise IngestError(f"PDF parsing failed unexpectedly: {path}") from exc
    else:
        raise ValueError(f"Unsupported file type: {path}")

    text = _clean_text(text)
    meta = SourceMeta(
        source_id=f"file:{path.name}",
        title=path.stem,
        url=str(path),
        source_type=source_type,
        collected_at=_now(),
        content_hash=_hash_text(text),
        tier="unverified",
    )
    return RawDocument(text=text, meta=meta)


def ingest_files(path: Path) -> List[RawDocument]:
    docs: List[RawDocument] = []
    for file_path in path.rglob("*"):
        if file_path.is_file() and file_path.suffix.lower() in {".txt", ".md", ".pdf"}:
            docs.append(load_file(file_path))
    return docs


def ingest_rss(feed_urls: Iterable[str]) -> List[RawDocument]:
    docs: List[RawDocument] = []
    for url in feed_urls:
        feed = feedparser.parse(url)
        for entry in feed.entries:
            text = _clean_text(entry.get("summary", ""))
            if not text:
                continue
            meta = SourceMeta(
                source_id=f"rss:{entry.get('id', entry.get('link', url))}",
                title=entry.get("title", "Untitled"),
                url=entry.get("link"),
                source_type="rss",
                collected_at=_now(),
                published_at=_parse_dt(entry.get("published")),
                content_hash=_hash_text(text),
                tier="unverified",
            )
            docs.append(RawDocument(text=text, meta=meta))
    return docs


def ingest_web(urls: Iterable[str]) -> List[RawDocument]:
    docs: List[RawDocument] = []
    for url in urls:
        try:
            resp = requests.get(url, timeout=20)
            resp.raise_for_status()
            html = resp.text
        except requests.RequestException as exc:
            raise IngestError(f"Web source fetch failed: {url}") from exc
        soup = BeautifulSoup(html, "html.parser")
        text = _clean_text(soup.get_text(" "))
        if not text:
            continue
        meta = SourceMeta(
            source_id=f"web:{url}",
            title=soup.title.string.strip() if soup.title and soup.title.string else url,
            url=url,
            source_type="web",
            collected_at=_now(),
            content_hash=_hash_text(text),
            tier="unverified",
        )
        docs.append(RawDocument(text=text, meta=meta))
    return docs


def _parse_dt(raw: Optional[str]) -> Optional[datetime]:
    if not raw:
        return None
    for fmt in ("%a, %d %b %Y %H:%M:%S %z", "%Y-%m-%d"):
        try:
            return datetime.strptime(raw, fmt)
        except Exception:
            continue
    return None


def to_snapshot(doc: RawDocument, stale_after_days: int = 30) -> SourceSnapshot:
    meta = doc.meta
    snapshot_id = f"{meta.source_type}:{meta.content_hash[:12]}"
    return SourceSnapshot(
        snapshot_id=snapshot_id,
        content_hash=meta.content_hash,
        content_text=doc.text,
        metadata=meta.model_dump(),
        retrieved_at=meta.collected_at,
        source_type=meta.source_type,
        url=meta.url,
        stale_after_days=stale_after_days,
        embedding_id=snapshot_id,
    )
