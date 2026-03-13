# Market-Trend Research Desk (MTRD)
**Multi-Agent Intelligence System for Automated Market Synthesis**

## Executive Summary
MTRD transforms fragmented industry data into audit-ready competitive briefs through a coordinated multi-agent workflow. Unlike standard RAG applications, this system prioritizes **data lineage** and **deterministic validation** to ensure every insight is traceable to a verified source.

* **Business Question:** How can market teams produce high-velocity, evidence-first briefs without sacrificing auditability?
* **Solution:** A specialized agent swarm (Ingest, Validate, Synthesize, Critique, Audit) that enforces structural integrity at every stage of the intelligence pipeline.
* **Outcome:** Strategic reports with a 100% verifiable lineage trail stored in a high-concurrency SQLite backend.

## Multi-Agent Orchestration
The system moves beyond simple prompting by assigning discrete responsibilities to specialized agents:

1. **Ingestion Agent:** Extracts raw data from .txt and .md sources using Pydantic for strict schema enforcement.
2. **Validation Agent:** Performs quality gates on metadata completeness and structural consistency before storage.
3. **Synthesis Agent:** Executes a tiered strategy—**Brief-Lite** for rapid extraction and **Extractive Fallback** for complex datasets.
4. **Critique Agent:** Acting as a "human-in-the-loop" proxy, it flags weak evidence and enforces direct alignment with source text.
5. **Audit Agent:** Manages the permanent record, mapping every claim to content hashes and source IDs in the SQLite snapshot store.

## Architecture and Production Readiness
* **Storage:** SQLite (WAL mode) for robust, high-concurrency snapshotting and provenance tracking.
* **Inference Strategy:** Optimized for local-first execution (Ollama) to maintain data privacy, with a modular driver ready for OpenAI/Anthropic API integration as project budgets scale.
* **Reliability:** Comprehensive unit and integration testing via pytest, covering the full ingestion-to-audit lifecycle.

## Run (Local)
```bash
uv venv
. .venv/bin/activate
uv pip install -r requirements.txt
python mtrd_cli.py ingest-files --path ./data/sources --db ./data/snapshots.db
pytest -q
```
## Roadmap
* **Vector Retrieval: Integrating ChromaDB/LlamaIndex for semantic search across 10,000+ document libraries.

* **Stakeholder Interface: Developing a Streamlit dashboard to transition from CLI to executive-facing visuals.

* **Temporal Analysis: Automated "Change Reports" to track and diff market shifts over time.
