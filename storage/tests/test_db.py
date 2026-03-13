from pathlib import Path

from storage.db import connect, init_db, upsert_snapshot, get_snapshot
from storage.models import SourceSnapshot


def test_upsert_and_get_snapshot(tmp_path: Path):
    db_path = tmp_path / "snapshots.db"
    conn = connect(db_path)
    init_db(conn)

    snap = SourceSnapshot(
        snapshot_id="file:abc123",
        content_hash="deadbeef",
        content_text="hello world",
        metadata={"title": "Test"},
        retrieved_at=SourceSnapshot.now_utc(),
        source_type="file",
        url="/tmp/test.txt",
        stale_after_days=30,
    )

    upsert_snapshot(conn, snap)
    loaded = get_snapshot(conn, "file:abc123")

    assert loaded is not None
    assert loaded.snapshot_id == snap.snapshot_id
    assert loaded.content_text == "hello world"
