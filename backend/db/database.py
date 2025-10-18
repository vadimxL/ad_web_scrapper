from __future__ import annotations

from typing import Optional

import firebase_admin
from firebase_admin import credentials
from firebase_admin import db as firebase_db
from firebase_admin.db import Reference

from .firebase_config import FirebaseConfig


class Database:
    """Lightweight Firebase Realtime Database wrapper (non-singleton).
    Initialization:
        - If a FirebaseConfig is provided, it is validated and used.
        - If not provided, configuration is pulled from backend.config via FirebaseConfig.from_config_module().
        - If a Firebase app is already initialized in this process, it is reused.

    Typical usage:
        from backend.db.firebase_config import FirebaseConfig
        cfg = FirebaseConfig.from_config_module()
        db = Database(cfg)
        db = Database()
    Database instances reuse the already initialized default firebase_admin app.
    """

    def __init__(self, config: Optional[FirebaseConfig] = None, auto_init: bool = True) -> None:
        self._config: Optional[FirebaseConfig] = config
        self._app: Optional[firebase_admin.App] = None
        if auto_init:
            self.init()

    def init(self) -> None:
        if self._app is not None:
            return
        if firebase_admin._apps:  # type: ignore[attr-defined]
            # Reuse existing default app (avoids multiple initialize_app calls)
            self._app = firebase_admin.get_app()
            return
        if self._config is None:
            # Lazy load from environment variables
            self._config = FirebaseConfig.from_env()
        # Validate config
        self._config.validate()
        cred = credentials.Certificate(str(self._config.credentials_path))
        self._app = firebase_admin.initialize_app(cred, {"databaseURL": self._config.database_url})

    def reference(self, path: str) -> Reference:
        if self._app is None:
            raise RuntimeError("Database not initialized. Call init() first.")
        return firebase_db.reference(path, app=self._app)

    def clear(self) -> None:
        self.reference("/").delete()

    def is_ready(self) -> bool:
        return self._app is not None
