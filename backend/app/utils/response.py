"""Compatibility exports; new HTTP code belongs in :mod:`app.api.responses`."""

from app.api.responses import ApiResponse, error, fail, ok

__all__ = ["ApiResponse", "error", "fail", "ok"]
