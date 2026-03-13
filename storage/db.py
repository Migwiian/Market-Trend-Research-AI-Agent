from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Iterable, List, Optional

from storage.models import SourceSnapshot


def connect(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS snapshots (
            snapshot_id TEXT PRIMARY KEY,
            content_hash TEXT NOT NULL,
            content_text TEXT NOT NULL,
            metadata_json TEXT NOT NULL,
            retrieved_at TEXT NOT NULL,
            source_type TEXT NOT NULL,
            url TEXT,
            stale_after_days INTEGER NOT NULL
        );
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_snapshots_hash ON snapshots(content_hash);"
    )
    conn.commit()


def upsert_snapshot(conn: sqlite3.Connection, snap: SourceSnapshot) -> None:
    conn.execute(
        """
        INSERT INTO snapshots (
            snapshot_id, content_hash, content_text, metadata_json, retrieved_at,
            source_type, url, stale_after_days
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(snapshot_id) DO UPDATE SET
            content_hash=excluded.content_hash,
            content_text=excluded.content_text,
            metadata_json=excluded.metadata_json,
            retrieved_at=excluded.retrieved_at,
            source_type=excluded.source_type,
            url=excluded.url,
            stale_after_days=excluded.stale_after_days;
        """,
        (
            snap.snapshot_id,
            snap.content_hash,
            snap.content_text,
            json.dumps(snap.metadata),
            snap.retrieved_at.isoformat(),
            snap.source_type,
            snap.url,
            snap.stale_after_days,
        ),
    )
    conn.commit()


def get_snapshot(conn: sqlite3.Connection, snapshot_id: str) -> Optional[SourceSnapshot]:
    cur = conn.execute(
        "SELECT snapshot_id, content_hash, content_text, metadata_json, retrieved_at, source_type, url, stale_after_days "
        "FROM snapshots WHERE snapshot_id=?",
        (snapshot_id,),
    )
    row = cur.fetchone()
    if not row:
        return None
    return _row_to_snapshot(row)


def list_snapshots(conn: sqlite3.Connection, limit: int = 50) -> List[SourceSnapshot]:
    cur = conn.execute(
        "SELECT snapshot_id, content_hash, content_text, metadata_json, retrieved_at, source_type, url, stale_after_days "
        "FROM snapshots ORDER BY retrieved_at DESC LIMIT ?",
        (limit,),
    )
    return [_row_to_snapshot(row) for row in cur.fetchall()]


def _row_to_snapshot(row) -> SourceSnapshot:
    snapshot_id, content_hash, content_text, metadata_json, retrieved_at, source_type, url, stale_after_days = row
    return SourceSnapshot(
        snapshot_id=snapshot_id,
        content_hash=content_hash,
        content_text=content_text,
        metadata=json.loads(metadata_json),
        retrieved_at=SourceSnapshot.now_utc().fromisoformat(retrieved_at),
        source_type=source_type,
        url=url,
        stale_after_days=int(stale_after_days),
    )
