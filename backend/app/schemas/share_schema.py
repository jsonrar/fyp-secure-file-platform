from pydantic import BaseModel


class ShareFileRequest(BaseModel):
    target_user_id: int
    owner_private_key_pem: str
    can_download: bool = True
    can_share: bool = False


class RevokeAccessRequest(BaseModel):
    target_user_id: int
