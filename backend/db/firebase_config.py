from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class FirebaseConfig:
    """Immutable configuration for Firebase Realtime Database.

    This class intentionally does NOT read environment variables directly to avoid
    duplication; env loading is centralized in backend.config. Construct via:
      - FirebaseConfig.from_config_module()
      - FirebaseConfig.from_settings(path, url)
    """
    credentials_path: Path
    database_url: str

    @staticmethod
    def from_settings(credentials_path: str, database_url: str) -> "FirebaseConfig":
        return FirebaseConfig(Path(credentials_path), database_url)

    @staticmethod
    def from_config_module() -> "FirebaseConfig":
        from backend import config as cfg  # lazy import to avoid circular dependency
        return FirebaseConfig(Path(cfg.FIREBASE_CERTIFICATE_PATH), cfg.FIREBASE_DB_URL)

    def validate(self) -> None:
        if not self.credentials_path.exists():
            raise FileNotFoundError(f"Firebase credentials file not found: {self.credentials_path}")
        if not self.database_url.startswith("https://"):
            raise ValueError("database_url must start with https://")
