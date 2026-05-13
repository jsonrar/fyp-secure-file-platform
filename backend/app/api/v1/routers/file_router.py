from fastapi import APIRouter, File, UploadFile

from app.services.file_service import FileService
from app.utils.response import ok

router = APIRouter()


@router.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    content = await file.read()
    result = FileService().encrypt_uploaded_bytes_draft(file.filename or "uploaded_file", content)
    return ok("File encrypted and stored in draft flow", result)


@router.get("")
def list_files():
    return ok("File list draft", {"files": []})


@router.get("/{file_id}")
def get_file(file_id: int):
    return ok("File metadata draft", {"file_id": file_id})


@router.post("/{file_id}/download")
def download_file(file_id: int):
    return ok("Download draft. Real flow should check permission, unwrap key, decrypt, watermark, and return file.", {"file_id": file_id})


@router.delete("/{file_id}")
def delete_file(file_id: int):
    return ok("Delete draft", {"file_id": file_id})


@router.post("/{file_id}/integrity-check")
def integrity_check(file_id: int):
    return ok("Integrity check draft", {"file_id": file_id, "status": "VALID"})
