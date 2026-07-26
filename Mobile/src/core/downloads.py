import os
import re
import threading
import uuid

from yt_dlp import YoutubeDL

from core.storage import storage


class DownloadInterrupted(Exception):
    pass


class MobileDownloadManager:
    def __init__(self):
        self.items = storage.downloads
        self.listeners = []
        self.lock = threading.RLock()
        for item in self.items.values():
            if item.get("status") == "downloading": item["status"] = "paused"
        storage.save_downloads()

    def add_listener(self, callback):
        if callback not in self.listeners: self.listeners.append(callback)

    def _notify(self):
        storage.save_downloads()
        for callback in list(self.listeners):
            try: callback()
            except Exception: pass

    def start(self, url, anime, episode):
        item_id = str(uuid.uuid4())
        safe_title = re.sub(r'[^\w .-]', '', anime["title"]).strip()
        path = str(storage.root / "downloads" / f"{safe_title} - Episode {episode}.mp4")
        self.items[item_id] = {
            "id": item_id, "anime_id": anime["id"], "title": anime["title"], "thumbnail": anime.get("thumbnail"),
            "episode": str(episode), "url": url, "path": path, "status": "queued", "progress": 0,
            "speed": "--", "eta": "--", "pause": False, "cancel": False,
        }
        self._notify()
        self._launch(item_id)
        return item_id

    def _launch(self, item_id):
        threading.Thread(target=self._worker, args=(item_id,), daemon=True).start()

    def pause(self, item_id):
        item = self.items.get(item_id)
        if item:
            item["pause"] = True; item["status"] = "paused"; self._notify()

    def resume(self, item_id):
        item = self.items.get(item_id)
        if item and item.get("status") in ("paused", "error"):
            item["pause"] = False; item["cancel"] = False; item["status"] = "queued"; self._notify(); self._launch(item_id)

    def cancel(self, item_id):
        item = self.items.get(item_id)
        if item:
            item["cancel"] = True; item["status"] = "cancelled"; self._notify()

    def remove(self, item_id):
        item = self.items.pop(item_id, None)
        if item and os.path.exists(item.get("path", "")):
            try: os.remove(item["path"])
            except OSError: pass
        self._notify()

    def _worker(self, item_id):
        item = self.items.get(item_id)
        if not item: return
        item["status"] = "downloading"; self._notify()

        def hook(data):
            if item.get("pause") or item.get("cancel"): raise DownloadInterrupted()
            if data.get("status") == "downloading":
                total = data.get("total_bytes") or data.get("total_bytes_estimate") or 0
                downloaded = data.get("downloaded_bytes") or 0
                item["progress"] = downloaded / total if total else item.get("progress", 0)
                item["speed"] = data.get("_speed_str", "--").strip()
                item["eta"] = data.get("_eta_str", "--").strip()
                self._notify()

        try:
            options = {
                "outtmpl": item["path"], "quiet": True, "no_warnings": True, "continuedl": True,
                "concurrent_fragment_downloads": 4, "hls_prefer_native": True, "format": "best",
                "http_headers": {"Referer": "https://mkissa.to"}, "progress_hooks": [hook],
            }
            with YoutubeDL(options) as ydl: ydl.download([item["url"]])
            if item.get("cancel"): item["status"] = "cancelled"
            elif item.get("pause"): item["status"] = "paused"
            else: item["status"] = "completed"; item["progress"] = 1
        except DownloadInterrupted:
            item["status"] = "cancelled" if item.get("cancel") else "paused"
        except Exception as exc:
            item["status"] = "error"; item["error"] = str(exc)[:300]
            storage.log("error", "download_failed", title=item["title"], episode=item["episode"], error=str(exc))
        self._notify()


download_manager = MobileDownloadManager()
