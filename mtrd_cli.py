from __future__ import annotations

import argparse
from pathlib import Path

from ingestion.sources import ingest_files, to_snapshot
from storage.db import connect, init_db, list_snapshots, upsert_snapshot


def cmd_ingest_files(args: argparse.Namespace) -> None:
    root = Path(args.path)
    db_path = Path(args.db)
    conn = connect(db_path)
    init_db(conn)

    sources = ingest_files(root)
    for raw in sources:
        snap = to_snapshot(raw)
        upsert_snapshot(conn, snap)

    print(f"Ingested {len(sources)} sources into {db_path}")


def cmd_list_snapshots(args: argparse.Namespace) -> None:
    db_path = Path(args.db)
    conn = connect(db_path)
    init_db(conn)

    rows = list_snapshots(conn, limit=args.limit)
    for row in rows:
        print(f"{row.snapshot_id}\t{row.source_type}\t{row.retrieved_at.isoformat()}\t{row.url}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="mtrd")
    sub = parser.add_subparsers(dest="command", required=True)

    p_ingest = sub.add_parser("ingest-files", help="Ingest local .txt/.md files into snapshot store")
    p_ingest.add_argument("--path", required=True, help="Root folder to ingest")
    p_ingest.add_argument("--db", required=True, help="SQLite DB path")
    p_ingest.set_defaults(func=cmd_ingest_files)

    p_list = sub.add_parser("list-snapshots", help="List snapshots in the DB")
    p_list.add_argument("--db", required=True, help="SQLite DB path")
    p_list.add_argument("--limit", type=int, default=50)
    p_list.set_defaults(func=cmd_list_snapshots)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
