from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse

from app.api.dependencies import get_current_actor, get_request_context, get_shelf_service
from app.api.responses import AUTH_NO_STORE_HEADERS, ApiSuccessResponse, ok
from app.domain.auth import ActorContext, RequestContext
from app.schemas.shelf_schema import (
    ShelfCreate,
    ShelfDeleteOut,
    ShelfListOut,
    ShelfOut,
    ShelfRename,
)
from app.services.shelf_service import ShelfService

router = APIRouter()

ActorDependency = Annotated[ActorContext, Depends(get_current_actor)]
RequestContextDependency = Annotated[RequestContext, Depends(get_request_context)]
ShelfServiceDependency = Annotated[ShelfService, Depends(get_shelf_service)]


@router.get("", response_model=ApiSuccessResponse[ShelfListOut])
def list_shelves(
    actor: ActorDependency,
    service: ShelfServiceDependency,
) -> JSONResponse:
    return ok(
        message="Shelves retrieved",
        data=service.list_shelves(actor=actor),
        headers=AUTH_NO_STORE_HEADERS,
    )


@router.post(
    "",
    response_model=ApiSuccessResponse[ShelfOut],
    status_code=status.HTTP_201_CREATED,
)
def create_shelf(
    payload: ShelfCreate,
    actor: ActorDependency,
    context: RequestContextDependency,
    service: ShelfServiceDependency,
) -> JSONResponse:
    result = service.create(actor=actor, name=payload.name, context=context)
    return ok(
        message="Shelf created",
        data=result,
        code=status.HTTP_201_CREATED,
        headers=AUTH_NO_STORE_HEADERS,
    )


@router.post("/{shelf_id}/rename", response_model=ApiSuccessResponse[ShelfOut])
def rename_shelf(
    shelf_id: UUID,
    payload: ShelfRename,
    actor: ActorDependency,
    context: RequestContextDependency,
    service: ShelfServiceDependency,
) -> JSONResponse:
    result = service.rename(
        actor=actor,
        shelf_id=shelf_id,
        name=payload.name,
        context=context,
    )
    return ok(
        message="Shelf renamed",
        data=result,
        headers=AUTH_NO_STORE_HEADERS,
    )


@router.post("/{shelf_id}/delete", response_model=ApiSuccessResponse[ShelfDeleteOut])
def delete_shelf(
    shelf_id: UUID,
    actor: ActorDependency,
    context: RequestContextDependency,
    service: ShelfServiceDependency,
) -> JSONResponse:
    """Remove a shelf. The files on it return to the root and none of them are deleted."""
    result = service.delete(actor=actor, shelf_id=shelf_id, context=context)
    return ok(
        message="Shelf deleted; its files returned to the root",
        data=result,
        headers=AUTH_NO_STORE_HEADERS,
    )
