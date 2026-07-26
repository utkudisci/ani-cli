import subprocess

import requests

from core.diagnostics import diagnostics


class UpdateManager:
    API_URL = "https://api.github.com/repos/utkudisci/Ani-GUI/commits/master"

    def check(self):
        try:
            local = subprocess.run(
                ["git", "rev-parse", "HEAD"], capture_output=True, text=True,
                timeout=5, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            ).stdout.strip()
            response = requests.get(self.API_URL, timeout=10, headers={"Accept": "application/vnd.github+json"})
            response.raise_for_status()
            payload = response.json()
            remote = payload.get("sha", "")
            result = {
                "ok": True,
                "update_available": bool(local and remote and local != remote),
                "local": local[:7], "remote": remote[:7],
                "message": payload.get("commit", {}).get("message", "").splitlines()[0],
                "url": payload.get("html_url"),
            }
            diagnostics.log("info", "updates", "Update check completed", result=result)
            return result
        except Exception as exc:
            diagnostics.log("warning", "updates", "Update check failed", error=str(exc))
            return {"ok": False, "error": str(exc)}


update_manager = UpdateManager()
