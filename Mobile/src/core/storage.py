import json
import os
import threading
from datetime import datetime, timezone
from pathlib import Path


class Storage:
    def __init__(self):
        root = os.getenv("FLET_APP_STORAGE_DATA")
        self.root = Path(root) if root else Path(__file__).resolve().parents[2] / ".mobile-data"
        self.root.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self.settings = self._read("settings.json", {
            "language": "tr", "mode": "sub", "theme": "dark",
            "check_updates": True, "quality": "best",
        })
        self.library = self._read("library.json", {"favorites": {}, "history": {}})
        self.provider_stats = self._read("providers.json", {})
        self.downloads = self._read("downloads.json", {})
        self.log_path = self.root / "mobile.log"
        (self.root / "downloads").mkdir(exist_ok=True)

    def _read(self, name, default):
        try:
            path = self.root / name
            return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default
        except Exception:
            return default

    def _write(self, name, value):
        with self._lock:
            (self.root / name).write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")

    def save_settings(self): self._write("settings.json", self.settings)
    def save_library(self): self._write("library.json", self.library)
    def save_providers(self): self._write("providers.json", self.provider_stats)
    def save_downloads(self): self._write("downloads.json", self.downloads)

    def toggle_favorite(self, anime):
        favorites = self.library["favorites"]
        anime_id = anime["id"]
        if anime_id in favorites:
            favorites.pop(anime_id)
            added = False
        else:
            favorites[anime_id] = {k: anime.get(k) for k in ("id", "title", "thumbnail")}
            added = True
        self.save_library()
        return added

    def is_favorite(self, anime_id): return anime_id in self.library["favorites"]

    def mark_watched(self, anime, episode):
        self.library["history"][anime["id"]] = {
            "id": anime["id"], "title": anime["title"], "thumbnail": anime.get("thumbnail"),
            "episode": str(episode), "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        self.save_library()

    def log(self, level, message, **details):
        record = {"time": datetime.now(timezone.utc).isoformat(timespec="seconds"), "level": level, "message": message, **details}
        with self._lock:
            with self.log_path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(record, ensure_ascii=False) + "\n")

    def logs(self, limit=100):
        if not self.log_path.exists(): return []
        return self.log_path.read_text(encoding="utf-8", errors="replace").splitlines()[-limit:]


storage = Storage()
