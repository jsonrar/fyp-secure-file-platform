from fastapi import APIRouter

from app.schemas.recovery_schema import RecoveryExecuteRequest, RecoveryRequestCreate
from app.services.recovery_service import RecoveryService
from app.utils.response import ok

router = APIRouter()


@router.post("/request")
def create_recovery_request(payload: RecoveryRequestCreate):
    result = RecoveryService().create_recovery_request_draft(payload.file_id, requested_by=1, reason=payload.reason)
    return ok("Recovery request draft created", result)


@router.post("/{request_id}/approve")
def approve_recovery(request_id: int):
    return ok("Recovery request approval draft", {"request_id": request_id, "status": "approved"})


@router.post("/{request_id}/execute")
def execute_recovery(request_id: int, payload: RecoveryExecuteRequest):
    return ok("Recovery execution draft", {"request_id": request_id, "status": "completed"})


@router.get("/requests")
def list_recovery_requests():
    return ok("Recovery request list draft", {"requests": []})
