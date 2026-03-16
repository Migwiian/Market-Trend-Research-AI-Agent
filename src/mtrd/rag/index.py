from __future__ import annotations

from typing import Iterable

import shutil
from pathlib import Path

from llama_index.core import Settings, VectorStoreIndex, StorageContext
from llama_index.core.node_parser import SentenceSplitter, HierarchicalNodeParser
import chromadb
from llama_index.vector_stores.chroma import ChromaVectorStore

from mtrd.config import CHROMA_DIR, AppConfig
from mtrd.ingest.loader import snapshots_to_llama_documents, to_llama_documents
from mtrd.ingest.sources import RawDocument
from mtrd.rag.runtime import get_embed_model
from mtrd.storage.db import connect, init_db, list_snapshots_all


def _get_chroma_dir(override: Path | None) -> Path:
    return override or CHROMA_DIR


def _configure_chunking(config: AppConfig) -> None:
    strategy = (config.chunk_strategy or "default").lower()
    if strategy == "default":
        return
    if strategy == "fixed":
        Settings.node_parser = SentenceSplitter(
            chunk_size=config.chunk_size, chunk_overlap=config.chunk_overlap
        )
        return
    if strategy == "hierarchical":
        Settings.node_parser = HierarchicalNodeParser.from_defaults(
            chunk_sizes=[2048, config.chunk_size, 128]
        )
        return
    raise ValueError(f"Unknown chunk strategy: {config.chunk_strategy}")


def build_index(
    docs: Iterable[RawDocument],
    config: AppConfig,
    persist_dir: Path | None = None,
    rebuild: bool = False,
) -> VectorStoreIndex:
    chroma_dir = _get_chroma_dir(persist_dir)
    if rebuild and chroma_dir.exists():
        shutil.rmtree(chroma_dir)
    chroma_dir.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(chroma_dir))
    collection = client.get_or_create_collection(name=config.chroma_collection)
    vector_store = ChromaVectorStore(chroma_collection=collection)
    storage_context = StorageContext.from_defaults(vector_store=vector_store)
    Settings.embed_model = get_embed_model(config)
    _configure_chunking(config)

    llama_docs = to_llama_documents(docs)
    index = VectorStoreIndex.from_documents(llama_docs, storage_context=storage_context)
    return index


def build_index_from_db(
    db_path: Path,
    config: AppConfig,
    persist_dir: Path | None = None,
    rebuild: bool = False,
) -> VectorStoreIndex:
    conn = connect(db_path)
    init_db(conn)
    snapshots = list_snapshots_all(conn)
    chroma_dir = _get_chroma_dir(persist_dir)
    if rebuild and chroma_dir.exists():
        shutil.rmtree(chroma_dir)
    chroma_dir.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(chroma_dir))
    collection = client.get_or_create_collection(name=config.chroma_collection)
    vector_store = ChromaVectorStore(chroma_collection=collection)
    storage_context = StorageContext.from_defaults(vector_store=vector_store)
    Settings.embed_model = get_embed_model(config)
    _configure_chunking(config)
    llama_docs = snapshots_to_llama_documents(snapshots)
    return VectorStoreIndex.from_documents(llama_docs, storage_context=storage_context)


def load_index(config: AppConfig, persist_dir: Path | None = None) -> VectorStoreIndex:
    chroma_dir = _get_chroma_dir(persist_dir)
    client = chromadb.PersistentClient(path=str(chroma_dir))
    collection = client.get_or_create_collection(name=config.chroma_collection)
    vector_store = ChromaVectorStore(chroma_collection=collection)
    storage_context = StorageContext.from_defaults(vector_store=vector_store)
    Settings.embed_model = get_embed_model(config)
    _configure_chunking(config)
    return VectorStoreIndex.from_vector_store(vector_store=vector_store, storage_context=storage_context)
