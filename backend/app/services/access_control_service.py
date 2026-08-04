class AccessControlService:
    def can_download_draft(self, user_id: int, file_id: int) -> bool:
        """Deny until both grant and active key-wrapping checks are implemented."""
        return False
