import os
import subprocess
import shutil
import requests
import threading
import uuid
import time
from dataclasses import dataclass
from typing import Callable, Dict, Optional, List
from core.settings_manager import settings_manager

@dataclass
class DownloadItem:
    id: str
    title: str
    episode: str
    url: str
    path: str
    status: str = "pending"  # pending, downloading, completed, error, cancelled
    progress: float = 0.0
    speed: str = "0 KB/s"
    eta: str = "--:--"
    error_msg: Optional[str] = None
    cancel_flag: bool = False

class DownloadManager:
    def __init__(self):
        self.has_aria2 = shutil.which("aria2c") is not None
        print(f"⬇️ Download Manager initialized. aria2c detected: {self.has_aria2}")
        self.downloads: Dict[str, DownloadItem] = {}
        self.listeners: List[Callable] = []  # List of callback functions
        self.lock = threading.Lock()

    def add_listener(self, callback: Callable):
        """Add a listener for updates"""
        with self.lock:
            if callback not in self.listeners:
                self.listeners.append(callback)

    def remove_listener(self, callback: Callable):
        """Remove a listener"""
        with self.lock:
            if callback in self.listeners:
                self.listeners.remove(callback)
    
    def get_download_dir(self):
        """Get current download directory from settings"""
        download_dir = settings_manager.get("downloads", "location") or os.path.join(os.path.expanduser("~"), "ani-cli-downloads")
        if not os.path.exists(download_dir):
            os.makedirs(download_dir)
        return download_dir

    def get_all_downloads(self):
        with self.lock:
            # Return a copy to ensure thread safety for iteration
            return list(self.downloads.values())

    def cancel_download(self, download_id):
        with self.lock:
            if download_id in self.downloads:
                self.downloads[download_id].cancel_flag = True
                self.downloads[download_id].status = "cancelled"
        self._notify_update()

    def download_episode(self, url, anime_title, episode_no, on_progress=None, on_complete=None, on_error=None):
        """Start a download and return the download ID"""
        download_id = str(uuid.uuid4())
        filename = f"{self._sanitize_filename(anime_title)} - Episode {episode_no}.mp4"
        filepath = os.path.join(self.get_download_dir(), filename)
        
        item = DownloadItem(
            id=download_id,
            title=anime_title,
            episode=str(episode_no),
            url=url,
            path=filepath
        )
        with self.lock:
            self.downloads[download_id] = item
        self._notify_update()
        
        threading.Thread(
            target=self._download_worker,
            args=(download_id, url, filepath, on_progress, on_complete, on_error),
            daemon=True
        ).start()
        
        return download_id

    def _notify_update(self):
        # Iterate over a copy to avoid modification during iteration errors (threading)
        listeners_copy = []
        with self.lock:
            listeners_copy = list(self.listeners)
            
        for listener in listeners_copy:
            try:
                listener()
            except Exception as e:
                print(f"Error in download listener: {e}")

    def _download_worker(self, download_id, url, filepath, on_progress, on_complete, on_error):
        item = self.downloads.get(download_id)
        if not item: 
            return

        item.status = "downloading"
        self._notify_update()

        try:
            if self.has_aria2:
                self._download_aria2(item)
            else:
                self._download_requests(item)
            
            if item.cancel_flag:
                item.status = "cancelled"
                # Cleanup partial file
                if os.path.exists(filepath):
                    os.remove(filepath)
            else:
                item.status = "completed"
                item.progress = 1.0
                if on_complete:
                    on_complete(filepath)
            
        except Exception as e:
            item.status = "error"
            item.error_msg = str(e)
            if on_error:
                on_error(str(e))
        
        self._notify_update()

    def _download_aria2(self, item: DownloadItem):
        print(f"🚀 Starting aria2c download: {item.path}")
        cmd = [
            "aria2c", 
            item.url, 
            "--summary-interval=1",
            "--referer=https://allmanga.to",
            "--out",
            os.path.basename(item.path),
            "--dir",
            os.path.dirname(item.path)
        ]
        
        # We process stdout to check for cancel and parsing progress
        import re
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, bufsize=1, universal_newlines=True)
        
        # Regex to parse aria2 output: [#oid 10MiB/100MiB(10%) CN:1 DL:1.2MiB ETA:1m]
        progress_pattern = re.compile(r"\[.*?(\d+\.?\d*[KMG]?)i?B/(\d+\.?\d*[KMG]?)i?B\((\d+)%\).*?DL:(\d+\.?\d*[KMG]?)i?B.*?ETA:(.*?)\]")
        
        while process.poll() is None:
            if item.cancel_flag:
                process.terminate()
                return
            
            # Read line without blocking indefinitely
            output_line = process.stdout.readline()
            
            if output_line:
                # print(f"ARIA2: {output_line.strip()}") # Debug
                match = progress_pattern.search(output_line)
                if match:
                    # current_size = match.group(1) # Unused for now
                    # total_size = match.group(2) # Unused for now
                    percentage = int(match.group(3))
                    speed = match.group(4)
                    eta = match.group(5)
                    
                    item.progress = percentage / 100.0
                    item.speed = f"{speed}iB/s"
                    item.eta = eta
                    self._notify_update()
            else:
                 time.sleep(0.1)
            
        if process.returncode != 0:
            stderr = process.stderr.read()
            # Check if it was just because of cancellation
            if item.cancel_flag:
                return
            raise Exception(f"Aria2c failed: {stderr}")

    def _download_requests(self, item: DownloadItem):
        print(f"🐢 Starting requests download (fallback): {item.path}")
        headers = {"Referer": "https://allmanga.to"}
        
        start_time = time.time()
        
        with requests.get(item.url, stream=True, headers=headers) as r:
            r.raise_for_status()
            total_length = int(r.headers.get('content-length', 0))
            
            with open(item.path, 'wb') as f:
                if total_length == 0:
                    f.write(r.content)
                else:
                    dl = 0
                    for chunk in r.iter_content(chunk_size=8192):
                        if item.cancel_flag:
                            return
                            
                        if chunk:
                            f.write(chunk)
                            dl += len(chunk)
                            
                            # Calculate stats
                            item.progress = dl / total_length
                            elapsed = time.time() - start_time
                            if elapsed > 0:
                                speed_bps = dl / elapsed
                                item.speed = f"{speed_bps/1024/1024:.2f} MB/s"
                            
                            self._notify_update()

    def _sanitize_filename(self, name):
        return "".join([c for c in name if c.isalpha() or c.isdigit() or c==' ']).rstrip()

download_manager = DownloadManager()
