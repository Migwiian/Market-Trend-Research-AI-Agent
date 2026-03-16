from __future__ import annotations

from typing import Iterable, List

from llama_index.core import Document

from mtrd.ingest.sources import RawDocument
from storage.models import SourceSnapshot


def to_llama_documents(docs: Iterable[RawDocument]) -> List[Document]:
    out: List[Document] = []
    for doc in docs:
        out.append(Document(text=doc.text, metadata=doc.meta.model_dump()))
    return out


def snapshots_to_llama_documents(snapshots: Iterable[SourceSnapshot]) -> List[Document]:
    out: List[Document] = []
    for snap in snapshots:
        meta = dict(snap.metadata or {})
        meta.setdefault("source_id", snap.snapshot_id)
        meta.setdefault("title", meta.get("title", snap.snapshot_id))
        meta.setdefault("url", snap.url)
        meta.setdefault("source_type", snap.source_type)
        meta.setdefault("content_hash", snap.content_hash)
        meta.setdefault("tier", "unverified")
        meta.setdefault("collected_at", snap.retrieved_at.isoformat())
        if "published_at" in meta and hasattr(meta["published_at"], "isoformat"):
            meta["published_at"] = meta["published_at"].isoformat()

        out.append(
            Document(
                text=snap.content_text,
                metadata=meta,
                id_=snap.snapshot_id,
            )
        )
    return out
