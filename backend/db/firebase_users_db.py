import hashlib
import secrets
import uuid
from datetime import UTC, datetime
from typing import Optional

from backend.db.database import Database


class FirebaseUsersDB:
    """Firebase-backed users repository.

    Data layout (Realtime Database):
      /users/{user_id} -> {id,email,password_hash,salt,created_at}
      /users_emails/{email_hash} -> user_id   (email uniqueness + lookup index)

    email_hash = sha256(lowercased_email).hexdigest() to avoid illegal Firebase path characters
    ('.', '#', '$', '[', ']', '?'). Direct email strings are not used as keys.
    """
    def __init__(self, database: Database, users_path: str = "users", email_index_suffix: str = "_emails"):
        self._db = database
        self._users_path = users_path
        self._emails_index_path = f"{users_path}{email_index_suffix}"  # e.g. users_emails

    # ---- helpers ----
    @staticmethod
    def _hash_password(password: str, salt: str) -> str:
        dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 100_000)
        return dk.hex()

    @staticmethod
    def _email_index_key(lower_email: str) -> str:
        return hashlib.sha256(lower_email.encode("utf-8")).hexdigest()

    def verify_password(self, password: str, user: dict) -> bool:
        return self._hash_password(password, user["salt"]) == user["password_hash"]

    # ---- lookups ----
    def find_by_id(self, user_id: str) -> Optional[dict]:
        ref = self._db.reference(f"{self._users_path}/{user_id}")
        return ref.get()

    def find_by_email(self, email: str) -> Optional[dict]:
        lower_email = email.lower()
        key = self._email_index_key(lower_email)
        idx_ref = self._db.reference(f"{self._emails_index_path}/{key}")
        user_id = idx_ref.get()
        if not user_id:
            return None
        return self.find_by_id(user_id)

    # ---- mutation ----
    def create_user(self, email: str, password: str) -> dict:
        lower_email = email.lower()
        key = self._email_index_key(lower_email)
        idx_ref = self._db.reference(f"{self._emails_index_path}/{key}")
        if idx_ref.get():
            raise ValueError("User already exists")
        salt = secrets.token_hex(16)
        password_hash = self._hash_password(password, salt)
        user = {
            "id": uuid.uuid4().hex,
            "email": email,
            "password_hash": password_hash,
            "salt": salt,
            "created_at": datetime.now(UTC).isoformat()
        }
        self._db.reference(f"{self._users_path}/{user['id']}").set(user)
        idx_ref.set(user['id'])
        return user

    def clear_all_users(self):
        users_ref = self._db.reference(self._users_path)
        users = users_ref.get() or {}
        users_list = list(users.values()) if isinstance(users, dict) else []
        users_ref.delete()
        self._db.reference(self._emails_index_path).delete()
        return users_list
