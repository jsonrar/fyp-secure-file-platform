from uuid import UUID

from fastapi import APIRouter

from app.api.dependencies import reject_unimplemented_api

router = APIRouter()


@router.get("")
def list_audit_logs() -> None:
    reject_unimplemented_api()


@router.get("/file/{file_id}")
def file_audit_logs(file_id: UUID) -> None:
    reject_unimplemented_api()


@router.post("/verify-chain")
def verify_chain() -> None:
    reject_unimplemented_api()
