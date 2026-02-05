from pypresence import Presence
import time
import threading

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
        if not self.connected or not self.rpc:
            return

        try:
            # Should be run in thread? pypresence updates are usually fast but network calls.
            # Lets just try direct first.
            if not self.start_time:
                self.start_time = time.time()
                
            details = f"{anime_title}"
            state_text = f"Episode {episode_no}"
            
            self.rpc.update(
                state=state_text,
                details=details,
                # large_image="ani_neco_arc", # These require uploaded assets in Dev Portal
                # small_image="play_icon",
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
