import glob
import os
import shutil
import subprocess
import time
import queue
import threading
from importlib import metadata

import requests

from core.diagnostics import diagnostics


class SystemManager:
    WINGET_PACKAGES = {
        "mpv": "mpv-player.mpv-CI.MSVC",
        "aria2c": "aria2.aria2",
    }

    def find(self, name):
        direct = shutil.which(name) or shutil.which(f"{name}.exe")
        if direct:
            return direct
        patterns = {
            "mpv": r"%LOCALAPPDATA%\Microsoft\WinGet\Packages\mpv-player.mpv-CI.MSVC_*\mpv.exe",
            "aria2c": r"%LOCALAPPDATA%\Microsoft\WinGet\Packages\aria2.aria2_*\aria2c.exe",
        }
        matches = glob.glob(os.path.expandvars(patterns.get(name, ""))) if name in patterns else []
        return matches[0] if matches else None

    def dependency_status(self):
        result = {
            "Python": {"ok": True, "detail": os.sys.version.split()[0]},
            "MPV": {"ok": bool(self.find("mpv")), "detail": self.find("mpv") or "Not installed"},
            "aria2c": {"ok": bool(self.find("aria2c")), "detail": self.find("aria2c") or "Optional"},
        }
        for package in ("flet", "requests", "cryptography", "yt-dlp", "pypresence"):
            try:
                result[package] = {"ok": True, "detail": metadata.version(package)}
            except metadata.PackageNotFoundError:
                result[package] = {"ok": False, "detail": "Not installed"}
        return result

    def health_check(self):
        checks = self.dependency_status()
        started = time.monotonic()
        try:
            response = requests.get("https://mkissa.to", timeout=(5, 10))
            checks["Mkissa"] = {
                "ok": response.ok,
                "detail": f"HTTP {response.status_code} · {time.monotonic() - started:.2f}s",
            }
        except Exception as exc:
            checks["Mkissa"] = {"ok": False, "detail": str(exc)[:160]}
        diagnostics.log("info", "health", "Health check completed", checks=checks)
        return checks

    def install_command(self, dependency):
        package_id = self.WINGET_PACKAGES.get(dependency)
        winget = shutil.which("winget")
        if not package_id or not winget:
            return None
        return [
            winget, "install", "--id", package_id, "--exact", "--source", "winget",
            "--accept-package-agreements", "--accept-source-agreements", "--silent",
            "--disable-interactivity",
        ]

    def run_install(self, dependency, progress=None, timeout=600):
        command = self.install_command(dependency)
        if not command:
            return False, "Winget or package definition is unavailable"
        process = subprocess.Popen(
            command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
            encoding="utf-8", errors="replace", bufsize=1,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        output = []
        started = time.monotonic()
        lines = queue.Queue()

        def read_output():
            for line in process.stdout or []:
                lines.put(line.strip())

        reader = threading.Thread(target=read_output, daemon=True)
        reader.start()
        while process.poll() is None:
            if time.monotonic() - started > timeout:
                process.kill()
                return False, "Installation timed out"
            line = ""
            while not lines.empty():
                line = lines.get_nowait()
                if line:
                    output.append(line)
            if progress:
                progress(int(time.monotonic() - started), line)
            time.sleep(0.5)
        reader.join(timeout=2)
        while not lines.empty():
            line = lines.get_nowait()
            if line:
                output.append(line)
        success = process.returncode == 0
        message = output[-1] if output else ("Installed" if success else "Unknown Winget error")
        diagnostics.log("info" if success else "error", "installer", f"{dependency} install finished", success=success, detail=message)
        return success, message


system_manager = SystemManager()
