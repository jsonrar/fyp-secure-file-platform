from uuid import UUID

from fastapi import APIRouter

from app.api.dependencies import reject_unimplemented_api
from app.schemas.recovery_schema import RecoveryExecuteRequest, RecoveryRequestCreate

router = APIRouter()


@router.post("/request")
def create_recovery_request(payload: RecoveryRequestCreate) -> None:
    reject_unimplemented_api()


@router.post("/{request_id}/approve")
def approve_recovery(request_id: UUID) -> None:
    reject_unimplemented_api()


@router.post("/{request_id}/execute")
def execute_recovery(
    request_id: UUID,
    payload: RecoveryExecuteRequest,
) -> None:
    reject_unimplemented_api()


@router.get("/requests")
def list_recovery_requests() -> None:
    reject_unimplemented_api()
