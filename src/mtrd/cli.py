from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import typer
from rich import print

from mtrd.audit.diff import diff_briefs
from mtrd.audit.snapshot import save_snapshots
from mtrd.config import AppConfig, BRIEF_DIR, SNAPSHOT_DIR, ensure_dirs
from mtrd.ingest.sources import ingest_files, ingest_rss, ingest_web, RawDocument
from mtrd.rag.index import build_index
from mtrd.rag.query import generate_brief

app = typer.Typer(no_args_is_help=True)


def _load_snapshots() -> list[RawDocument]:
    docs: list[RawDocument] = []
    for path in SNAPSHOT_DIR.glob("*.json"):
        payload = json.loads(path.read_text(encoding="utf-8"))
        meta = payload["meta"]
        text = payload["text"]
        from mtrd.models import SourceMeta

        docs.append(RawDocument(text=text, meta=SourceMeta(**meta)))
    return docs


@app.command()
def ingest_files_cmd(path: Path = typer.Option(..., "--path")) -> None:
    """Ingest local files and save snapshots."""
    ensure_dirs()
    docs = ingest_files(path)
    save_snapshots(docs)
    print(f"Ingested {len(docs)} documents")


@app.command()
def ingest_rss_cmd(feed: list[str] = typer.Option(..., "--feed")) -> None:
    """Ingest RSS feeds and save snapshots."""
    ensure_dirs()
    docs = ingest_rss(feed)
    save_snapshots(docs)
    print(f"Ingested {len(docs)} documents")


@app.command()
def ingest_web_cmd(url: list[str] = typer.Option(..., "--url")) -> None:
    """Ingest web pages and save snapshots."""
    ensure_dirs()
    docs = ingest_web(url)
    save_snapshots(docs)
    print(f"Ingested {len(docs)} documents")


@app.command()
def build_index_cmd(from_snapshots: bool = typer.Option(True, "--from-snapshots")) -> None:
    """Build Chroma index from snapshots."""
    ensure_dirs()
    config = AppConfig()
    docs = _load_snapshots() if from_snapshots else []
    if not docs:
        raise typer.BadParameter("No snapshots found. Run ingest first.")
    build_index(docs, config)
    print("Index built")


@app.command()
def brief(
    topic: str = typer.Option(..., "--topic"),
    audience: str = typer.Option(..., "--audience"),
    lens: str = typer.Option(..., "--lens"),
) -> None:
    """Generate a typed brief and save as JSON + Markdown."""
    ensure_dirs()
    config = AppConfig()
    brief = generate_brief(topic, audience, lens, config)

    slug = topic.lower().replace(" ", "-")
    ts = datetime.utcnow().strftime("%Y%m%d%H%M")
    json_path = BRIEF_DIR / f"{slug}-{ts}.json"
    md_path = BRIEF_DIR / f"{slug}-{ts}.md"

    json_path.write_text(brief.model_dump_json(indent=2), encoding="utf-8")
    md_path.write_text(_brief_to_md(brief), encoding="utf-8")

    print(f"Saved {json_path}")
    print(f"Saved {md_path}")


@app.command()
def diff_briefs_cmd(a: Path = typer.Option(..., "--a"), b: Path = typer.Option(..., "--b")) -> None:
    """Diff two brief JSON outputs."""
    diff = diff_briefs(a, b)
    print(diff)


def _brief_to_md(brief) -> str:
    lines = [f"# {brief.topic}", ""]
    lines.append(f"Audience: {brief.audience}")
    lines.append(f"Lens: {brief.lens}")
    lines.append("")
    lines.append("## Executive Summary")
    for item in brief.executive_summary:
        lines.append(f"- {item}")
    lines.append("")
    for section in brief.sections:
        lines.append(f"## {section.heading}")
        for bullet in section.bullets:
            lines.append(f"- {bullet}")
        lines.append("")
    lines.append("## Key Risks")
    for item in brief.key_risks:
        lines.append(f"- {item}")
    lines.append("")
    lines.append("## Key Opportunities")
    for item in brief.key_opportunities:
        lines.append(f"- {item}")
    lines.append("")
    lines.append("## Signals")
    for sig in brief.signals:
        lines.append(f"- {sig.claim} (confidence {sig.confidence})")
    lines.append("")
    lines.append("## Assumptions")
    for item in brief.assumptions:
        lines.append(f"- {item}")
    lines.append("")
    lines.append("## Decision Summary")
    lines.append(brief.decision_summary)
    lines.append("")
    lines.append("## Citations")
    for cite in brief.citations:
        lines.append(f"- {cite.title} | {cite.url}")
    return "\n".join(lines)
