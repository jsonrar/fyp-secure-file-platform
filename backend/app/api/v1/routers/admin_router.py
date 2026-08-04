from fastapi import APIRouter

from app.api.dependencies import reject_unimplemented_api

router = APIRouter()


@router.get("/users")
def list_users() -> None:
    reject_unimplemented_api()


@router.get("/files")
def list_all_files() -> None:
    reject_unimplemented_api()
