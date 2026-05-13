from fastapi import APIRouter

from app.utils.response import ok

router = APIRouter()


@router.get("/users")
def list_users():
    return ok("Admin user list draft", {"users": []})


@router.get("/files")
def list_all_files():
    return ok("Admin file list draft", {"files": []})
