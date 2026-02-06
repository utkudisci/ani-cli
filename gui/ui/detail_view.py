
import flet as ft
import os
import subprocess
import shutil
import threading
from core.scraper import AniScraper
from core.download_manager import download_manager
from core.history_manager import history_manager
from core.rpc_manager import rpc_manager
from core.rpc_manager import rpc_manager
from core.settings_manager import settings_manager
from core.theme_manager import theme_manager

def find_player_executable(player_name):
    """Find player executable with robust Windows support.
    
    Checks in order:
    1. Custom path from settings (if provided)
    2. shutil.which() (PATH-based)
    3. Known Windows install locations
    
    Returns full path to executable or None if not found.
    """
    # Check for custom path in settings
    custom_path = settings_manager.get("playback", f"{player_name}_custom_path")
    if custom_path and os.path.exists(custom_path):
        print(f"✓ Using custom {player_name.upper()} path: {custom_path}")
        return custom_path
    
    # Try PATH-based detection
    path = shutil.which(player_name)
    if path:
        print(f"✓ Found {player_name.upper()} in PATH: {path}")
        return path
    
    # Try with .exe extension explicitly (Windows)
    path = shutil.which(f"{player_name}.exe")
    if path:
        print(f"✓ Found {player_name.upper()}.exe in PATH: {path}")
        return path
    
    # Check known Windows install locations
    if player_name == "vlc":
        known_paths = [
            r"C:\Program Files\VideoLAN\VLC\vlc.exe",
            r"C:\Program Files (x86)\VideoLAN\VLC\vlc.exe",
        ]
    elif player_name == "mpv":
        known_paths = [
            r"C:\Program Files\mpv\mpv.exe",
            r"C:\Program Files (x86)\mpv\mpv.exe",
            os.path.expanduser(r"~\scoop\apps\mpv\current\mpv.exe"),
        ]
    else:
        known_paths = []
    
    for candidate in known_paths:
        if os.path.exists(candidate):
            print(f"✓ Found {player_name.upper()} at known location: {candidate}")
            return candidate
    
    print(f"✗ {player_name.upper()} not found in PATH or known locations")
    return None

class EpisodeDetailView(ft.Column):
    def __init__(self, page: ft.Page, anime_data: dict, on_back=None, mode="sub"):
        super().__init__(expand=True)
        # self.page is managed by Flet
        self.anime = anime_data
        self.on_back = on_back
        self.mode = mode  # Store sub/dub mode
        self.scraper = AniScraper()
        self.history = history_manager
        
        self.episodes_grid = ft.GridView(
            runs_count=8,
            max_extent=80,
            child_aspect_ratio=1.5,
            spacing=10,
            run_spacing=10,
            expand=True
        )
        
        # Loading overlay for episodes loading
        self.loading_overlay = ft.Container(
            content=ft.Column([
                ft.ProgressRing(width=64, height=64, stroke_width=6),
                ft.Text("Loading episodes...", size=18, weight=ft.FontWeight.BOLD),
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=20, alignment=ft.MainAxisAlignment.CENTER),
            alignment=ft.Alignment(0, 0),
            expand=True,
        )

        self.content_stack = ft.Stack([
            ft.Container(content=self.episodes_grid, expand=True),
            self.loading_overlay,  # Overlay on top
        ], expand=True)
        
        # Favorite button
        is_fav = self.history.is_favorite(self.anime["id"])
        self.fav_button = ft.IconButton(
            icon=ft.Icons.FAVORITE if is_fav else ft.Icons.FAVORITE_BORDER,
            icon_color="red" if is_fav else None,
            tooltip="Remove from favorites" if is_fav else "Add to favorites",
            on_click=self.toggle_favorite
        )

        # Action Mode Toggle (Watch vs Download)
        self.action_mode = "watch"
        # Action Mode Toggle (Watch vs Download)
        self.action_mode = "watch"
        # Action Mode Toggle (Watch vs Download)
        self.action_mode = "watch"
        
        # Manual Toggle Buttons
        theme = theme_manager.get_theme()
        watch_bg = theme.primary if self.action_mode == "watch" else None
        watch_color = theme.text if self.action_mode == "watch" else None
        
        self.btn_watch = ft.ElevatedButton(
            "Watch", 
            icon=ft.Icons.PLAY_ARROW, 
            on_click=lambda e: self.set_action_mode("watch"),
            bgcolor=watch_bg, color=watch_color
        )
        self.btn_download = ft.OutlinedButton(
            "Download", 
            icon=ft.Icons.DOWNLOAD, 
            on_click=lambda e: self.set_action_mode("download")
        )

        self.mode_control = ft.Row(
            [self.btn_watch, self.btn_download], 
            alignment=ft.MainAxisAlignment.CENTER,
            spacing=10
        )

        # Build controls
        self.controls = [
            ft.Row(
                [
                    ft.IconButton(ft.Icons.ARROW_BACK, on_click=self.go_back),
                    ft.Text(self.anime["title"], size=20, weight=ft.FontWeight.BOLD, expand=True),
                    self.fav_button,
                ]
            ),
            ft.Row([self.mode_control], alignment=ft.MainAxisAlignment.CENTER), # Add toggle
            self.content_stack,
        ]

    def set_action_mode(self, mode):
        self.action_mode = mode
        self._update_theme_colors()
        
    def _update_theme_colors(self):
        theme = theme_manager.get_theme()
        
        if self.action_mode == "watch":
            self.btn_watch = ft.ElevatedButton("Watch", icon=ft.Icons.PLAY_ARROW, on_click=lambda e: self.set_action_mode("watch"), bgcolor=theme.primary, color=theme.text)
            self.btn_download = ft.OutlinedButton("Download", icon=ft.Icons.DOWNLOAD, on_click=lambda e: self.set_action_mode("download"))
        else:
            self.btn_watch = ft.OutlinedButton("Watch", icon=ft.Icons.PLAY_ARROW, on_click=lambda e: self.set_action_mode("watch"))
            self.btn_download = ft.ElevatedButton("Download", icon=ft.Icons.DOWNLOAD, on_click=lambda e: self.set_action_mode("download"), bgcolor=theme.primary, color=theme.text)
            
        self.mode_control.controls = [self.btn_watch, self.btn_download]
        self.mode_control.update()
        
        # Update episode buttons if they exist
        if hasattr(self, "episode_buttons") and self.episode_buttons:
            for ep_str, btn in self.episode_buttons.items():
                is_watched = self.history.is_episode_watched(self.anime["id"], int(ep_str))
                if btn.style:
                    btn.style.side = ft.BorderSide(2, theme.primary) if is_watched else None
                try:
                    btn.update()
                except: pass
        
        # self.show_snack(f"Mode switched to: {self.action_mode.upper()}") # SNACK REMOVED AS IT IS NOISY ON THEME UPDATE
        # Reload episodes to update click handlers (or just check mode in handler)
        # Better to check mode in handler to avoid reload flicker
        
    def on_episode_click(self, ep_no):
        if self.action_mode == "watch":
            self.play_episode(ep_no)
        else:
            self.download_episode_action(ep_no)

    def download_episode_action(self, ep_no):
        self.show_snack(f"Starting download for Episode {ep_no}...")
        threading.Thread(target=self._download_episode_thread, args=(ep_no,), daemon=True).start()

    def _download_episode_thread(self, ep_no):
        # 1. Fetch links (reuse logic?)
        # For simplicity, copy-paste basic fetch logic or refactor. 
        # Refactoring play_episode to be reusable for getting stream url would be best.
        # But for now, lets duplicate fetch logic to keep changes isolated.
        
        try:
            # Show simple loading toast/overlay? No, allow background.
            print(f"⬇️ Fetching link for download: Episode {ep_no}")
            
            embeds = self.scraper.get_episode_embeds(self.anime["id"], ep_no, mode=self.mode)
            if not embeds:
                self.show_snack("Download failed: No embeds found")
                return

            stream_url = None
            for embed in embeds:
                stream_url = self.scraper.get_stream_link(embed)
                if stream_url: break
            
            if not stream_url:
                 self.show_snack("Download failed: No stream link")
                 return
            
            # Start download
            # Update button to downloading state
            btn = self.episode_buttons.get(str(ep_no))
            if btn:
                btn.content = ft.Row([
                    ft.ProgressRing(width=16, height=16, stroke_width=2),
                    ft.Text("Downloading...", size=12),
                ], alignment=ft.MainAxisAlignment.CENTER)
                btn.update()

            def on_dl_complete(path):
                self.show_snack(f"Download complete: {os.path.basename(path)}")
                if btn:
                    btn.content = ft.Row([
                        ft.Icon(ft.Icons.CHECK, color="green"),
                        ft.Text("Saved", size=12),
                    ], alignment=ft.MainAxisAlignment.CENTER)
                    btn.bgcolor = "rgba(0, 255, 0, 0.2)"  # Green with opacity
                    btn.update()

            def on_dl_error(err):
                self.show_snack(f"Download error: {err}")
                if btn:
                    btn.content = ft.Row([
                        ft.Icon(ft.Icons.ERROR, color="red"),
                        ft.Text("Error", size=12),
                    ], alignment=ft.MainAxisAlignment.CENTER)
                    btn.update()

            download_manager.download_episode(
                stream_url, 
                self.anime["title"], 
                ep_no,
                on_complete=on_dl_complete,
                on_error=on_dl_error
            )
            # Update Discord RPC
            rpc_manager.update_activity(self.anime["title"], ep_no, state="Downloading")
            self.show_snack(f"Download started: Episode {ep_no}")
            
        except Exception as e:
            print(f"Download thread error: {e}")
            self.show_snack(f"Error starting download: {e}")
            # Reset button state if error occurred before download started
            btn = self.episode_buttons.get(str(ep_no))
            if btn:
                btn.content = ft.Text(str(ep_no))
                btn.update()


    def did_mount(self):
        self.page.pubsub.subscribe(self._on_pubsub_message)
        theme_manager.add_listener(self._on_theme_update)
        self.load_episodes()
        
    def will_unmount(self):
        """Cleanup when view is destroyed"""
        try:
            self.page.pubsub.unsubscribe_all()
            print(f"🧹 Unsubscribed from PubSub for {self.anime['title']}")
        except Exception as e:
            print(f"⚠️ Error unsubscribing: {e}")
        theme_manager.remove_listener(self._on_theme_update)
            
    def _on_theme_update(self):
        self._update_theme_colors()
        
    def _on_pubsub_message(self, message):
        topic = message.get("topic")
        if topic == "episodes_loaded":
            self._on_episodes_loaded(message["data"])
        elif topic == "stream_found":
            data = message["data"]
            self._on_stream_found(data["url"], data["ep_no"])
        elif topic == "error":
            self._on_error(message["data"])

    def go_back(self, e):
        if self.on_back:
            self.on_back()
    
    def toggle_favorite(self, e):
        """Toggle favorite status"""
        is_fav = self.history.is_favorite(self.anime["id"])
        
        if is_fav:
            # Remove from favorites
            self.history.remove_favorite(self.anime["id"])
            self.fav_button.icon = ft.Icons.FAVORITE_BORDER
            self.fav_button.icon_color = None
            self.fav_button.tooltip = "Add to favorites"
            self.show_snack("Removed from favorites")
        else:
            # Add to favorites
            self.history.add_favorite(
                anime_id=self.anime["id"],
                anime_title=self.anime["title"],
                thumbnail=self.anime.get("thumbnail")
            )
            self.fav_button.icon = ft.Icons.FAVORITE
            self.fav_button.icon_color = "red"
            self.fav_button.tooltip = "Remove from favorites"
            self.show_snack("Added to favorites ❤️")
        
        self.fav_button.update()

    def load_episodes(self):
        # Start loading in a separate thread to not block UI
        self.loading_overlay.visible = True
        self.content_stack.update()
        
        # Start Worker
        threading.Thread(target=self._load_episodes_thread, daemon=True).start()

    def _load_episodes_thread(self):
        print(f"📺 Loading episodes with mode: {self.mode}")  # DEBUG
        try:
            # Fetch episodes with selected mode (sub/dub)
            # This is BLOCKING and happens in background
            eps = self.scraper.get_episodes_list(self.anime["id"], mode=self.mode)
            
            # Marshal to UI thread via PubSub
            if self.page:
                self.page.pubsub.send_all({"topic": "episodes_loaded", "data": eps})
                
        except Exception as e:
            print(f"Error loading episodes: {e}")
            if self.page:
                self.page.pubsub.send_all({"topic": "error", "data": str(e)})

    def _on_episodes_loaded(self, eps):
        # This runs on UI thread!
        self.episode_buttons = {} # Store references
        controls = []
        
        theme = theme_manager.get_theme()
        for ep in eps:
            is_watched = self.history.is_episode_watched(self.anime["id"], ep)
            
            # Simple text content for both
            button_content = ft.Text(str(ep))
            
            # Themed style for watched episodes
            style = ft.ButtonStyle(
                padding=0,
                side=ft.BorderSide(2, theme.primary) if is_watched else None,
                shape=ft.RoundedRectangleBorder(radius=8)
            )
            
            btn = ft.ElevatedButton(
                content=button_content,
                on_click=lambda e, ep=ep: self.on_episode_click(ep),
                style=style
            )
            self.episode_buttons[str(ep)] = btn
            controls.append(btn)
            
        self.episodes_grid.controls = controls
        
        # Hide loading
        if self.loading_overlay in self.content_stack.controls:
             self.content_stack.controls.remove(self.loading_overlay)
        
        self.content_stack.update()

    def _on_error(self, message):
         if self.loading_overlay in self.content_stack.controls:
             self.content_stack.controls.remove(self.loading_overlay)
         self.content_stack.update()
         self.show_snack(f"Error: {message}")



    def show_snack(self, message):
        sb = ft.SnackBar(content=ft.Text(message))
        self.page.overlay.append(sb)
        sb.open = True
        self.page.update()

    def play_episode(self, ep_no):
        """Play episode - fetch stream link and launch MPV"""
        print(f"Playing Episode {ep_no}")
        
        # Show loading overlay
        # Access controls safely
        if len(self.loading_overlay.content.controls) > 1:
            self.loading_overlay.content.controls[1].value = f"Fetching stream links for Episode {ep_no}..."
        
        # Ensure overlay is in stack
        if self.loading_overlay not in self.content_stack.controls:
            self.content_stack.controls.append(self.loading_overlay)
            
        self.loading_overlay.visible = True
        self.content_stack.update()
        
        threading.Thread(target=self._play_episode_thread, args=(ep_no,), daemon=True).start()

    def _play_episode_thread(self, ep_no):
        try:
            # Get Links (Blocking)
            embeds = self.scraper.get_episode_embeds(self.anime["id"], ep_no, mode=self.mode)
            if not embeds:
                self.page.pubsub.send_all({"topic": "error", "data": "No embeds found!"})
                return

            # Try ALL providers (Blocking)
            stream_url = None
            for i, embed in enumerate(embeds):
                provider_name = embed.get("sourceName", f"Provider {i+1}")
                print(f"Trying provider: {provider_name}")
                
                stream_url = self.scraper.get_stream_link(embed)
                if stream_url:
                    print(f"✓ Success! Provider '{provider_name}' returned: {stream_url}")
                    break  # Found a working provider
                else:
                    print(f"✗ Provider '{provider_name}' failed, trying next...")

            if not stream_url:
                self.page.pubsub.send_all({"topic": "error", "data": "No valid stream links found!"})
                return

            # Marshal success to UI thread via PubSub
            self.page.pubsub.send_all({"topic": "stream_found", "data": {"url": stream_url, "ep_no": ep_no}})
            
        except FileNotFoundError:
             self.page.pubsub.send_all({"topic": "error", "data": "MPV not found in PATH!"})
        except Exception as e:
            print(f"Error playing episode: {e}")
            self.page.pubsub.send_all({"topic": "error", "data": f"Error: {e}"})

    def _on_stream_found(self, stream_url, ep_no):
        print(f"Final Stream URL: {stream_url}")
        
        # Hide loading
        if self.loading_overlay in self.content_stack.controls:
            self.content_stack.controls.remove(self.loading_overlay)
        self.content_stack.update()
        
        # Update Discord RPC
        rpc_manager.update_activity(self.anime["title"], ep_no)

        # Launch player (use settings with robust detection)
        player = settings_manager.get("playback", "default_player") or "mpv"
        print(f"🎬 Attempting to launch {player.upper()}...")
        
        # Find player executable with robust detection
        if player == "vlc":
            vlc_path = find_player_executable("vlc")
            if not vlc_path:
                # VLC not found, fallback to MPV
                error_msg = "VLC not found in PATH or known locations! Falling back to MPV..."
                print(f"⚠️ {error_msg}")
                self.show_snack(error_msg)
                player = "mpv"  # Switch to MPV
            else:
                cmd = [
                    vlc_path,
                    f"--meta-title={self.anime['title']} - Episode {ep_no}",
                    "--http-referrer=https://allmanga.to",
                    stream_url
                ]
        
        if player == "mpv":  # MPV (default or fallback)
            mpv_path = find_player_executable("mpv")
            if not mpv_path:
                error_msg = "MPV not found! Please install MPV or configure a custom player path in settings."
                self.show_snack(error_msg)
                print(f"❌ {error_msg}")
                return
            cmd = [
                mpv_path,
                f"--force-media-title={self.anime['title']} - Episode {ep_no}",
                "--referrer=https://allmanga.to",
                stream_url
            ]
        
        # Launch player
        try:
            print(f"🚀 Launching: {' '.join(cmd)}")
            subprocess.Popen(cmd)
        except Exception as e:
            error_msg = f"Failed to launch player: {e}"
            print(f"❌ {error_msg}")
            self.show_snack(error_msg)
        
        # ✅ Mark episode as watched in history
        self.history.mark_episode_watched(
            anime_id=self.anime["id"],
            anime_title=self.anime["title"],
            episode_no=ep_no,
            thumbnail=self.anime.get("thumbnail")
        )
        
        # Refresh episode list to update watched status icons
        # This calls load_episodes again, which is now thread safe
        self.load_episodes()
        
        self.show_snack(f"Playing Episode {ep_no}...")


