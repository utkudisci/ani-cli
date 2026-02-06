import json
import os
from pathlib import Path

class SettingsManager:
    def __init__(self):
        # Settings file location
        self.settings_dir = Path.home() / ".ani-cli-gui"
        self.settings_file = self.settings_dir / "settings.json"
        
        # Default settings
        self.defaults = {
            "playback": {
                "default_mode": "sub",
                "default_player": "mpv"
            },
            "downloads": {
                "location": str(Path.home() / "ani-cli-downloads")
            },
            "discord_rpc": {
                "enabled": True,
                "show_episode": True,
                "show_title": True
            },
            "appearance": {
                "theme": "standard"
            }
        }
        
        self.settings = self.load_settings()
    
    def load_settings(self):
        """Load settings from JSON file or create with defaults"""
        try:
            print(f"📂 Loading settings from: {self.settings_file}")
            if self.settings_file.exists():
                with open(self.settings_file, 'r') as f:
                    content = f.read()
                    print(f"📄 Raw settings file content: {content}")
                    loaded = json.loads(content)
                    # Merge with defaults to handle new settings
                    merged = self._merge_defaults(loaded)
                    print(f"🧩 Merged settings: {merged}")
                    return merged
            else:
                # Create directory and file with defaults
                print("🆕 Settings file not found, creating defaults")
                self.settings_dir.mkdir(parents=True, exist_ok=True)
                self.save_settings(self.defaults)
                return self.defaults.copy()
        except Exception as e:
            print(f"⚠️ Error loading settings: {e}")
            return self.defaults.copy()
    
    def _merge_defaults(self, loaded):
        """Merge loaded settings with defaults to handle missing keys"""
        merged = self.defaults.copy()
        for category, values in loaded.items():
            if category in merged:
                merged[category].update(values)
            else:
                # Preserve categories not in defaults (e.g. from newer versions or plugins)
                merged[category] = values
        return merged
    
    def save_settings(self, settings=None):
        """Save settings to JSON file"""
        try:
            print(f"🆔 SettingsManager.save_settings instance ID: {id(self)}")
            if settings:
                self.settings = settings
            
            print(f"💾 Saving settings to: {self.settings_file}")
            print(f"📦 Content to save: {self.settings}")
            
            self.settings_dir.mkdir(parents=True, exist_ok=True)
            with open(self.settings_file, 'w') as f:
                json.dump(self.settings, f, indent=2)
            print("✅ Settings saved")
            return True
        except Exception as e:
            print(f"⚠️ Error saving settings: {e}")
            return False
    
    def get(self, category, key):
        """Get a specific setting value"""
        return self.settings.get(category, {}).get(key)
    
    def set(self, category, key, value):
        """Set a specific setting value"""
        if category not in self.settings:
            self.settings[category] = {}
        self.settings[category][key] = value
    
    def get_all(self):
        """Get all settings"""
        return self.settings.copy()

# Global settings manager instance
settings_manager = SettingsManager()
