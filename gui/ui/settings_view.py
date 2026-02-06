import flet as ft
from core.settings_manager import settings_manager
from core.theme_manager import theme_manager
import threading

class SettingsView(ft.Container):
    def __init__(self, page: ft.Page, on_close=None):
        super().__init__()
        self._page = page  # Use _page to avoid read-only property conflict
        self.on_close_callback = on_close
        
        # Load current settings
        self.current_settings = settings_manager.get_all()
        
        # Create UI controls
        self._build_ui()
        
        # Add theme listener
        theme_manager.add_listener(self._on_theme_update)
        
    def _build_ui(self):
        # Playback settings
        self.mode_dropdown = ft.Dropdown(
            label="Default Mode",
            options=[
                ft.dropdown.Option("sub", "Subtitles (Sub)"),
                ft.dropdown.Option("dub", "Dubbed (Dub)"),
            ],
            value=self.current_settings["playback"]["default_mode"],
            width=300
        )
        
        self.player_dropdown = ft.Dropdown(
            label="Default Player",
            options=[
                ft.dropdown.Option("mpv", "MPV"),
                ft.dropdown.Option("vlc", "VLC"),
            ],
            value=self.current_settings["playback"]["default_player"],
            width=300
        )

        # Appearance settings
        theme_options = [
            ft.dropdown.Option(key, theme.name) 
            for key, theme in theme_manager.get_all_themes().items()
        ]
        self.theme_dropdown = ft.Dropdown(
            label="Theme",
            options=theme_options,
            value=theme_manager.get_theme().key,
            width=300
        )
        self.theme_dropdown.on_change = lambda e: self._on_theme_change(e)
        
        # Download settings
        self.download_location = ft.TextField(
            label="Download Location",
            value=self.current_settings["downloads"]["location"],
            read_only=True,
            expand=True
        )
        
        self.browse_button = ft.ElevatedButton(
            "Browse...",
            icon=ft.Icons.FOLDER_OPEN,
            on_click=self._browse_folder
        )
        
        # Discord RPC settings
        self.rpc_enabled = ft.Switch(
            label="Enable Discord RPC",
            value=self.current_settings["discord_rpc"]["enabled"]
        )
        
        self.rpc_show_episode = ft.Switch(
            label="Show Episode Number",
            value=self.current_settings["discord_rpc"]["show_episode"]
        )
        
        self.rpc_show_title = ft.Switch(
            label="Show Anime Title",
            value=self.current_settings["discord_rpc"]["show_title"]
        )
        
        # Build the overlay
        self.content = ft.Container(
            content=ft.Column([
                # Header
                ft.Row([
                    ft.Text("Settings", size=24, weight=ft.FontWeight.BOLD),
                    ft.IconButton(
                        icon=ft.Icons.CLOSE,
                        on_click=self._close,
                        tooltip="Close"
                    )
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                
                ft.Divider(),
                
                # Scrollable content
                ft.Container(
                    content=ft.Column([
                        # Playback Section
                        ft.Text("🎬 Playback", size=18, weight=ft.FontWeight.BOLD),
                        self.mode_dropdown,
                        self.player_dropdown,
                        ft.Divider(height=20),

                        # Appearance Section
                        ft.Text("🎨 Appearance", size=18, weight=ft.FontWeight.BOLD),
                        self.theme_dropdown,  
                        ft.Divider(height=20),
                        
                        # Downloads Section
                        ft.Text("⬇️ Downloads", size=18, weight=ft.FontWeight.BOLD),
                        ft.Row([
                            self.download_location,
                            self.browse_button
                        ]),
                        ft.Divider(height=20),
                        
                        # Discord RPC Section
                        ft.Text("🎮 Discord RPC", size=18, weight=ft.FontWeight.BOLD),
                        self.rpc_enabled,
                        self.rpc_show_episode,
                        self.rpc_show_title,
                        ft.Divider(height=20),
                        
                    ], scroll=ft.ScrollMode.AUTO, spacing=10),
                    expand=True
                ),
                
                # Footer buttons
                ft.Row([
                    ft.ElevatedButton(
                        "Save",
                        icon=ft.Icons.SAVE,
                        on_click=self._save_settings,
                        bgcolor="#1976D2",  # Blue
                        color="#FFFFFF"  # White
                    ),
                    ft.OutlinedButton(
                        "Cancel",
                        icon=ft.Icons.CANCEL,
                        on_click=self._close
                    )
                ], alignment=ft.MainAxisAlignment.END, spacing=10)
                
            ], spacing=15),
            padding=30,
            bgcolor=theme_manager.get_theme().surface,  # Use theme surface
            border_radius=10,
            width=500,
            height=600
        )
        self.settings_panel = self.content # Reference for theme updates
        
        # Overlay background
        self.bgcolor = "rgba(0, 0, 0, 0.5)"  # Semi-transparent black
        self.alignment = ft.Alignment(0, 0)  # Center
        self.expand = True
    
    def _browse_folder(self, e):
        """Open native Windows folder picker"""
        def pick_folder():
            try:
                # Use tkinter for native Windows folder dialog
                from tkinter import Tk, filedialog
                root = Tk()
                root.withdraw()  # Hide the main window
                root.attributes('-topmost', True)  # Bring dialog to front
                
                folder_path = filedialog.askdirectory(
                    title="Select Download Folder",
                    initialdir=self.download_location.value or "C:\\"
                )
                root.destroy()
                
                if folder_path:
                    # Update UI on main thread
                    self.download_location.value = folder_path
                    self._page.update()
            except Exception as ex:
                print(f"Error opening folder picker: {ex}")
        
        # Run in separate thread to avoid blocking UI
        threading.Thread(target=pick_folder, daemon=True).start()

    
    def _save_settings(self, e):
        """Save settings and close"""
        # Update settings
        settings_manager.set("playback", "default_mode", self.mode_dropdown.value)
        settings_manager.set("playback", "default_player", self.player_dropdown.value)
        settings_manager.set("downloads", "location", self.download_location.value)
        settings_manager.set("discord_rpc", "enabled", self.rpc_enabled.value)
        settings_manager.set("discord_rpc", "show_episode", self.rpc_show_episode.value)
        settings_manager.set("discord_rpc", "show_title", self.rpc_show_title.value)
        
        # Explicitly save theme from dropdown value (Fix for missing on_change event)
        current_theme_val = self.theme_dropdown.value
        print(f"💾 SAVE CLICKED: theme_dropdown.value is currently: '{current_theme_val}'")
        
        if current_theme_val:
            # Force update settings_manager just in case on_change missed it
            settings_manager.set("appearance", "theme", current_theme_val)
            theme_manager.set_theme(current_theme_val, self._page)
        
        # Save to file
        if settings_manager.save_settings():
            # Show success message
            snackbar = ft.SnackBar(content=ft.Text("✅ Settings saved successfully!"))
            self._page.overlay.append(snackbar)
            snackbar.open = True
            self._page.update()
        
        # Close overlay
        self._close(e)
    
    def _on_theme_change(self, e):
        """Update theme immediately"""
        print(f"🖱️ DROPDOWN CHANGE: New value is '{e.data}'")
        # Explicitly update the dropdown's internal value to ensure it matches UI
        self.theme_dropdown.value = e.data
        theme_manager.set_theme(e.data, self._page)

    def _on_theme_update(self):
        """Update settings view colors dynamically"""
        theme = theme_manager.get_theme()
        # Update the main panel background
        if hasattr(self, "settings_panel"):
            self.settings_panel.bgcolor = theme.surface
            self.settings_panel.update()
        
        self.update()

    def _close(self, e):
        """Close the settings overlay"""
        theme_manager.remove_listener(self._on_theme_update)
        if self.on_close_callback:
            self.on_close_callback()
