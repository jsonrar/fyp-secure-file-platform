from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.routers import auth_router, file_router, share_router, audit_router, recovery_router, admin_router
from app.core.config import settings

app = FastAPI(
    title=settings.APP_NAME,
    version="0.1.0",
    description="Secure File Encryption and Sharing Platform API",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router.router, prefix=f"{settings.API_PREFIX}/auth", tags=["Auth"])
app.include_router(file_router.router, prefix=f"{settings.API_PREFIX}/files", tags=["Files"])
app.include_router(share_router.router, prefix=f"{settings.API_PREFIX}/files", tags=["Sharing"])
app.include_router(audit_router.router, prefix=f"{settings.API_PREFIX}/audit-logs", tags=["Audit Logs"])
app.include_router(recovery_router.router, prefix=f"{settings.API_PREFIX}/recovery", tags=["Recovery"])
app.include_router(admin_router.router, prefix=f"{settings.API_PREFIX}/admin", tags=["Admin"])


@app.get("/")
def root():
    return {
        "success": True,
        "message": "Secure File Encryption Platform API is running",
        "docs": "/docs",
    }
