# Market-Trend Research Desk (MTRD)
**Strategic Intelligence System for Automated Market Analysis**

## Business Impact and Objective
Market analysts often face a "synthesis bottleneck," where manual processing of fragmented reports delays critical decision-making. MTRD automates the ingestion-to-brief pipeline, providing audit-ready market snapshots. This project demonstrates a production-minded approach to market intelligence, moving beyond simple chat interfaces to structured, evidence-first reporting.

## Executive Summary
This system transforms raw, unstructured industry data into structured competitive intelligence.
* **Business Question:** How can we ensure 100% data lineage and "evidence-first" reporting for high-stakes market briefs?
* **Core Insight:** By implementing a Tiered Synthesis Layer, the system maintains high accuracy during local inference while providing a clear architectural path for high-performance API integration.
* **Outcome:** Provides a validated SQLite audit trail that maps every summary back to its source hash, ensuring data integrity for stakeholders.

## Technical Workflow
1. **Ingestion:** Automated pipeline for local .txt and .md sources using Pydantic for strict schema validation.
2. **Storage:** SQLite (Write-Ahead Logging mode) for high-concurrency snapshotting, metadata tracking, and content hashing.
3. **Synthesis:** A dual-track approach featuring Brief-Lite for rapid extraction and an Extractive Fallback for complex datasets.

## Tech Stack and Scalability
* **Current Engine:** Python, PydanticAI, Ollama (Local Inference for development and data privacy).
* **Model Strategy:** Modular architecture currently utilizing local LLMs, with a defined roadmap to integrate OpenAI or Anthropic APIs for high-reasoning tasks as the project budget scales.
* **Reliability:** Full test coverage for ingestion, storage, and synthesis modules via pytest.

## Run (Local)
```bash
uv venv
. .venv/bin/activate
uv pip install -r requirements.txt
python mtrd_cli.py ingest-files --path ./data/sources --db ./data/snapshots.db
pytest -q
```

## Roadmap
* **Vector Integration: Transitioning to ChromaDB/LlamaIndex to support retrieval across large-scale document libraries.

* **Stakeholder Interface: Developing a Streamlit UI to move from CLI-based operations to user-facing dashboards.

* **Enterprise Features: Automated "Change Reports" (diffing) to track market shifts over time.
