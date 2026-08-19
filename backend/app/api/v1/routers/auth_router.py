from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse

from app.api.dependencies import get_auth_service, get_current_actor, get_request_context
from app.api.responses import AUTH_NO_STORE_HEADERS, ApiSuccessResponse, ok
from app.domain.auth import ActorContext, RequestContext
from app.schemas.auth_schema import (
    AuthMeResponse,
    AuthRefreshRequest,
    AuthRefreshResponse,
    AuthSessionListResponse,
    AuthSessionResponse,
    AuthSessionRevokeResponse,
    AuthUserResponse,
    ChangePasswordRequest,
    ChangePasswordResponse,
    UserLoginRequest,
    UserLoginResponse,
    UserLogoutAllResponse,
    UserLogoutResponse,
    UserRegisterRequest,
    UserRegisterResponse,
)
from app.services.auth_service import AuthService

router = APIRouter()

AuthServiceDependency = Annotated[AuthService, Depends(get_auth_service)]
ActorDependency = Annotated[ActorContext, Depends(get_current_actor)]
RequestContextDependency = Annotated[RequestContext, Depends(get_request_context)]


@router.post(
    "/register",
    response_model=ApiSuccessResponse[UserRegisterResponse],
    status_code=status.HTTP_201_CREATED,
)
def register(
    payload: UserRegisterRequest,
    auth_service: AuthServiceDependency,
    context: RequestContextDependency,
) -> JSONResponse:
    result = auth_service.register(
        username=payload.username,
        password=payload.password,
        context=context,
    )
    response_data = UserRegisterResponse.model_validate(result)
    return ok(
        message="Registration successful",
        data=response_data,
        code=status.HTTP_201_CREATED,
        headers=AUTH_NO_STORE_HEADERS,
    )


@router.post("/login", response_model=ApiSuccessResponse[UserLoginResponse])
def login(
    payload: UserLoginRequest,
    auth_service: AuthServiceDependency,
    context: RequestContextDependency,
) -> JSONResponse:
    result = auth_service.login(
        username=payload.username,
        password=payload.password,
        context=context,
    )
    response_data = UserLoginResponse(
        user=AuthUserResponse.model_validate(result.user),
        access_token=result.tokens.access_token,
        refresh_token=result.tokens.refresh_token,
        token_type=result.tokens.token_type,
        access_expires_at=result.tokens.access_expires_at,
        refresh_expires_at=result.tokens.refresh_expires_at,
        session_id=result.tokens.session_id,
    )
    return ok(
        message="Login successful",
        data=response_data,
        headers=AUTH_NO_STORE_HEADERS,
    )


@router.post("/refresh", response_model=ApiSuccessResponse[AuthRefreshResponse])
def refresh(
    payload: AuthRefreshRequest,
    auth_service: AuthServiceDependency,
    context: RequestContextDependency,
) -> JSONResponse:
    result = auth_service.refresh(refresh_token=payload.refresh_token, context=context)
    response_data = AuthRefreshResponse.model_validate(result.tokens)
    return ok(
        message="Session refreshed",
        data=response_data,
        headers=AUTH_NO_STORE_HEADERS,
    )


@router.get("/me", response_model=ApiSuccessResponse[AuthMeResponse])
def me(
    actor: ActorDependency,
    auth_service: AuthServiceDependency,
) -> JSONResponse:
    user = auth_service.get_me(actor=actor)
    response_data = AuthMeResponse(user=AuthUserResponse.model_validate(user))
    return ok(
        message="Current account retrieved",
        data=response_data,
        headers=AUTH_NO_STORE_HEADERS,
    )


@router.post("/logout", response_model=ApiSuccessResponse[UserLogoutResponse])
def logout(
    actor: ActorDependency,
    context: RequestContextDependency,
    auth_service: AuthServiceDependency,
) -> JSONResponse:
    auth_service.logout(actor=actor, context=context)
    return ok(
        message="Logout successful",
        data=UserLogoutResponse(),
        headers=AUTH_NO_STORE_HEADERS,
    )


@router.post("/logout-all", response_model=ApiSuccessResponse[UserLogoutAllResponse])
def logout_all(
    actor: ActorDependency,
    context: RequestContextDependency,
    auth_service: AuthServiceDependency,
) -> JSONResponse:
    revoked_sessions = auth_service.logout_all(actor=actor, context=context)
    response_data = UserLogoutAllResponse(revoked_sessions=revoked_sessions)
    return ok(
        message="All sessions logged out",
        data=response_data,
        headers=AUTH_NO_STORE_HEADERS,
    )


@router.post(
    "/change-password",
    response_model=ApiSuccessResponse[ChangePasswordResponse],
)
def change_password(
    payload: ChangePasswordRequest,
    actor: ActorDependency,
    context: RequestContextDependency,
    auth_service: AuthServiceDependency,
) -> JSONResponse:
    revoked_sessions = auth_service.change_password(
        actor=actor,
        current_password=payload.current_password,
        new_password=payload.new_password,
        context=context,
    )
    response_data = ChangePasswordResponse(revoked_sessions=revoked_sessions)
    return ok(
        message="Password changed; please log in again",
        data=response_data,
        headers=AUTH_NO_STORE_HEADERS,
    )


@router.get("/sessions", response_model=ApiSuccessResponse[AuthSessionListResponse])
def list_sessions(
    actor: ActorDependency,
    auth_service: AuthServiceDependency,
) -> JSONResponse:
    sessions = auth_service.list_sessions(actor=actor)
    response_data = AuthSessionListResponse(
        sessions=[AuthSessionResponse.model_validate(session) for session in sessions]
    )
    return ok(
        message="Sessions retrieved",
        data=response_data,
        headers=AUTH_NO_STORE_HEADERS,
    )


@router.post(
    "/sessions/{session_id}/revoke",
    response_model=ApiSuccessResponse[AuthSessionRevokeResponse],
)
def revoke_session(
    session_id: UUID,
    actor: ActorDependency,
    context: RequestContextDependency,
    auth_service: AuthServiceDependency,
) -> JSONResponse:
    auth_service.revoke_session(actor=actor, session_id=session_id, context=context)
    response_data = AuthSessionRevokeResponse(session_id=session_id)
    return ok(
        message="Session revoked",
        data=response_data,
        headers=AUTH_NO_STORE_HEADERS,
    )
