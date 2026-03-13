from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable, List

from mtrd.config import SNAPSHOT_DIR
from mtrd.ingest.sources import RawDocument


def save_snapshots(docs: Iterable[RawDocument]) -> List[Path]:
    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    paths: List[Path] = []
    for doc in docs:
        path = SNAPSHOT_DIR / f"{doc.meta.content_hash}.json"
        payload = {"meta": doc.meta.model_dump(), "text": doc.text}
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        paths.append(path)
    return paths
