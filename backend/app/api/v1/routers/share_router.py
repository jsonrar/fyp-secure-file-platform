from uuid import UUID

from fastapi import APIRouter

from app.api.dependencies import reject_unimplemented_api
from app.schemas.share_schema import RevokeAccessRequest, ShareFileRequest

router = APIRouter()


@router.post("/{file_id}/share")
def share_file(file_id: UUID, payload: ShareFileRequest) -> None:
    reject_unimplemented_api()


@router.get("/{file_id}/shared-users")
def shared_users(file_id: UUID) -> None:
    reject_unimplemented_api()


@router.post("/{file_id}/revoke")
def revoke_access(file_id: UUID, payload: RevokeAccessRequest) -> None:
    reject_unimplemented_api()
