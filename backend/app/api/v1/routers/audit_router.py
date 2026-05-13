from fastapi import APIRouter

from app.utils.response import ok

router = APIRouter()


@router.get("")
def list_audit_logs():
    return ok("Audit log list draft", {"logs": []})


@router.get("/file/{file_id}")
def file_audit_logs(file_id: int):
    return ok("File audit logs draft", {"file_id": file_id, "logs": []})


@router.post("/verify-chain")
def verify_chain():
    return ok("Audit chain verification draft", {"status": "VALID"})
