from __future__ import annotations

import json
import sys
from datetime import datetime
from uuid import uuid4
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parent
SRC_DIR = ROOT / "src"
if SRC_DIR.exists() and str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from mtrd.briefs import brief_to_markdown  # noqa: E402
from mtrd.config import AppConfig, BRIEF_DIR, ensure_dirs  # noqa: E402
from mtrd.audit.diff import diff_brief_payloads, diff_briefs  # noqa: E402
from mtrd.audit.log import write_audit_log  # noqa: E402
from mtrd.ingest.sources import ingest_files, to_snapshot  # noqa: E402
from mtrd.rag.index import build_index_from_db  # noqa: E402
from mtrd.rag.query import generate_brief  # noqa: E402
from mtrd.storage.db import (  # noqa: E402
    connect,
    get_latest_brief_version,
    get_brief_json,
    init_db,
    insert_brief,
    list_briefs,
    list_snapshots_all,
    upsert_snapshot,
)


def _default_path(name: str) -> str:
    return str(Path("data") / name)


def _staleness_days(source) -> int | None:
    try:
        base = getattr(source, "published_at", None) or getattr(source, "collected_at", None)
        if not base:
            return None
        if isinstance(base, str):
            base = datetime.fromisoformat(base)
        delta = datetime.utcnow() - base.replace(tzinfo=None)
        return max(0, delta.days)
    except Exception:
        return None


st.set_page_config(page_title="MTRD", layout="wide")

st.title("Market-Trend Research Desk")
st.caption("Evidence-first market briefs with traceable sources.")

with st.sidebar:
    st.header("Configuration")
    data_path = st.text_input("Data source path", value=_default_path("sources"))
    db_path = st.text_input("SQLite DB path", value=_default_path("snapshots.db"))
    lens = st.selectbox("Lens", ["Growth", "Risk", "Enterprise", "Mid-Market"])
    top_k = st.number_input("Top‑k sources", min_value=1, max_value=20, value=6, step=1)
    structured = st.checkbox("Enable structured synthesis (if available)", value=False)
    tier = st.selectbox("Tier", ["fast", "standard"], index=0)
    st.subheader("Chunking")
    chunk_strategy = st.selectbox("Strategy", ["default", "fixed", "hierarchical"], index=0)
    chunk_size = st.number_input("Chunk size", min_value=128, max_value=2048, value=512, step=64)
    chunk_overlap = st.number_input("Chunk overlap", min_value=0, max_value=512, value=50, step=10)

    try:
        conn = connect(Path(db_path))
        init_db(conn)
        snap_count = len(list_snapshots_all(conn))
        st.caption(f"Snapshots in DB: {snap_count}")
    except Exception:
        st.caption("Snapshots in DB: N/A")

st.subheader("Inputs")
query = st.text_input("Query", value="Competitive positioning in mid-market")
audience = st.text_input("Audience", value="Executive")

st.subheader("Actions")
col1, col2, col3 = st.columns(3)
sources_state = st.session_state.setdefault("sources", [])
brief_state = st.session_state.setdefault("brief", None)
with col1:
    if st.button("Ingest Files"):
        source_root = Path(data_path)
        if not source_root.exists():
            st.error(f"Source path not found: {source_root}")
        else:
            with st.spinner("Ingesting files into SQLite..."):
                docs = ingest_files(source_root)
                conn = connect(Path(db_path))
                init_db(conn)
                for doc in docs:
                    snap = to_snapshot(doc)
                    upsert_snapshot(conn, snap)
            st.success(f"Ingested {len(docs)} documents into {db_path}")
with col2:
    if st.button("Build Index"):
        db_file = Path(db_path)
        if not db_file.exists():
            st.error(f"SQLite DB not found: {db_file}")
        else:
            conn = connect(db_file)
            init_db(conn)
            snapshots = list_snapshots_all(conn)
            if not snapshots:
                st.error("No snapshots found. Run ingestion first.")
            else:
                with st.spinner("Building Chroma index..."):
                    ensure_dirs()
                    config = AppConfig()
                    config.chunk_strategy = chunk_strategy
                    config.chunk_size = int(chunk_size)
                    config.chunk_overlap = int(chunk_overlap)
                    build_index_from_db(db_file, config, rebuild=True)
                st.success(f"Index built from {len(snapshots)} snapshots")
with col3:
    if st.button("Generate Brief"):
        if not query.strip():
            st.error("Query is required.")
        else:
            with st.spinner("Retrieving sources and generating brief..."):
                ensure_dirs()
                config = AppConfig()
                if structured:
                    config.extractive_only = False
                brief = generate_brief(query, audience, lens, config, tier=tier)
                brief_state = brief
                st.session_state["brief"] = brief_state
                sources_state = brief.citations
                st.session_state["sources"] = sources_state
                conn = connect(Path(db_path))
                init_db(conn)
                version = get_latest_brief_version(conn, brief.topic, brief.lens) + 1
                slug = brief.topic.lower().replace(" ", "-")
                brief_id = str(uuid4())
                insert_brief(
                    conn=conn,
                    brief_id=brief_id,
                    topic=brief.topic,
                    audience=brief.audience,
                    lens=brief.lens,
                    generated_at=brief.generated_at.isoformat(),
                    version=version,
                    brief_json=brief.model_dump_json(),
                    citations_json=json.dumps([c.model_dump() for c in brief.citations], default=str),
                )
                write_audit_log(
                    conn,
                    action="generate",
                    details={"brief_id": brief_id, "topic": brief.topic, "lens": brief.lens, "version": version},
                )
                if not config.extractive_only and any(
                    "fallback" in a.lower() for a in (brief.assumptions or [])
                ):
                    write_audit_log(
                        conn,
                        action="fallback",
                        details={"brief_id": brief_id, "topic": brief.topic, "lens": brief.lens},
                    )
            st.success("Brief generated.")

st.subheader("One-Click")
if st.button("Run End-to-End Pipeline"):
    source_root = Path(data_path)
    db_file = Path(db_path)
    if not source_root.exists():
        st.error(f"Source path not found: {source_root}")
    else:
        with st.spinner("Running ingest → index → brief..."):
            docs = ingest_files(source_root)
            conn = connect(db_file)
            init_db(conn)
            for doc in docs:
                snap = to_snapshot(doc)
                upsert_snapshot(conn, snap)
            config = AppConfig()
            if structured:
                config.extractive_only = False
            config.chunk_strategy = chunk_strategy
            config.chunk_size = int(chunk_size)
            config.chunk_overlap = int(chunk_overlap)
            build_index_from_db(db_file, config, rebuild=True)
            brief = generate_brief(query, audience, lens, config, tier=tier)
            st.session_state["brief"] = brief
            st.session_state["sources"] = brief.citations
            version = get_latest_brief_version(conn, brief.topic, brief.lens) + 1
            slug = brief.topic.lower().replace(" ", "-")
            brief_id = str(uuid4())
            insert_brief(
                conn=conn,
                brief_id=brief_id,
                topic=brief.topic,
                audience=brief.audience,
                lens=brief.lens,
                generated_at=brief.generated_at.isoformat(),
                version=version,
                brief_json=brief.model_dump_json(),
                citations_json=json.dumps([c.model_dump() for c in brief.citations], default=str),
            )
            write_audit_log(
                conn,
                action="generate",
                details={"brief_id": brief_id, "topic": brief.topic, "lens": brief.lens, "version": version},
            )
            if not config.extractive_only and any(
                "fallback" in a.lower() for a in (brief.assumptions or [])
            ):
                write_audit_log(
                    conn,
                    action="fallback",
                    details={"brief_id": brief_id, "topic": brief.topic, "lens": brief.lens},
                )
        st.success("Pipeline complete.")

st.subheader("Results")
if sources_state:
    st.markdown("**Top‑k Sources**")
    for idx, source in enumerate(sources_state, start=1):
        title = getattr(source, "title", "Untitled")
        url = getattr(source, "url", "")
        staleness = _staleness_days(source)
        suffix = f" (staleness {staleness}d)" if staleness is not None else ""
        st.write(f"{idx}. {title} {url}{suffix}")
else:
    st.write("No sources yet.")

if brief_state:
    st.markdown("**Brief (Extractive default)**")
    st.json(brief_state.model_dump())

    st.markdown("**Export**")
    ensure_dirs()
    slug = brief_state.topic.lower().replace(" ", "-")
    ts = brief_state.generated_at.strftime("%Y%m%d%H%M")
    json_path = BRIEF_DIR / f"{slug}-{ts}.json"
    md_path = BRIEF_DIR / f"{slug}-{ts}.md"

    if st.button("Save JSON + Markdown"):
        json_path.write_text(brief_state.model_dump_json(indent=2), encoding="utf-8")
        md_path.write_text(brief_to_markdown(brief_state), encoding="utf-8")
        conn = connect(Path(db_path))
        init_db(conn)
        write_audit_log(
            conn,
            action="export",
            details={"json": json_path.name, "markdown": md_path.name, "topic": brief_state.topic},
        )
        st.success(f"Saved {json_path.name} and {md_path.name}")

    json_bytes = brief_state.model_dump_json(indent=2).encode("utf-8")
    md_bytes = brief_to_markdown(brief_state).encode("utf-8")
    st.download_button("Download JSON", data=json_bytes, file_name=json_path.name)
    st.download_button("Download Markdown", data=md_bytes, file_name=md_path.name)

st.subheader("Diff Briefs")
ensure_dirs()
conn = None
try:
    conn = connect(Path(db_path))
    init_db(conn)
    brief_rows = list_briefs(conn, limit=200)
except Exception:
    brief_rows = []

if len(brief_rows) >= 2:
    brief_ids = [row[0] for row in brief_rows]
    col_a, col_b = st.columns(2)
    with col_a:
        a_id = st.selectbox("Brief A (DB)", brief_ids, index=0)
    with col_b:
        b_id = st.selectbox("Brief B (DB)", brief_ids, index=1)
    if st.button("Show Diff (DB)"):
        a_json = get_brief_json(conn, a_id) if conn else None
        b_json = get_brief_json(conn, b_id) if conn else None
        if not a_json or not b_json:
            st.error("Brief id not found in DB.")
        else:
            diff_text = diff_brief_payloads(a_json, b_json, label_a=a_id, label_b=b_id)
            st.code(diff_text, language="diff")
else:
    brief_files = sorted(BRIEF_DIR.glob("*.json"))
    brief_names = [p.name for p in brief_files]
    if len(brief_names) < 2:
        st.write("Need at least two brief JSON files to diff.")
    else:
        col_a, col_b = st.columns(2)
        with col_a:
            a_name = st.selectbox("Brief A (file)", brief_names, index=0)
        with col_b:
            b_name = st.selectbox("Brief B (file)", brief_names, index=1)
        if st.button("Show Diff (file)"):
            diff_text = diff_briefs(BRIEF_DIR / a_name, BRIEF_DIR / b_name)
            st.code(diff_text, language="diff")
