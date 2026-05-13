from typing import Any


def ok(message: str = "success", data: Any = None) -> dict:
    return {
        "success": True,
        "status": "success",
        "message": message,
        "data": data,
    }


def fail(message: str = "failed", data: Any = None) -> dict:
    return {
        "success": False,
        "status": "fail",
        "message": message,
        "data": data,
    }
