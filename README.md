# A Multi-Agent Evidence Engine for Market Intelligence
**AI research pipeline for audit‑ready briefs**

## Problem
Market teams need fast competitive briefs, but source data is messy and hard to trust. Most tools return fluent summaries without a reliable audit trail.

## Action
Build a local-first pipeline that ingests raw documents, preserves lineage, retrieves the most relevant evidence, and generates a structured brief that always links back to sources.

## Solution
MTRD turns fragmented documents into audit-ready briefs with citations, bounded context, and repeatable outputs.

## What It Includes
* **Ingestion:** txt/md/pdf, RSS, and web sources.
* **Snapshot Store:** SQLite with content hashing; JSON/Markdown are exports only.
* **Indexing + Retrieval:** Chroma + LlamaIndex, top‑k evidence with preserved metadata.
* **Brief Generation:** Extractive‑only by default; optional structured synthesis by tier (fast vs standard).
* **Governance:** Audit log, brief versioning, and diffing.
* **UI:** Streamlit for end‑to‑end demo flow.

## Run (Local)
```bash
uv venv
. .venv/bin/activate
uv pip install -r requirements.txt
PYTHONPATH=src python -m mtrd.cli ingest-files-cmd --path ./data/sources --db ./data/snapshots.db
PYTHONPATH=src python -m mtrd.cli build-index-cmd --db ./data/snapshots.db --rebuild
PYTHONPATH=src python -m mtrd.cli brief --topic "Mid-market CRM" --audience "Executive" --lens "Growth"
streamlit run streamlit_app.py
pytest -q
```
## Current Progress
* **Vector Retrieval:** Scale Chroma/LlamaIndex across larger document libraries.
* **Stakeholder Interface:** Expand the dashboard with filters and report sharing.
* **Temporal Analysis:** Automated change reports to track market shifts over time.
