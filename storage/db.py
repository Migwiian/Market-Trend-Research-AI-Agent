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
            stale_after_days INTEGER NOT NULL,
            embedding_id TEXT
        );
        """
    )
    conn.execute("PRAGMA table_info(snapshots);")
    try:
        conn.execute("ALTER TABLE snapshots ADD COLUMN embedding_id TEXT;")
    except sqlite3.OperationalError:
        pass
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS briefs (
            brief_id TEXT PRIMARY KEY,
            topic TEXT NOT NULL,
            audience TEXT NOT NULL,
            lens TEXT NOT NULL,
            generated_at TEXT NOT NULL,
            version INTEGER NOT NULL,
            brief_json TEXT NOT NULL,
            citations_json TEXT NOT NULL
        );
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS audit_log (
            audit_id TEXT PRIMARY KEY,
            action TEXT NOT NULL,
            user TEXT,
            timestamp TEXT NOT NULL,
            details_json TEXT NOT NULL
        );
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_snapshots_hash ON snapshots(content_hash);"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_briefs_topic ON briefs(topic);"
    )
    conn.commit()


def upsert_snapshot(conn: sqlite3.Connection, snap: SourceSnapshot) -> None:
    conn.execute(
        """
        INSERT INTO snapshots (
            snapshot_id, content_hash, content_text, metadata_json, retrieved_at,
            source_type, url, stale_after_days, embedding_id
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(snapshot_id) DO UPDATE SET
            content_hash=excluded.content_hash,
            content_text=excluded.content_text,
            metadata_json=excluded.metadata_json,
            retrieved_at=excluded.retrieved_at,
            source_type=excluded.source_type,
            url=excluded.url,
            stale_after_days=excluded.stale_after_days,
            embedding_id=excluded.embedding_id;
        """,
        (
            snap.snapshot_id,
            snap.content_hash,
            snap.content_text,
            json.dumps(snap.metadata, default=str),
            snap.retrieved_at.isoformat(),
            snap.source_type,
            snap.url,
            snap.stale_after_days,
            snap.embedding_id,
        ),
    )
    conn.commit()


def get_snapshot(conn: sqlite3.Connection, snapshot_id: str) -> Optional[SourceSnapshot]:
    cur = conn.execute(
        "SELECT snapshot_id, content_hash, content_text, metadata_json, retrieved_at, source_type, url, stale_after_days, embedding_id "
        "FROM snapshots WHERE snapshot_id=?",
        (snapshot_id,),
    )
    row = cur.fetchone()
    if not row:
        return None
    return _row_to_snapshot(row)


def list_snapshots(conn: sqlite3.Connection, limit: int = 50) -> List[SourceSnapshot]:
    cur = conn.execute(
        "SELECT snapshot_id, content_hash, content_text, metadata_json, retrieved_at, source_type, url, stale_after_days, embedding_id "
        "FROM snapshots ORDER BY retrieved_at DESC LIMIT ?",
        (limit,),
    )
    return [_row_to_snapshot(row) for row in cur.fetchall()]


def list_snapshots_all(conn: sqlite3.Connection) -> List[SourceSnapshot]:
    cur = conn.execute(
        "SELECT snapshot_id, content_hash, content_text, metadata_json, retrieved_at, source_type, url, stale_after_days, embedding_id "
        "FROM snapshots ORDER BY retrieved_at DESC"
    )
    return [_row_to_snapshot(row) for row in cur.fetchall()]


def insert_brief(
    conn: sqlite3.Connection,
    brief_id: str,
    topic: str,
    audience: str,
    lens: str,
    generated_at: str,
    version: int,
    brief_json: str,
    citations_json: str,
) -> None:
    conn.execute(
        """
        INSERT INTO briefs (
            brief_id, topic, audience, lens, generated_at, version, brief_json, citations_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?);
        """,
        (brief_id, topic, audience, lens, generated_at, version, brief_json, citations_json),
    )
    conn.commit()


def get_latest_brief_version(conn: sqlite3.Connection, topic: str, lens: str) -> int:
    cur = conn.execute(
        "SELECT MAX(version) FROM briefs WHERE topic=? AND lens=?",
        (topic, lens),
    )
    row = cur.fetchone()
    if not row or row[0] is None:
        return 0
    return int(row[0])


def list_briefs(conn: sqlite3.Connection, limit: int = 50):
    cur = conn.execute(
        "SELECT brief_id, topic, lens, generated_at, version FROM briefs "
        "ORDER BY generated_at DESC LIMIT ?",
        (limit,),
    )
    return cur.fetchall()


def get_brief_json(conn: sqlite3.Connection, brief_id: str) -> Optional[str]:
    cur = conn.execute(
        "SELECT brief_json FROM briefs WHERE brief_id=?",
        (brief_id,),
    )
    row = cur.fetchone()
    if not row:
        return None
    return row[0]


def insert_audit_log(
    conn: sqlite3.Connection,
    audit_id: str,
    action: str,
    user: str | None,
    timestamp: str,
    details_json: str,
) -> None:
    conn.execute(
        """
        INSERT INTO audit_log (audit_id, action, user, timestamp, details_json)
        VALUES (?, ?, ?, ?, ?);
        """,
        (audit_id, action, user, timestamp, details_json),
    )
    conn.commit()


def _row_to_snapshot(row) -> SourceSnapshot:
    (
        snapshot_id,
        content_hash,
        content_text,
        metadata_json,
        retrieved_at,
        source_type,
        url,
        stale_after_days,
        embedding_id,
    ) = row
    return SourceSnapshot(
        snapshot_id=snapshot_id,
        content_hash=content_hash,
        content_text=content_text,
        metadata=json.loads(metadata_json),
        retrieved_at=SourceSnapshot.now_utc().fromisoformat(retrieved_at),
        source_type=source_type,
        url=url,
        stale_after_days=int(stale_after_days),
        embedding_id=embedding_id,
    )
