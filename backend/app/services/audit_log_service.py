import hashlib
import json
from datetime import datetime, timezone
from typing import Any


class AuditLogService:
    """Creates tamper-evident audit log hashes.

    Database insert logic can be added after the ORM session flow is finalised.
    """

    GENESIS_HASH = "0" * 64

    def build_log_hash(self, previous_hash: str | None, log_content: dict[str, Any]) -> str:
        previous = previous_hash or self.GENESIS_HASH
        canonical = json.dumps(log_content, sort_keys=True, default=str)
        return hashlib.sha256((previous + canonical).encode("utf-8")).hexdigest()

    def make_log_content(
        self,
        actor_user_id: int | None,
        action: str,
        resource_type: str | None,
        resource_id: str | None,
        result: str,
        description: str | None = None,
    ) -> dict[str, Any]:
        return {
            "actor_user_id": actor_user_id,
            "action": action,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "result": result,
            "description": description,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
