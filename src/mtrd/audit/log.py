from __future__ import annotations

import json
from datetime import datetime, timezone
from uuid import uuid4

from mtrd.storage.db import insert_audit_log


def write_audit_log(conn, action: str, details: dict, user: str | None = None) -> str:
    audit_id = str(uuid4())
    ts = datetime.now(timezone.utc).isoformat()
    insert_audit_log(
        conn=conn,
        audit_id=audit_id,
        action=action,
        user=user,
        timestamp=ts,
        details_json=json.dumps(details),
    )
    return audit_id
