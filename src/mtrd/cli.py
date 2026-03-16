from __future__ import annotations

import os
from uuid import uuid4
from datetime import datetime
from pathlib import Path

import typer
from rich import print

from mtrd.audit.diff import diff_brief_payloads, diff_briefs
from mtrd.audit.log import write_audit_log
from mtrd.briefs import brief_to_markdown
from mtrd.config import AppConfig, BRIEF_DIR, ensure_dirs
from mtrd.ingest.sources import ingest_files, ingest_rss, ingest_web, to_snapshot
from mtrd.rag.index import build_index_from_db, load_index
from mtrd.rag.query import generate_brief
from storage.db import (
    connect,
    get_latest_brief_version,
    get_brief_json,
    init_db,
    insert_brief,
    list_briefs,
    list_snapshots,
    upsert_snapshot,
)

app = typer.Typer(no_args_is_help=True)


@app.command()
def ingest_files_cmd(
    path: Path = typer.Option(..., "--path"),
    db: Path = typer.Option(..., "--db"),
) -> None:
    """Ingest local files and write snapshots to SQLite."""
    docs = ingest_files(path)
    conn = connect(db)
    init_db(conn)
    for doc in docs:
        snap = to_snapshot(doc)
        upsert_snapshot(conn, snap)
    write_audit_log(
        conn,
        action="ingest",
        details={"count": len(docs), "source": "files", "path": str(path)},
    )
    print(f"Ingested {len(docs)} documents into {db}")


@app.command()
def ingest_rss_cmd(
    feed: list[str] = typer.Option(..., "--feed"),
    db: Path = typer.Option(..., "--db"),
) -> None:
    """Ingest RSS feeds and write snapshots to SQLite."""
    docs = ingest_rss(feed)
    conn = connect(db)
    init_db(conn)
    for doc in docs:
        snap = to_snapshot(doc)
        upsert_snapshot(conn, snap)
    write_audit_log(
        conn,
        action="ingest",
        details={"count": len(docs), "source": "rss", "feeds": feed},
    )
    print(f"Ingested {len(docs)} documents into {db}")


@app.command()
def ingest_web_cmd(
    url: list[str] = typer.Option(..., "--url"),
    db: Path = typer.Option(..., "--db"),
) -> None:
    """Ingest web pages and write snapshots to SQLite."""
    docs = ingest_web(url)
    conn = connect(db)
    init_db(conn)
    for doc in docs:
        snap = to_snapshot(doc)
        upsert_snapshot(conn, snap)
    write_audit_log(
        conn,
        action="ingest",
        details={"count": len(docs), "source": "web", "urls": url},
    )
    print(f"Ingested {len(docs)} documents into {db}")


@app.command()
def list_snapshots_cmd(
    db: Path = typer.Option(..., "--db"),
    limit: int = typer.Option(50, "--limit"),
) -> None:
    """List snapshots from SQLite."""
    conn = connect(db)
    init_db(conn)
    rows = list_snapshots(conn, limit=limit)
    for row in rows:
        print(f"{row.snapshot_id}\t{row.source_type}\t{row.retrieved_at.isoformat()}\t{row.url}")


@app.command()
def build_index_cmd(
    db: Path = typer.Option(..., "--db"),
    rebuild: bool = typer.Option(False, "--rebuild"),
    chunk_strategy: str = typer.Option("default", "--chunk-strategy"),
    chunk_size: int = typer.Option(512, "--chunk-size"),
    chunk_overlap: int = typer.Option(50, "--chunk-overlap"),
) -> None:
    """Build Chroma index from SQLite snapshots."""
    ensure_dirs()
    config = AppConfig()
    config.chunk_strategy = chunk_strategy
    config.chunk_size = chunk_size
    config.chunk_overlap = chunk_overlap
    build_index_from_db(db, config, rebuild=rebuild)
    conn = connect(db)
    init_db(conn)
    write_audit_log(
        conn,
        action="index",
        details={
            "db": str(db),
            "rebuild": rebuild,
            "chunk_strategy": chunk_strategy,
            "chunk_size": chunk_size,
            "chunk_overlap": chunk_overlap,
        },
    )
    print("Index built from SQLite")


@app.command()
def brief(
    topic: str = typer.Option(..., "--topic"),
    audience: str = typer.Option(..., "--audience"),
    lens: str = typer.Option(..., "--lens"),
    structured: bool = typer.Option(False, "--structured"),
    tier: str = typer.Option("fast", "--tier"),
) -> None:
    """Generate a typed brief and save as JSON + Markdown."""
    ensure_dirs()
    config = AppConfig()
    if structured:
        config.extractive_only = False
    brief = generate_brief(topic, audience, lens, config, tier=tier)

    slug = topic.lower().replace(" ", "-")
    ts = datetime.utcnow().strftime("%Y%m%d%H%M")
    json_path = BRIEF_DIR / f"{slug}-{ts}.json"
    md_path = BRIEF_DIR / f"{slug}-{ts}.md"

    json_path.write_text(brief.model_dump_json(indent=2), encoding="utf-8")
    md_path.write_text(brief_to_markdown(brief), encoding="utf-8")

    db = Path(os.getenv("MTRD_DB_PATH", "data/snapshots.db"))
    conn = connect(db)
    init_db(conn)
    version = get_latest_brief_version(conn, topic, lens) + 1
    brief_id = str(uuid4())
    insert_brief(
        conn=conn,
        brief_id=brief_id,
        topic=topic,
        audience=audience,
        lens=lens,
        generated_at=brief.generated_at.isoformat(),
        version=version,
        brief_json=brief.model_dump_json(),
        citations_json=json.dumps([c.model_dump() for c in brief.citations], default=str),
    )
    write_audit_log(
        conn,
        action="generate",
        details={"brief_id": brief_id, "topic": topic, "lens": lens, "version": version},
    )
    if not config.extractive_only and any(
        "fallback" in a.lower() for a in (brief.assumptions or [])
    ):
        write_audit_log(
            conn,
            action="fallback",
            details={"brief_id": brief_id, "topic": topic, "lens": lens},
        )

    print(f"Saved {json_path}")
    print(f"Saved {md_path}")


@app.command()
def list_briefs_cmd(
    db: Path = typer.Option(..., "--db"),
    limit: int = typer.Option(50, "--limit"),
) -> None:
    """List stored briefs."""
    conn = connect(db)
    init_db(conn)
    rows = list_briefs(conn, limit=limit)
    for row in rows:
        brief_id, topic, lens, generated_at, version = row
        print(f"{brief_id}\t{topic}\t{lens}\t{generated_at}\t{version}")


@app.command()
def query(
    query_text: str = typer.Option(..., "--query"),
    top_k: int = typer.Option(6, "--top-k"),
) -> None:
    """Retrieve top-k sources from Chroma."""
    ensure_dirs()
    config = AppConfig()
    index = load_index(config)
    retriever = index.as_retriever(similarity_top_k=top_k)
    nodes = retriever.retrieve(query_text)
    if not nodes:
        print("No results.")
        return
    for idx, node in enumerate(nodes, start=1):
        meta = node.metadata or {}
        title = meta.get("title", "Untitled")
        url = meta.get("url", "")
        snippet = node.get_text()[:200].replace("\n", " ")
        print(f"[{idx}] {title} {url}\n{snippet}\n")


@app.command()
def diff_briefs_cmd(a: Path = typer.Option(..., "--a"), b: Path = typer.Option(..., "--b")) -> None:
    """Diff two brief JSON outputs."""
    diff = diff_briefs(a, b)
    print(diff)


@app.command()
def diff_briefs_db_cmd(
    db: Path = typer.Option(..., "--db"),
    a: str = typer.Option(..., "--a"),
    b: str = typer.Option(..., "--b"),
) -> None:
    """Diff two briefs stored in SQLite by brief_id."""
    conn = connect(db)
    init_db(conn)
    a_json = get_brief_json(conn, a)
    b_json = get_brief_json(conn, b)
    if not a_json or not b_json:
        raise typer.BadParameter("Brief id not found in DB.")
    diff = diff_brief_payloads(a_json, b_json, label_a=a, label_b=b)
    print(diff)




if __name__ == "__main__":
    app()
