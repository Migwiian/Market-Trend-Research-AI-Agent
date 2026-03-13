from __future__ import annotations

from typing import Iterable, List

from llama_index.core import Document

from mtrd.ingest.sources import RawDocument


def to_llama_documents(docs: Iterable[RawDocument]) -> List[Document]:
    out: List[Document] = []
    for doc in docs:
        out.append(Document(text=doc.text, metadata=doc.meta.model_dump()))
    return out
