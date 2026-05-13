class AccessControlService:
    def can_download_draft(self, user_id: int, file_id: int) -> bool:
        """Replace with database permission check."""
        return True
