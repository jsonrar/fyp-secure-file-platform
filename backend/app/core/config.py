from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str = "Secure File Encryption Platform"
    APP_ENV: str = "development"
    APP_DEBUG: bool = True
    API_PREFIX: str = "/api/v1"
    SECRET_KEY: str = "change-this-secret-key"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 120

    DB_HOST: str = "localhost"
    DB_PORT: int = 3306
    DB_USER: str = "fyp_user"
    DB_PASSWORD: str = "fyp_password"
    DB_NAME: str = "fyp_secure_file_platform"

    ENCRYPTED_FILE_DIR: str = "backend/encrypted_files"
    TEMP_FILE_DIR: str = "backend/temp_files"
    RECOVERY_PUBLIC_KEY_PATH: str = "recovery_keys/recovery_public.pem"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    @property
    def DATABASE_URL(self) -> str:
        return (
            f"mysql+pymysql://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}?charset=utf8mb4"
        )


settings = Settings()
