from __future__ import annotations

from datetime import datetime, timezone

from mtrd.storage.db import connect, init_db, upsert_snapshot
from mtrd.storage.models import SourceSnapshot


def _make_snapshot(snapshot_id: str, text: str) -> SourceSnapshot:
    now = datetime.now(timezone.utc)
    return SourceSnapshot(
        snapshot_id=snapshot_id,
        content_hash=f"hash-{snapshot_id}",
        content_text=text,
        metadata={
            "source_id": snapshot_id,
            "title": f"Title {snapshot_id}",
            "url": f"https://example.com/{snapshot_id}",
            "source_type": "file",
            "collected_at": now.isoformat(),
            "content_hash": f"hash-{snapshot_id}",
            "tier": "unverified",
        },
        retrieved_at=now,
        source_type="file",
        url=f"https://example.com/{snapshot_id}",
        stale_after_days=30,
    )


def test_build_index_and_retrieve(tmp_path):
    from mtrd.config import AppConfig, EmbeddingConfig
    from mtrd.rag.index import build_index_from_db, load_index

    db_path = tmp_path / "snapshots.db"
    conn = connect(db_path)
    init_db(conn)

    upsert_snapshot(conn, _make_snapshot("file:one", "Growth in mid-market demand."))
    upsert_snapshot(conn, _make_snapshot("file:two", "Regulatory risk increases in EU."))

    config = AppConfig(embeddings=EmbeddingConfig(backend="mock"))
    chroma_dir = tmp_path / "chroma"
    build_index_from_db(db_path, config, persist_dir=chroma_dir, rebuild=True)

    index = load_index(config, persist_dir=chroma_dir)
    retriever = index.as_retriever(similarity_top_k=2)
    nodes = retriever.retrieve("mid-market demand")

    assert len(nodes) >= 1
    meta = nodes[0].metadata or {}
    assert "title" in meta
