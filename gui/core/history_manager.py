import json
import os
from datetime import datetime
from pathlib import Path

class HistoryManager:
    def __init__(self):
        # Store history in user's home directory
        self.history_dir = Path.home() / ".ani-cli-gui"
        self.history_file = self.history_dir / "watch_history.json"
        self.favorites_file = self.history_dir / "favorites.json"
        
        # Create directory if not exists
        self.history_dir.mkdir(exist_ok=True)
        
        # Load existing data
        self.history = self._load_json(self.history_file, {})
        self.favorites = self._load_json(self.favorites_file, [])
    
    def _load_json(self, filepath, default):
        """Load JSON file or return default"""
        try:
            if filepath.exists():
                with open(filepath, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            print(f"Error loading {filepath}: {e}")
        return default
    
    def _save_json(self, filepath, data):
        """Save data to JSON file"""
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error saving {filepath}: {e}")
    
    def mark_episode_watched(self, anime_id, anime_title, episode_no, thumbnail=None):
        """Mark an episode as watched"""
        anime_id = str(anime_id)
        episode_no = str(episode_no)
        
        # Initialize anime entry if not exists
        if anime_id not in self.history:
            self.history[anime_id] = {
                "title": anime_title,
                "thumbnail": thumbnail,
                "episodes": {},
                "last_episode": 0,
                "last_watched": None
            }
        
        # Mark episode as watched
        self.history[anime_id]["episodes"][episode_no] = {
            "watched": True,
            "timestamp": datetime.now().isoformat()
        }
        
        # Update last watched info
        self.history[anime_id]["last_episode"] = int(episode_no)
        self.history[anime_id]["last_watched"] = datetime.now().isoformat()
        self.history[anime_id]["title"] = anime_title  # Update title in case it changed
        if thumbnail:
            self.history[anime_id]["thumbnail"] = thumbnail
        
        self._save_json(self.history_file, self.history)
    
    def is_episode_watched(self, anime_id, episode_no):
        """Check if episode is watched"""
        anime_id = str(anime_id)
        episode_no = str(episode_no)
        
        if anime_id in self.history:
            return episode_no in self.history[anime_id]["episodes"]
        return False
    
    def get_continue_watching(self, limit=10):
        """Get list of anime to continue watching (sorted by last watched)"""
        continue_list = []
        
        for anime_id, data in self.history.items():
            continue_list.append({
                "id": anime_id,
                "title": data["title"],
                "thumbnail": data.get("thumbnail"),
                "last_episode": data["last_episode"],
                "last_watched": data["last_watched"]
            })
        
        # Sort by last watched (most recent first)
        continue_list.sort(key=lambda x: x["last_watched"] or "", reverse=True)
        
        return continue_list[:limit]
    
    def add_favorite(self, anime_id, anime_title, thumbnail=None):
        """Add anime to favorites"""
        anime_id = str(anime_id)
        
        # Check if already in favorites
        if not any(f["id"] == anime_id for f in self.favorites):
            self.favorites.append({
                "id": anime_id,
                "title": anime_title,
                "thumbnail": thumbnail,
                "added": datetime.now().isoformat()
            })
            self._save_json(self.favorites_file, self.favorites)
            return True
        return False
    
    def remove_favorite(self, anime_id):
        """Remove anime from favorites"""
        anime_id = str(anime_id)
        self.favorites = [f for f in self.favorites if f["id"] != anime_id]
        self._save_json(self.favorites_file, self.favorites)
    
    def is_favorite(self, anime_id):
        """Check if anime is in favorites"""
        anime_id = str(anime_id)
        return any(f["id"] == anime_id for f in self.favorites)
    
    def get_favorites(self):
        """Get all favorites"""
        return self.favorites

# Global instance
history_manager = HistoryManager()
