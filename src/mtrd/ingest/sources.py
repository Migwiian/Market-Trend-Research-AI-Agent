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
        text = path.read_text(encoding="utf-8", errors="ignore")
    elif path.suffix.lower() == ".pdf":
        try:
            from pypdf import PdfReader

            reader = PdfReader(str(path))
            text = "\n".join(page.extract_text() or "" for page in reader.pages)
        except Exception as exc:
            raise RuntimeError(f"PDF read failed: {path}") from exc
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
        resp = requests.get(url, timeout=20)
        resp.raise_for_status()
        html = resp.text
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
