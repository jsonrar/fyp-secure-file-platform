from collections.abc import Generator
from typing import Annotated, NoReturn

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.domain.auth import ActorContext, RequestContext
from app.domain.errors import AuthenticationError, FeatureNotImplementedError
from app.services.auth_service import AuthService

_bearer_scheme = HTTPBearer(auto_error=False)


def reject_unimplemented_api() -> NoReturn:
    """Fail closed while a draft router has no authenticated implementation."""
    raise FeatureNotImplementedError()


def get_request_context(request: Request) -> RequestContext:
    client_host = request.client.host if request.client is not None else None
    user_agent = request.headers.get("user-agent")
    return RequestContext(
        ip_address=client_host[:45] if client_host else None,
        user_agent=user_agent[:1024] if user_agent else None,
    )


def get_request_db(request: Request) -> Generator[Session, None, None]:
    """Yield a session from the engine owned by this FastAPI application instance."""
    db = request.app.state.db_session_factory()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def get_auth_service(
    request: Request,
    db: Annotated[Session, Depends(get_request_db)],
) -> AuthService:
    return AuthService(
        db=db,
        settings=request.app.state.settings,
        passwords=request.app.state.password_manager,
    )


def get_current_actor(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer_scheme)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> ActorContext:
    if credentials is None or not credentials.credentials:
        raise AuthenticationError()
    return auth_service.authenticate_access_token(credentials.credentials)
