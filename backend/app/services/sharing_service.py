class SharingService:
    def share_file_draft(self, file_id: int, owner_user_id: int, target_user_id: int) -> dict:
        return {
            "file_id": file_id,
            "owner_user_id": owner_user_id,
            "target_user_id": target_user_id,
            "flow": "unwrap owner AES file key, then wrap it using target user's public key",
        }

    def revoke_access_draft(self, file_id: int, target_user_id: int) -> dict:
        return {
            "file_id": file_id,
            "target_user_id": target_user_id,
            "result": "mark access grant and key wrapping as revoked",
        }
