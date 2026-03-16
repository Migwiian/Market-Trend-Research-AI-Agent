# MTRD: Market-Trend Research Desk
**A Multi-Agent RAG Pipeline for Cited Market Intelligence.**

## What it is
MTRD is a local-first AI engine that uses a **Librarian/Analyst agent orchestration** to turn messy documents into audit-ready briefs. It automates the research flow: ingesting PDFs, web pages, and RSS feeds, then generating reports where every claim is linked to a source.

## Why i built this
Most AI tools hallucinate or lose their sources. This tool uses **immutable SQLite snapshots** and **Pydantic contracts** to ensure that when the agents speak, the evidence is verifiable and hasn't been tampered with.

## Key Features
* **Multi-Agent Flow:** Uses a "Librarian" for retrieval and an "Analyst" for synthesis to keep logic separated.
* **Evidence-First RAG:** Maps data to a shared `EvidenceBlock` model so citations (Source ID + Hash) are preserved.
* **Data Integrity:** SQLite triggers block updates to source snapshots, creating a permanent audit trail.
* **Zero Cost:** Runs on local LLMs (**Ollama**) and local vector storage (**Chroma**).

## Tech Stack
* **Orchestration:** LlamaIndex (Multi-Agent logic)
* **Database:** SQLite & ChromaDB
* **Data Validation:** Pydantic
* **Environment:** Python (managed with `uv`)
* **UI:** Streamlit

## Quick Start
```bash
# Setup environment
uv venv && . .venv/bin/activate && uv pip install -r requirements.txt

# Ingest data and build index
PYTHONPATH=src python -m mtrd.cli ingest-files-cmd --path ./data/sources
PYTHONPATH=src python -m mtrd.cli build-index-cmd --rebuild

# Generate a brief
PYTHONPATH=src python -m mtrd.cli brief --topic "Market Trends"
