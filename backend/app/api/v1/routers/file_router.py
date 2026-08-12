from uuid import UUID

from fastapi import APIRouter, File, UploadFile

from app.api.dependencies import reject_unimplemented_api

router = APIRouter()


@router.post("/upload")
async def upload_file(file: UploadFile = File(...)) -> None:
    reject_unimplemented_api()


@router.get("")
def list_files() -> None:
    reject_unimplemented_api()


@router.get("/{file_id}")
def get_file(file_id: UUID) -> None:
    reject_unimplemented_api()


@router.post("/{file_id}/download")
def download_file(file_id: UUID) -> None:
    reject_unimplemented_api()


@router.post("/{file_id}/delete")
def delete_file(file_id: UUID) -> None:
    reject_unimplemented_api()


@router.post("/{file_id}/integrity-check")
def integrity_check(file_id: UUID) -> None:
    reject_unimplemented_api()
