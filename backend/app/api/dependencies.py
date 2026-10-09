from collections.abc import Generator
from typing import Annotated

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.domain.auth import ActorContext, RequestContext
from app.domain.enums import SystemRole
from app.domain.errors import AuthenticationError, AuthorizationError
from app.services.account_deletion_service import AccountDeletionService
from app.services.account_notice_service import AccountNoticeService
from app.services.admin_service import AdminService
from app.services.audit_log_service import AuditLogService
from app.services.audit_query_service import AuditQueryService
from app.services.auth_service import AuthService
from app.services.avatar_service import AvatarService
from app.services.avatar_storage_service import AvatarStorageService
from app.services.file_service import FileService
from app.services.file_storage_service import FileStorageService
from app.services.integrity_service import IntegrityService
from app.services.key_service import KeyService
from app.services.recovery_service import RecoveryService
from app.services.security_agent_service import SecurityAgentService
from app.services.share_notification_service import ShareNotificationService
from app.services.sharing_service import SharingService

_bearer_scheme = HTTPBearer(auto_error=False)


def get_request_context(request: Request) -> RequestContext:
    client_host = request.client.host if request.client is not None else None
    user_agent = request.headers.get("user-agent")
    return RequestContext(
        ip_address=client_host[:45] if client_host else None,
        user_agent=user_agent[:1024] if user_agent else None,
    )


def get_settings(request: Request) -> Settings:
    return request.app.state.settings


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


def get_key_service(
    request: Request,
    db: Annotated[Session, Depends(get_request_db)],
) -> KeyService:
    return KeyService(db=db, settings=request.app.state.settings)


def get_file_service(
    request: Request,
    db: Annotated[Session, Depends(get_request_db)],
) -> FileService:
    settings = request.app.state.settings
    return FileService(
        db=db,
        settings=settings,
        storage=FileStorageService(settings=settings),
        audit_service=AuditLogService(db),
    )


def get_account_deletion_service(
    request: Request,
    db: Annotated[Session, Depends(get_request_db)],
) -> AccountDeletionService:
    settings = request.app.state.settings
    return AccountDeletionService(
        db=db,
        passwords=request.app.state.password_manager,
        storage=FileStorageService(settings=settings),
        reauthentication=AuthService(
            db=db,
            settings=settings,
            passwords=request.app.state.password_manager,
        ),
        avatar_storage=AvatarStorageService(settings=settings),
        audit_service=AuditLogService(db),
    )


def get_avatar_service(
    request: Request,
    db: Annotated[Session, Depends(get_request_db)],
) -> AvatarService:
    settings = request.app.state.settings
    return AvatarService(
        db=db,
        settings=settings,
        storage=AvatarStorageService(settings=settings),
        audit_service=AuditLogService(db),
    )


def get_sharing_service(
    request: Request,
    db: Annotated[Session, Depends(get_request_db)],
) -> SharingService:
    settings = request.app.state.settings
    return SharingService(
        db=db,
        notifier=ShareNotificationService(settings=settings),
    )


def get_recovery_service(
    db: Annotated[Session, Depends(get_request_db)],
) -> RecoveryService:
    return RecoveryService(db=db)


def get_audit_query_service(
    db: Annotated[Session, Depends(get_request_db)],
) -> AuditQueryService:
    return AuditQueryService(db=db)


def get_admin_service(
    request: Request,
    db: Annotated[Session, Depends(get_request_db)],
) -> AdminService:
    settings = request.app.state.settings
    audit = AuditLogService(db)
    return AdminService(
        db=db,
        audit_service=audit,
        notices=AccountNoticeService(settings=settings),
        integrity_service=IntegrityService(
            db=db,
            settings=settings,
            storage=FileStorageService(settings=settings),
            audit_service=audit,
        ),
    )


def get_security_agent_service(
    db: Annotated[Session, Depends(get_request_db)],
) -> SecurityAgentService:
    return SecurityAgentService(db=db)


def get_current_actor(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer_scheme)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
    db: Annotated[Session, Depends(get_request_db)],
) -> ActorContext:
    if credentials is None or not credentials.credentials:
        raise AuthenticationError()
    actor = auth_service.authenticate_access_token(credentials.credentials)
    # Authentication only reads. Ending that transaction returns the connection to the pool
    # before the endpoint runs, instead of holding it for the whole request: an async handler
    # that then waited on the thread pool kept it while every thread waited for a connection,
    # and at 100 concurrent users the pool timed out (#140).
    db.rollback()
    return actor


def require_admin(
    actor: Annotated[ActorContext, Depends(get_current_actor)],
) -> ActorContext:
    if actor.role is not SystemRole.ADMIN:
        raise AuthorizationError()
    return actor


def require_recovery_reviewer(
    actor: Annotated[ActorContext, Depends(get_current_actor)],
) -> ActorContext:
    if actor.role not in {SystemRole.ADMIN, SystemRole.RECOVERY_OFFICER}:
        raise AuthorizationError()
    return actor
