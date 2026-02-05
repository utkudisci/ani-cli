
import flet as ft
import subprocess
import threading
from core.scraper import AniScraper
from core.history_manager import history_manager
import subprocess

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
            visible=False,
            alignment=ft.Alignment(0, 0),
            expand=True,
        )
        
        # Favorite button
        is_fav = self.history.is_favorite(self.anime["id"])
        self.fav_button = ft.IconButton(
            icon=ft.Icons.FAVORITE if is_fav else ft.Icons.FAVORITE_BORDER,
            icon_color="red" if is_fav else None,
            tooltip="Remove from favorites" if is_fav else "Add to favorites",
            on_click=self.toggle_favorite
        )

        # Build controls
        self.controls = [
            ft.Row(
                [
                    ft.IconButton(ft.Icons.ARROW_BACK, on_click=self.go_back),
                    ft.Text(self.anime["title"], size=20, weight=ft.FontWeight.BOLD, expand=True),
                    self.fav_button,  # Add favorite button
                ]
            ),
            ft.Stack([
                ft.Container(content=self.episodes_grid, expand=True),
                self.loading_overlay,  # Overlay on top
            ], expand=True),
        ]

    def did_mount(self):
        self.load_episodes()

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
        self.loading_overlay.update()
        threading.Thread(target=self._load_episodes_thread, daemon=True).start()

    def _load_episodes_thread(self):
        print(f"📺 Loading episodes with mode: {self.mode}")  # DEBUG
        try:
            # Fetch episodes with selected mode (sub/dub)
            eps = self.scraper.get_episodes_list(self.anime["id"], mode=self.mode)
            
            # Update UI on main thread
            self.episodes_grid.controls.clear() # Fix duplication
            
            for ep in eps:
                # Check if episode is watched
                is_watched = self.history.is_episode_watched(self.anime["id"], ep)
                
                # Create button content with checkmark if watched
                if is_watched:
                    button_content = ft.Row([
                        ft.Icon(ft.Icons.CHECK_CIRCLE, color="green", size=16),
                        ft.Text(str(ep)),
                    ], tight=True, spacing=5)
                else:
                    button_content = ft.Text(str(ep))
                
                self.episodes_grid.controls.append(
                    ft.ElevatedButton(
                        content=button_content,
                        on_click=lambda e, ep=ep: self.play_episode(ep)
                    )
                )
        except Exception as e:
            print(f"Error loading episodes: {e}")
            # self.show_snack(f"Error loading episodes: {e}") 
            # Cannot easily show snack from thread without page reference handling
        
        # Hide loading
        self.loading_overlay.visible = False
        self.update()

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
        self.loading_overlay.visible = True
        self.loading_overlay.update()
        
        threading.Thread(target=self._play_episode_thread, args=(ep_no,), daemon=True).start()

    def _play_episode_thread(self, ep_no):
        try:
            # Get Links with selected mode
            embeds = self.scraper.get_episode_embeds(self.anime["id"], ep_no, mode=self.mode)
            if not embeds:
                self.loading_overlay.visible = False
                self.loading_overlay.update()
                self.show_snack("No embeds found!")
                return

            # Try ALL providers
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
                self.loading_overlay.visible = False
                self.loading_overlay.update()
                self.show_snack("No valid stream links found!")
                return
            
            # Hide loading
            self.loading_overlay.visible = False
            self.loading_overlay.update()
            
            print(f"Final Stream URL: {stream_url}")
            # Launch MPV
            cmd = [
                "mpv",
                f"--force-media-title={self.anime['title']} - Episode {ep_no}",
                "--referrer=https://allmanga.to",  # Important!
                stream_url
            ]
            subprocess.Popen(cmd)
            
            # ✅ Mark episode as watched in history
            self.history.mark_episode_watched(
                anime_id=self.anime["id"],
                anime_title=self.anime["title"],
                episode_no=ep_no,
                thumbnail=self.anime.get("thumbnail")
            )
            
            # Refresh episode list (run in thread context, but load_episodes spawns its own thread anyway)
            # Better to call load_episodes causing a UI update
            # Since load_episodes is now threaded, it's safe to call.
            self.load_episodes()
            
            self.show_snack(f"Playing Episode {ep_no}...")
            
        except FileNotFoundError:
             self.show_snack("MPV not found in PATH!")
        except Exception as e:
            print(f"Error playing episode: {e}")
            self.show_snack(f"Error: {e}")
            self.loading_overlay.visible = False
            self.loading_overlay.update()
