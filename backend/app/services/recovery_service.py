class RecoveryService:
    def create_recovery_request_draft(self, file_id: int, requested_by: int, reason: str) -> dict:
        return {
            "file_id": file_id,
            "requested_by": requested_by,
            "reason": reason,
            "status": "pending",
        }
