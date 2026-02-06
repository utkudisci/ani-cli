import flet as ft
from dataclasses import dataclass
from typing import Dict, List, Optional
from core.settings_manager import settings_manager

@dataclass
class Theme:
    name: str
    primary: str
    secondary: str
    background: str
    surface: str
    text: str
    error: str = "#FF5252"  # Red Accent 200
    success: str = "#69F0AE" # Green Accent 200

    @property
    def key(self):
        # Match the keys in PRESETS (standard, saiyan, eva_01, straw_hat, demon)
        return self.name.lower().replace(" ", "_").replace("-", "_")

# Anime-Inspired Presets
PRESETS = {
    "standard": Theme(
        "Standard", 
        primary="#2196F3",   # Blue
        secondary="#64B5F6", # Light Blue
        background="#111111",# Almost Black
        surface="#1E1E1E",   # Dark Grey
        text="#FFFFFF"
    ),
    "saiyan": Theme(
        "Saiyan",
        primary="#FF9800",   # Orange (Goku's Gi)
        secondary="#2196F3", # Blue (Undershirt)
        background="#0D0F16",# Dark Blue-ish Black
        surface="#1A2332",   # Dark Blue Grey
        text="#FFFFFF"
    ),
    "eva_01": Theme(
        "Eva-01",
        primary="#9C27B0",   # Purple
        secondary="#4CAF50", # Green
        background="#0F0518",# Deep Purple Black
        surface="#1D0E29",   # Dark Purple
        text="#FFFFFF"
    ),
    "straw_hat": Theme(
        "Straw Hat",
        primary="#F44336",   # Red (Vest)
        secondary="#FFEB3B", # Yellow (Hat/Sash)
        background="#1C0B0B",# Dark Red Black
        surface="#2D1515",   # Dark Red Brown
        text="#FFFFFF"
    ),
    "demon": Theme(
        "Demon",
        primary="#4CAF50",   # Green (Tanjiro Checkers)
        secondary="#000000", # Black
        background="#050F05",# Deep Green Black
        surface="#0F1F0F",   # Dark Green
        text="#FFFFFF"
    )
}

class ThemeManager:
    def __init__(self):
        self.current_theme: Theme = PRESETS["standard"]
        self.listeners: List[callable] = []
        self._load_theme()

    def _load_theme(self):
        """Load theme from settings"""
        theme_key = settings_manager.get("appearance", "theme")
        print(f"🎨 ThemeManager _load_theme reading key: {theme_key}")
        
        # Defensive check: if key doesn't exist or is invalid, fallback to standard
        if theme_key in PRESETS:
            self.current_theme = PRESETS[theme_key]
        else:
            # Try to match by name lower if key fails (backup)
            print(f"⚠️ Key '{theme_key}' not in presets, searching names...")
            for k, t in PRESETS.items():
                if t.key == theme_key:
                    self.current_theme = t
                    return
            self.current_theme = PRESETS["standard"]

    def set_theme(self, theme_key: str, page: Optional[ft.Page] = None):
        """Set active theme and notify listeners"""
        print(f"🎨 ThemeManager.set_theme called with: {theme_key}")
        print(f"🆔 ThemeManager using SettingsManager ID: {id(settings_manager)}")
        
        if theme_key in PRESETS:
            self.current_theme = PRESETS[theme_key]
            # Persist
            settings_manager.set("appearance", "theme", theme_key)
            print(f"🧐 Settings before save: {settings_manager.get_all()}")
            settings_manager.save_settings()
            
            # Apply to page if provided
            if page:
                self.apply_theme(page)
            
            # Notify listeners (e.g., UI components)
            self._notify_listeners()

    def apply_theme(self, page: ft.Page):
        """Apply current theme properties to the Flet page"""
        t = self.current_theme
        page.bgcolor = t.background
        
        # Set a global ColorScheme to affect standard Flet controls
        page.theme = ft.Theme(
            color_scheme=ft.ColorScheme(
                primary=t.primary,
                secondary=t.secondary,
                surface=t.surface,
                on_surface=t.text,
                on_primary=t.text,
                error=t.error,
            )
        )
        # Force redraw everything
        page.update()
        for control in page.controls:
             if hasattr(control, "update"):
                 try:
                     control.update()
                 except: pass

    def get_theme(self) -> Theme:
        return self.current_theme
    
    def get_all_themes(self) -> Dict[str, Theme]:
        return PRESETS

    def add_listener(self, callback: callable):
        if callback not in self.listeners:
            self.listeners.append(callback)

    def remove_listener(self, callback: callable):
        if callback in self.listeners:
            self.listeners.remove(callback)

    def _notify_listeners(self):
        for listener in self.listeners:
            try:
                listener()
            except Exception as e:
                print(f"Error in theme listener: {e}")

theme_manager = ThemeManager()
