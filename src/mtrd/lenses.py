from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Any

from mtrd.config import CONFIG_DIR


def load_lenses() -> Dict[str, Any]:
    path = Path(CONFIG_DIR) / "lenses.json"
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def get_lens_definition(lens: str) -> str:
    lenses = load_lenses()
    if lens not in lenses:
        raise ValueError(f"Unknown lens: {lens}")
    return lenses[lens]["definition"]
