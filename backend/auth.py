import hashlib
import hmac
import json
import os
import secrets
import threading
import uuid
from datetime import UTC, datetime
from typing import Any, Dict, List, Optional, Protocol

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, EmailStr


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserPublic(BaseModel):
    id: str
    email: EmailStr
    created_at: datetime


class UsersDB:
    """
    Minimal JSON-file-based user storage with salted PBKDF2-HMAC password hashing.
    Thread-safe for single-process concurrency via a lock.
    Serves as a fallback when Firebase configuration is missing.
    """
    def __init__(self, path: str = "users_db.json") -> None:
        self.path = path
        self._lock = threading.Lock()
        if not os.path.exists(self.path):
            with open(self.path, "w", encoding="utf-8") as f:
                json.dump({"users": []}, f)

    def _load(self) -> Dict[str, Any]:
        with self._lock:
            with open(self.path, "r", encoding="utf-8") as f:
                return json.load(f)

    def _save(self, data: Dict[str, Any]) -> None:
        with self._lock:
            with open(self.path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

    def find_by_email(self, email: str) -> Optional[dict]:
        data = self._load()
        for u in data.get("users", []):
            if u["email"].lower() == email.lower():
                return u
        return None

    def find_by_id(self, user_id: str) -> Optional[dict]:
        data = self._load()
        for u in data.get("users", []):
            if u["id"] == user_id:
                return u
        return None

    @staticmethod
    def _hash_password(password: str, salt: str) -> str:
        # PBKDF2-HMAC with SHA256
        dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 100_000)
        return dk.hex()

    def verify_password(self, password: str, user: dict) -> bool:
        user_pw_hashed: str = user.get("password_hash", "")
        entered_pw_hash = self._hash_password(password, user_pw_hashed)
        print(f"Verifying password: entered hash {entered_pw_hash}, stored hash {user_pw_hashed}")
        return hmac.compare_digest(user_pw_hashed, entered_pw_hash)

    def create_user(self, email: str, password: str) -> dict:
        if self.find_by_email(email):
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
        data = self._load()
        data.setdefault("users", []).append(user)
        self._save(data)
        return user

    def clear_all_users(self) -> List[dict]:
        data = self._load()
        users = data.get("users", [])
        print("Clearing all users. User info:")
        for user in users:
            print(user)
        data["users"] = []
        self._save(data)
        return users  # type: ignore[return-value]


class UserRepoProtocol(Protocol):
    def find_by_email(self, email: str) -> Optional[dict]: ...
    def find_by_id(self, user_id: str) -> Optional[dict]: ...
    def create_user(self, email: str, password: str) -> dict: ...
    def verify_password(self, password: str, user: dict) -> bool: ...
    def clear_all_users(self) -> List[dict]: ...


# --- Firebase-backed repository (preferred) ---------------------------------
try:
    from backend.db.database import Database  # type: ignore
    from backend.db.firebase_users_db import FirebaseUsersDB  # type: ignore
except Exception:  # pragma: no cover - import errors just disable firebase usage
    FirebaseUsersDB = None  # type: ignore
    Database = None  # type: ignore


def create_user_repo(shared_db: 'Database | None' = None) -> UserRepoProtocol:  # type: ignore[name-defined]
    """Factory for a user repository.

    If a shared Database instance is provided and FirebaseUsersDB is importable, returns a FirebaseUsersDB.
    Otherwise returns a JSON UsersDB.
    No direct environment access here (env already validated in config module / Database init).
    """
    if FirebaseUsersDB and shared_db and Database and isinstance(shared_db, Database):  # type: ignore[arg-type]
        try:
            return FirebaseUsersDB(shared_db)  # type: ignore[return-value]
        except Exception as e:  # pragma: no cover
            print(f"Firebase users DB init failed, falling back to JSON store: {e}")
    return UsersDB()


# Lazy user repository (set during app lifespan in main). Avoid duplicate init.
_user_repo: Optional[UserRepoProtocol] = None  # type: ignore


def set_user_repo(repo: UserRepoProtocol) -> None:
    global _user_repo
    _user_repo = repo


router = APIRouter(tags=["auth"])


def get_user_repo() -> UserRepoProtocol:
    """FastAPI dependency to get current user repository (JSON or Firebase).
    Falls back to a local UsersDB if lifespan didn't set one (e.g. in unit tests)."""
    global _user_repo
    if _user_repo is None:  # fallback lazy init
        _user_repo = create_user_repo()
    return _user_repo


def get_current_user(request: Request, repo=Depends(get_user_repo)) -> dict:
    user_id = request.session.get("user_id")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    user = repo.find_by_id(user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user


@router.post("/register", response_model=UserPublic, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, repo=Depends(get_user_repo)):
    email = str(payload.email)
    existing = repo.find_by_email(email)
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User already exists")
    try:
        user = repo.create_user(email, payload.password)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    return UserPublic(
        id=user["id"],
        email=user["email"],
        created_at=datetime.fromisoformat(user["created_at"]),
    )


@router.post("/login", response_model=UserPublic)
def login(payload: LoginRequest, request: Request, repo=Depends(get_user_repo)):
    email = str(payload.email)
    user = repo.find_by_email(email)
    if not user or not repo.verify_password(payload.password, user):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid credentials")
    request.session["user_id"] = user["id"]
    return UserPublic(
        id=user["id"],
        email=user["email"],
        created_at=datetime.fromisoformat(user["created_at"]),
    )


@router.post("/logout")
def logout(request: Request):
    request.session.clear()
    return {"message": "Logged out"}


@router.get("/me", response_model=UserPublic)
def me(user: dict = Depends(get_current_user)):
    return UserPublic(
        id=user["id"],
        email=user["email"],
        created_at=datetime.fromisoformat(user["created_at"]),
    )


@router.post("/debug/clear_users")
def clear_users_debug(repo=Depends(get_user_repo)):
    users = repo.clear_all_users()
    return {"message": f"All users have been removed (debug route). {len(users)} users deleted."}
