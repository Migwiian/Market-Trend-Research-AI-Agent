from __future__ import annotations

from typing import Iterable

from llama_index.core import Settings, VectorStoreIndex, StorageContext
from llama_index.vector_stores.chroma import ChromaVectorStore

from mtrd.config import CHROMA_DIR, AppConfig
from mtrd.ingest.loader import to_llama_documents
from mtrd.ingest.sources import RawDocument
from mtrd.rag.runtime import get_embed_model


def build_index(docs: Iterable[RawDocument], config: AppConfig) -> VectorStoreIndex:
    CHROMA_DIR.mkdir(parents=True, exist_ok=True)
    vector_store = ChromaVectorStore(persist_dir=str(CHROMA_DIR))
    storage_context = StorageContext.from_defaults(vector_store=vector_store)
    Settings.embed_model = get_embed_model(config)

    llama_docs = to_llama_documents(docs)
    index = VectorStoreIndex.from_documents(llama_docs, storage_context=storage_context)
    return index


def load_index(config: AppConfig) -> VectorStoreIndex:
    vector_store = ChromaVectorStore(persist_dir=str(CHROMA_DIR))
    storage_context = StorageContext.from_defaults(vector_store=vector_store)
    Settings.embed_model = get_embed_model(config)
    return VectorStoreIndex.from_vector_store(vector_store=vector_store, storage_context=storage_context)
