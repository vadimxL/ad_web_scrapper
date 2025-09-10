import os
import json
import uuid
import hashlib
import secrets
import threading
from datetime import datetime
from typing import Optional, Dict, Any

from fastapi import APIRouter, HTTPException, Request, status, Depends
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
    """
    def __init__(self, path: str = "users_db.json"):
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
        return self._hash_password(password, user["salt"]) == user["password_hash"]

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
            "created_at": datetime.utcnow().isoformat()
        }
        data = self._load()
        data.setdefault("users", []).append(user)
        self._save(data)
        return user


db = UsersDB()
router = APIRouter(tags=["auth"])


def get_current_user(request: Request) -> dict:
    user_id = request.session.get("user_id")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    user = db.find_by_id(user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user


@router.post("/register", response_model=UserPublic, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest):
    existing = db.find_by_email(payload.email)
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User already exists")
    try:
        user = db.create_user(payload.email, payload.password)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    return UserPublic(
        id=user["id"],
        email=user["email"],
        created_at=datetime.fromisoformat(user["created_at"]),
    )


@router.post("/login", response_model=UserPublic)
def login(payload: LoginRequest, request: Request):
    user = db.find_by_email(payload.email)
    if not user or not db.verify_password(payload.password, user):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid credentials")
    # Establish session
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
