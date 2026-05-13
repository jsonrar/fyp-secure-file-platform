from fastapi import APIRouter

from app.schemas.share_schema import RevokeAccessRequest, ShareFileRequest
from app.services.sharing_service import SharingService
from app.utils.response import ok

router = APIRouter()


@router.post("/{file_id}/share")
def share_file(file_id: int, payload: ShareFileRequest):
    result = SharingService().share_file_draft(file_id, owner_user_id=1, target_user_id=payload.target_user_id)
    return ok("Share draft completed", result)


@router.get("/{file_id}/shared-users")
def shared_users(file_id: int):
    return ok("Shared users draft", {"file_id": file_id, "shared_users": []})


@router.post("/{file_id}/revoke")
def revoke_access(file_id: int, payload: RevokeAccessRequest):
    result = SharingService().revoke_access_draft(file_id, payload.target_user_id)
    return ok("Revoke draft completed", result)
