"""
Room Manager — CRUD for named room locations.
Stored in rooms.json as { "name": {"x": ..., "y": ...} }.
"""
import json
import os
import threading

from config import ROOMS_FILE
from utils import logger


class RoomManager:

    def __init__(self, path: str = ROOMS_FILE):
        self._path = path
        self._lock = threading.Lock()
        self._rooms: dict[str, dict] = {}
        self._load()

    # ── persistence ──────────────────────────

    def _load(self):
        if os.path.exists(self._path):
            try:
                with open(self._path, "r") as f:
                    self._rooms = json.load(f)
                logger.info("Loaded %d rooms from %s", len(self._rooms), self._path)
            except Exception as e:
                logger.warning("Could not load rooms: %s", e)
                self._rooms = {}
        else:
            self._rooms = {}

    def _save(self):
        try:
            with open(self._path, "w") as f:
                json.dump(self._rooms, f, indent=2)
        except Exception as e:
            logger.error("Could not save rooms: %s", e)

    # ── CRUD ─────────────────────────────────

    def list_rooms(self) -> list[dict]:
        """Return all rooms as [{name, x, y}, ...]."""
        with self._lock:
            return [
                {"name": name, "x": coords["x"], "y": coords["y"]}
                for name, coords in self._rooms.items()
            ]

    def get_room(self, name: str) -> dict | None:
        """Get a room by name. Returns {name, x, y} or None."""
        key = name.lower().strip()
        with self._lock:
            if key in self._rooms:
                c = self._rooms[key]
                return {"name": key, "x": c["x"], "y": c["y"]}
        return None

    def set_room(self, name: str, x: float, y: float) -> dict:
        """Create or update a room."""
        key = name.lower().strip()
        with self._lock:
            self._rooms[key] = {"x": x, "y": y}
            self._save()
        logger.info("Room '%s' set at (%.1f, %.1f)", key, x, y)
        return {"name": key, "x": x, "y": y}

    def delete_room(self, name: str) -> bool:
        key = name.lower().strip()
        with self._lock:
            if key in self._rooms:
                del self._rooms[key]
                self._save()
                logger.info("Room '%s' deleted", key)
                return True
        return False
