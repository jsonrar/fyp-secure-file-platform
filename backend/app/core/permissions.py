from enum import Enum


class SystemRole(str, Enum):
    USER = "USER"
    ADMIN = "ADMIN"
    RECOVERY_OFFICER = "RECOVERY_OFFICER"


class FilePermission(str, Enum):
    OWNER = "OWNER"
    VIEW = "VIEW"
    DOWNLOAD = "DOWNLOAD"
    SHARE = "SHARE"
    REVOKE = "REVOKE"
    MANAGE = "MANAGE"
