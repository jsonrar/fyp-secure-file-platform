from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse

from app.api.dependencies import get_admin_service, get_request_context, require_admin
from app.api.responses import AUTH_NO_STORE_HEADERS, ApiSuccessResponse, ok
from app.core.time import to_api_utc
from app.domain.auth import ActorContext, RequestContext
from app.schemas.admin_schema import (
    AdminFileListResponse,
    AdminFileOut,
    AdminIntegrityReportOut,
    AdminIntegrityScanOut,
    AdminStatsOut,
    AdminUserListResponse,
    AdminUserOut,
    AdminUserStatusResponse,
)
from app.services.admin_service import AdminService

router = APIRouter()

AdminActorDependency = Annotated[ActorContext, Depends(require_admin)]
AdminServiceDependency = Annotated[AdminService, Depends(get_admin_service)]
RequestContextDependency = Annotated[RequestContext, Depends(get_request_context)]


@router.get("/users", response_model=ApiSuccessResponse[AdminUserListResponse])
def list_users(
    actor: AdminActorDependency,
    service: AdminServiceDependency,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0, le=1_000_000)] = 0,
) -> JSONResponse:
    rows = service.list_users(actor=actor, limit=limit, offset=offset)
    data = AdminUserListResponse(
        users=[
            AdminUserOut(
                user_id=UUID(user.user_uuid),
                username=user.username,
                role=user.role,
                status=user.status,
                created_at=to_api_utc(user.created_at),
                last_login_at=to_api_utc(user.last_login_at),
            )
            for user in rows[:limit]
        ],
        limit=limit,
        offset=offset,
        has_more=len(rows) > limit,
    )
    return ok(message="Users retrieved", data=data, headers=AUTH_NO_STORE_HEADERS)


@router.get("/stats", response_model=ApiSuccessResponse[AdminStatsOut])
def platform_stats(
    actor: AdminActorDependency,
    service: AdminServiceDependency,
) -> JSONResponse:
    data = service.platform_stats(actor=actor)
    return ok(message="Platform statistics retrieved", data=data, headers=AUTH_NO_STORE_HEADERS)


# One request must not hash the whole store: a few large objects can take minutes. The batch
# size and the time budget both stop the pass; the report says how many files are left, and
# the scheduled sweep (deployment/server/mcs21-integrity-sweep.*) covers the rest.
SCAN_BATCH_FILES = 50
SCAN_BUDGET_SECONDS = 20.0


@router.get("/integrity", response_model=ApiSuccessResponse[AdminIntegrityReportOut])
def integrity_report(
    actor: AdminActorDependency,
    service: AdminServiceDependency,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> JSONResponse:
    data = service.integrity_report(actor=actor, limit=limit)
    return ok(message="Integrity report retrieved", data=data, headers=AUTH_NO_STORE_HEADERS)


@router.post("/integrity/scan", response_model=ApiSuccessResponse[AdminIntegrityScanOut])
def scan_integrity(
    actor: AdminActorDependency,
    context: RequestContextDependency,
    service: AdminServiceDependency,
) -> JSONResponse:
    data = service.scan_integrity(
        actor=actor,
        context=context,
        limit=SCAN_BATCH_FILES,
        budget_seconds=SCAN_BUDGET_SECONDS,
    )
    return ok(message="Integrity scan finished", data=data, headers=AUTH_NO_STORE_HEADERS)


@router.get("/files", response_model=ApiSuccessResponse[AdminFileListResponse])
def list_all_files(
    actor: AdminActorDependency,
    service: AdminServiceDependency,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0, le=1_000_000)] = 0,
) -> JSONResponse:
    rows = service.list_files(actor=actor, limit=limit, offset=offset)
    data = AdminFileListResponse(
        files=[
            AdminFileOut(
                file_id=UUID(file.file_uuid),
                owner_id=UUID(owner.user_uuid),
                owner_username=owner.username,
                original_filename=file.original_filename,
                mime_type=file.mime_type,
                file_size=file.file_size_bytes,
                encrypted_size=file.encrypted_size_bytes,
                status=file.status,
                created_at=to_api_utc(file.created_at),
                updated_at=to_api_utc(file.updated_at),
            )
            for file, owner in rows[:limit]
        ],
        limit=limit,
        offset=offset,
        has_more=len(rows) > limit,
    )
    return ok(message="Files retrieved", data=data, headers=AUTH_NO_STORE_HEADERS)


def _set_status(
    *,
    user_id: UUID,
    enabled: bool,
    actor: ActorContext,
    context: RequestContext,
    service: AdminService,
) -> JSONResponse:
    user, changed, revoked = service.set_user_enabled(
        actor=actor,
        user_id=user_id,
        enabled=enabled,
        context=context,
    )
    data = AdminUserStatusResponse(
        user_id=user_id,
        status=user.status,
        changed=changed,
        revoked_sessions=revoked,
    )
    return ok(message="User status updated", data=data, headers=AUTH_NO_STORE_HEADERS)


@router.post(
    "/users/{user_id}/disable",
    response_model=ApiSuccessResponse[AdminUserStatusResponse],
)
def disable_user(
    user_id: UUID,
    actor: AdminActorDependency,
    context: RequestContextDependency,
    service: AdminServiceDependency,
) -> JSONResponse:
    return _set_status(
        user_id=user_id,
        enabled=False,
        actor=actor,
        context=context,
        service=service,
    )


@router.post(
    "/users/{user_id}/enable",
    response_model=ApiSuccessResponse[AdminUserStatusResponse],
)
def enable_user(
    user_id: UUID,
    actor: AdminActorDependency,
    context: RequestContextDependency,
    service: AdminServiceDependency,
) -> JSONResponse:
    return _set_status(
        user_id=user_id,
        enabled=True,
        actor=actor,
        context=context,
        service=service,
    )
