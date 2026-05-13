from app.core.security import hash_password, verify_password
from app.services.crypto_service import CryptoService


class AuthService:
    def __init__(self):
        self.crypto = CryptoService()

    def register_user_draft(self, username: str, email: str, password: str) -> dict:
        """Draft registration flow.

        Real implementation should insert user and public key into database.
        Private key should be returned once for the user to download safely.
        """
        private_key_pem, public_key_pem = self.crypto.generate_rsa_key_pair()
        return {
            "username": username,
            "email": email,
            "password_hash_preview": hash_password(password),
            "public_key_pem": public_key_pem,
            "private_key_pem": private_key_pem,
        }

    def verify_login_draft(self, password: str, password_hash_value: str) -> bool:
        return verify_password(password, password_hash_value)
