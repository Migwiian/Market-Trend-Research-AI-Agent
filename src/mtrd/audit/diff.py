from __future__ import annotations

import json
import difflib
from pathlib import Path


def diff_briefs(path_a: Path, path_b: Path) -> str:
    a = json.loads(path_a.read_text(encoding="utf-8"))
    b = json.loads(path_b.read_text(encoding="utf-8"))
    a_text = json.dumps(a, indent=2, sort_keys=True).splitlines()
    b_text = json.dumps(b, indent=2, sort_keys=True).splitlines()
    diff = difflib.unified_diff(a_text, b_text, fromfile=str(path_a), tofile=str(path_b))
    return "\n".join(diff)


def diff_brief_payloads(payload_a: str, payload_b: str, label_a: str = "A", label_b: str = "B") -> str:
    a = json.loads(payload_a)
    b = json.loads(payload_b)
    a_text = json.dumps(a, indent=2, sort_keys=True).splitlines()
    b_text = json.dumps(b, indent=2, sort_keys=True).splitlines()
    diff = difflib.unified_diff(a_text, b_text, fromfile=label_a, tofile=label_b)
    return "\n".join(diff)
