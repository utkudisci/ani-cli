import json
import threading
import time
from pathlib import Path

from core.diagnostics import diagnostics


class ProviderManager:
    BASE_PRIORITY = {"Default": 40, "Yt-mp4": 35, "S-mp4": 30, "Mp4": 25, "Ok": 20}

    def __init__(self):
        self.path = Path.home() / ".ani-cli-gui" / "provider-stats.json"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self.stats = self._load()

    def _load(self):
        try:
            return json.loads(self.path.read_text(encoding="utf-8")) if self.path.exists() else {}
        except Exception:
            return {}

    def _save(self):
        self.path.write_text(json.dumps(self.stats, indent=2), encoding="utf-8")

    def record(self, name, success, duration, error=None):
        with self._lock:
            item = self.stats.setdefault(name, {
                "attempts": 0, "successes": 0, "failures": 0,
                "consecutive_failures": 0, "average_seconds": 0.0,
            })
            item["attempts"] += 1
            item["successes" if success else "failures"] += 1
            item["consecutive_failures"] = 0 if success else item["consecutive_failures"] + 1
            item["average_seconds"] = round(
                ((item["average_seconds"] * (item["attempts"] - 1)) + duration) / item["attempts"], 2
            )
            item["last_success"] = int(time.time()) if success else item.get("last_success")
            item["last_error"] = None if success else str(error or "Unknown provider error")[:300]
            self._save()
        diagnostics.log(
            "info" if success else "warning", "provider",
            f"{name}: {'success' if success else 'failed'}",
            duration=round(duration, 2), error=error,
        )

    def score(self, name):
        item = self.stats.get(name, {})
        attempts = item.get("attempts", 0)
        ratio = item.get("successes", 0) / attempts if attempts else 0.5
        penalty = min(item.get("consecutive_failures", 0) * 12, 48)
        speed_penalty = min(item.get("average_seconds", 0) * 2, 20)
        return self.BASE_PRIORITY.get(name, 0) + ratio * 50 - penalty - speed_penalty

    def sort(self, embeds):
        return sorted(embeds, key=lambda item: self.score(item.get("sourceName", "Unknown")), reverse=True)

    def snapshot(self):
        with self._lock:
            return json.loads(json.dumps(self.stats))


provider_manager = ProviderManager()
