from pypresence import Presence
import time
import threading
from core.settings_manager import settings_manager

# Use a generic client ID or your own
CLIENT_ID = "1468834568613265501"  # Generic "Anime Client" ID placeholder or reliable one

class RPCManager:
    def __init__(self):
        self.rpc = None
        self.connected = False
        self.start_time = None
        # Connect in a separate thread to avoid blocking startup
        threading.Thread(target=self._connect, daemon=True).start()

    def _connect(self):
        try:
            self.rpc = Presence(CLIENT_ID)
            self.rpc.connect()
            self.connected = True
            print("🎮 Discord RPC Connected!")
        except Exception as e:
            print(f"⚠️ Discord RPC Connection Failed: {e}")
            self.connected = False

    def update_activity(self, anime_title, episode_no, state="Watching"):
        """Update Discord Presence"""
        # Check if RPC is enabled in settings
        if not settings_manager.get("discord_rpc", "enabled"):
            return
            
        if not self.connected or not self.rpc:
            return

        try:
            if not self.start_time:
                self.start_time = time.time()
            
            # Respect privacy settings
            show_title = settings_manager.get("discord_rpc", "show_title")
            show_episode = settings_manager.get("discord_rpc", "show_episode")
            
            details = anime_title if show_title else "Watching Anime"
            state_text = f"Episode {episode_no}" if show_episode else "Watching"
            
            self.rpc.update(
                state=state_text,
                details=details,
                start=self.start_time
            )
            print(f"✅ RPC Updated: {details} - {state_text}")
        except Exception as e:
            print(f"⚠️ RPC Update Failed: {e}")
            # Try reconnecting once?
            # self._connect() 

    def clear(self):
        if self.connected and self.rpc:
            try:
                self.rpc.clear()
            except:
                pass

rpc_manager = RPCManager()
