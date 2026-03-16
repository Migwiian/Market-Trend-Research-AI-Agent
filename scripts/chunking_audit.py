from __future__ import annotations

import json
import random
from pathlib import Path

from llama_index.core import Settings, VectorStoreIndex

from mtrd.config import AppConfig
from mtrd.ingest.loader import snapshots_to_llama_documents
from mtrd.storage.db import connect, init_db, list_snapshots_all


def main(db_path: Path, sample_size: int = 5) -> None:
    config = AppConfig()
    conn = connect(db_path)
    init_db(conn)
    snapshots = list_snapshots_all(conn)
    if not snapshots:
        raise SystemExit("No snapshots found. Run ingestion first.")

    docs = snapshots_to_llama_documents(snapshots)
    index = VectorStoreIndex.from_documents(docs)
    nodes = list(index.docstore.docs.values())

    parser = Settings.node_parser
    chunk_size = getattr(parser, "chunk_size", "N/A")
    chunk_overlap = getattr(parser, "chunk_overlap", "N/A")

    lengths = [len(n.text) for n in nodes]
    print(f"Node parser: {parser}")
    print(f"Chunk size: {chunk_size}")
    print(f"Chunk overlap: {chunk_overlap}")
    print(f"Chunks created: {len(nodes)}")
    print(f"Mean chunk size: {sum(lengths) / len(lengths):.0f}")
    print(f"Min: {min(lengths)}, Max: {max(lengths)}")

    sample = random.sample(nodes, min(sample_size, len(nodes)))
    for idx, node in enumerate(sample, start=1):
        meta = node.metadata or {}
        title = meta.get("title", "unknown")
        print(f"\n--- Chunk {idx} ---")
        print(f"Source: {title}")
        print(f"Text preview: {node.text[:200]}...")

    out = {
        "node_parser": str(parser),
        "chunk_size": chunk_size,
        "chunk_overlap": chunk_overlap,
        "chunks_created": len(nodes),
        "mean_chunk_size": sum(lengths) / len(lengths),
        "min_chunk_size": min(lengths),
        "max_chunk_size": max(lengths),
    }
    Path("data").mkdir(parents=True, exist_ok=True)
    Path("data/chunking_audit.json").write_text(json.dumps(out, indent=2), encoding="utf-8")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--db", required=True)
    parser.add_argument("--sample-size", type=int, default=5)
    args = parser.parse_args()
    main(Path(args.db), sample_size=args.sample_size)
