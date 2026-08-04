from fastapi import APIRouter, Depends

from app.api.dependencies import reject_unimplemented_api
from app.api.v1.routers import (
    admin_router,
    audit_router,
    auth_router,
    file_router,
    recovery_router,
    share_router,
)

api_router = APIRouter()
draft_only = [Depends(reject_unimplemented_api)]

api_router.include_router(
    auth_router.router,
    prefix="/auth",
    tags=["Auth"],
)
api_router.include_router(
    file_router.router,
    prefix="/files",
    tags=["Files"],
    dependencies=draft_only,
)
api_router.include_router(
    share_router.router,
    prefix="/files",
    tags=["Sharing"],
    dependencies=draft_only,
)
api_router.include_router(
    audit_router.router,
    prefix="/audit-logs",
    tags=["Audit Logs"],
    dependencies=draft_only,
)
api_router.include_router(
    recovery_router.router,
    prefix="/recovery",
    tags=["Recovery"],
    dependencies=draft_only,
)
api_router.include_router(
    admin_router.router,
    prefix="/admin",
    tags=["Admin"],
    dependencies=draft_only,
)
