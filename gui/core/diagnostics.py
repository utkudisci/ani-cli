import json
import os
import platform
import shutil
import sys
import threading
import zipfile
from datetime import datetime, timezone
from importlib import metadata
from pathlib import Path


class Diagnostics:
    def __init__(self):
        self.base_dir = Path.home() / ".ani-cli-gui"
        self.log_dir = self.base_dir / "logs"
        self.log_file = self.log_dir / "app.log"
        self._lock = threading.Lock()
        self.log_dir.mkdir(parents=True, exist_ok=True)

    def log(self, level, component, message, **details):
        try:
            from core.settings_manager import settings_manager
            if settings_manager.get("diagnostics", "logging_enabled") is False:
                return
        except Exception:
            pass
        record = {
            "time": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "level": level.upper(),
            "component": component,
            "message": str(message),
        }
        if details:
            record["details"] = details
        line = json.dumps(record, ensure_ascii=False)
        with self._lock:
            with self.log_file.open("a", encoding="utf-8") as handle:
                handle.write(line + "\n")

    def tail(self, limit=200):
        if not self.log_file.exists():
            return []
        with self._lock:
            lines = self.log_file.read_text(encoding="utf-8", errors="replace").splitlines()
        return lines[-limit:]

    def clear(self):
        with self._lock:
            self.log_file.write_text("", encoding="utf-8")

    def dependency_snapshot(self):
        packages = {}
        for name in ("flet", "requests", "cryptography", "yt-dlp", "pypresence"):
            try:
                packages[name] = metadata.version(name)
            except metadata.PackageNotFoundError:
                packages[name] = None
        return {
            "python": sys.version.split()[0],
            "platform": platform.platform(),
            "executables": {
                "mpv": shutil.which("mpv") or shutil.which("mpv.exe"),
                "aria2c": shutil.which("aria2c") or shutil.which("aria2c.exe"),
                "winget": shutil.which("winget"),
            },
            "packages": packages,
        }

    def export(self, destination_dir=None, health=None, provider_stats=None):
        destination = Path(destination_dir or (Path.home() / "Desktop"))
        if not destination.exists():
            destination = self.base_dir
        destination.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        archive = destination / f"ani-gui-diagnostics-{timestamp}.zip"
        report = {
            "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "environment": self.dependency_snapshot(),
            "health": health or {},
            "provider_stats": provider_stats or {},
            "privacy": "Watch history, favorites, download URLs and settings are excluded.",
        }
        with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as bundle:
            bundle.writestr("diagnostics.json", json.dumps(report, ensure_ascii=False, indent=2))
            if self.log_file.exists():
                bundle.write(self.log_file, "app.log")
        self.log("info", "diagnostics", "Diagnostics exported", path=str(archive))
        return str(archive)


diagnostics = Diagnostics()
