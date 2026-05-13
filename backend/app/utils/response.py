from typing import Any, Optional
from fastapi.responses import JSONResponse


class ApiResponse:
    @staticmethod
    def success(
        data: Any = None,
        message: str = "Success",
        description: Optional[str] = None,
        code: int = 200
    ) -> JSONResponse:
        return JSONResponse(
            status_code=code,
            content={
                "success": True,
                "status": "success",
                "message": message,
                "data": data,
                "description": description,
                "code": code
            }
        )

    @staticmethod
    def fail(
        message: str = "Request failed",
        data: Any = None,
        description: Optional[str] = None,
        code: int = 400
    ) -> JSONResponse:
        return JSONResponse(
            status_code=code,
            content={
                "success": False,
                "status": "fail",
                "message": message,
                "data": data,
                "description": description,
                "code": code
            }
        )

    @staticmethod
    def error(
        message: str = "Internal server error",
        data: Any = None,
        description: Optional[str] = None,
        code: int = 500
    ) -> JSONResponse:
        return JSONResponse(
            status_code=code,
            content={
                "success": False,
                "status": "error",
                "message": message,
                "data": data,
                "description": description,
                "code": code
            }
        )