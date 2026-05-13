from fastapi import APIRouter

from app.schemas.auth_schema import LoginRequest, RegisterRequest
from app.services.auth_service import AuthService
from app.utils.response import ok

router = APIRouter()


@router.post("/register")
def register(payload: RegisterRequest):
    result = AuthService().register_user_draft(payload.username, payload.email, payload.password)
    return ok("Registration draft completed. Store public key in DB and return private key once.", result)


@router.post("/login")
def login(payload: LoginRequest):
    # Replace with real database user lookup and session/JWT creation.
    return ok("Login draft completed", {"access_token": "demo-token", "token_type": "bearer"})


@router.post("/logout")
def logout():
    return ok("Logout draft completed")


@router.get("/me")
def me():
    return ok("Current user draft", {"user_id": 1, "username": "demo_user"})
