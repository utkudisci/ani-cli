import time

from core.storage import storage


class ProviderRanker:
    base = {"Default": 40, "Yt-mp4": 35, "S-mp4": 30, "Mp4": 25, "Ok": 20}

    def score(self, name):
        item = storage.provider_stats.get(name, {})
        attempts = item.get("attempts", 0)
        ratio = item.get("successes", 0) / attempts if attempts else 0.5
        return self.base.get(name, 0) + ratio * 50 - item.get("consecutive_failures", 0) * 12 - min(item.get("average_seconds", 0) * 2, 20)

    def sort(self, embeds):
        return sorted(embeds, key=lambda x: self.score(x.get("sourceName", "Unknown")), reverse=True)

    def record(self, name, success, duration, error=None):
        item = storage.provider_stats.setdefault(name, {"attempts": 0, "successes": 0, "failures": 0, "consecutive_failures": 0, "average_seconds": 0})
        item["attempts"] += 1
        item["successes" if success else "failures"] += 1
        item["consecutive_failures"] = 0 if success else item["consecutive_failures"] + 1
        item["average_seconds"] = round(((item["average_seconds"] * (item["attempts"] - 1)) + duration) / item["attempts"], 2)
        item["last_success"] = int(time.time()) if success else item.get("last_success")
        item["last_error"] = None if success else str(error or "Unknown")[:240]
        storage.save_providers()
        storage.log("info" if success else "warning", "provider_attempt", provider=name, success=success, duration=round(duration, 2), error=error)


provider_ranker = ProviderRanker()
