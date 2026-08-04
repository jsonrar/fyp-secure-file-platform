from enum import StrEnum


class SystemRole(StrEnum):
    USER = "USER"
    ADMIN = "ADMIN"
    RECOVERY_OFFICER = "RECOVERY_OFFICER"


class UserStatus(StrEnum):
    ACTIVE = "ACTIVE"
    DISABLED = "DISABLED"
    DELETED = "DELETED"


class SessionStatus(StrEnum):
    ACTIVE = "ACTIVE"
    EXPIRED = "EXPIRED"
    REVOKED = "REVOKED"


class LoginThrottleScope(StrEnum):
    ACCOUNT = "ACCOUNT"
    IP = "IP"
    REAUTH_ACCOUNT = "REAUTH_ACCOUNT"
    REAUTH_IP = "REAUTH_IP"
    REGISTRATION_IP = "REGISTRATION_IP"


class FileCapability(StrEnum):
    VIEW = "VIEW"
    DOWNLOAD = "DOWNLOAD"
    SHARE = "SHARE"
    REVOKE = "REVOKE"
    MANAGE = "MANAGE"
