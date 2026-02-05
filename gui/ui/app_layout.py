
import flet as ft
from core.scraper import AniScraper
from ui.detail_view import EpisodeDetailView
from ui.home_view import HomeView

class AppLayout(ft.Column):
    def __init__(self, page: ft.Page):
        super().__init__(expand=True)
        # self.page is a read-only property in Control, available after mount
        # We don't need to store it manually.
        self.scraper = AniScraper()
        self.current_view = "home"  # Track current view
        self.current_mode = "sub"  # Track current sub/dub mode
        
        self.results_grid = ft.GridView(
            expand=1,
            runs_count=5,
            max_extent=200,
            child_aspect_ratio=0.7,
            spacing=10,
            run_spacing=10,
        )
        self.search_field = ft.TextField(
            hint_text="Search anime...",
            expand=True,
            on_submit=self.search_anime,
            autofocus=True
        )
        
        # Loading overlay (centered spinner)
        # Loading overlay (centered spinner)
        self.loading_overlay = ft.Container(
            content=ft.Column([
                ft.ProgressRing(width=64, height=64, stroke_width=6),
                ft.Text("Searching...", size=18, weight=ft.FontWeight.BOLD),
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=20, alignment=ft.MainAxisAlignment.CENTER),
            visible=False,
            alignment=ft.Alignment(0, 0),
            expand=True,
        )
        
        # Home view
        self.home_view = HomeView(
            page, 
            on_search=self.search_from_home,
            on_anime_click=self.on_anime_click,
            on_mode_change=self.on_mode_change  # Add mode change callback
        )

        # Start with home view
        self.controls = [self.home_view]
    
    def on_mode_change(self, mode):
        """Handle mode change from home view toggle"""
        self.current_mode = mode
        print(f"🔄 Mode changed to: {mode}")  # DEBUG
    
    def search_from_home(self, query, mode="sub"):
        """Handle search from home screen"""
        # Switch to search results view
        self.current_view = "search"
        self.current_mode = mode  # Store selected mode
        self.search_field.value = query
        self.controls.clear()
        self.controls.extend([
            ft.Row(
                [
                    ft.IconButton(ft.Icons.HOME, on_click=self.show_home, tooltip="Home"),
                    self.search_field,
                    ft.IconButton(ft.Icons.SEARCH, on_click=self.search_anime),
                ],
                alignment=ft.MainAxisAlignment.CENTER,
            ),
            ft.Stack([
                ft.Container(content=self.results_grid, expand=True),
                self.loading_overlay,  # Overlay on top of results
            ], expand=True),
        ])
        self.update()
        self.search_anime(None)  # Trigger search
    
    def show_home(self, e=None):
        """Return to home screen"""
        self.current_view = "home"
        self.controls.clear()
        self.controls.append(self.home_view)
        # Remove loading overlay from page overlay when returning home
        if self.loading_overlay in self.page.overlay:
            self.page.overlay.remove(self.loading_overlay)
        self.update()
        # Refresh favorites and continue watching AFTER adding to page
        self.home_view.load_favorites()
        self.home_view.load_continue_watching()

    def search_anime(self, e):
        query = self.search_field.value
        if not query:
            return

        # Show loading overlay
        self.loading_overlay.visible = True
        self.results_grid.controls.clear()
        self.results_grid.update()
        self.loading_overlay.update()
        self.page.update() # Update page to show overlay immediately

        # Run search in background (or just sync for now, flet handles it ok-ish)
        # Ideally threading, but lets keep simple first
        results = self.scraper.search_anime(query)
        
        for anime in results:
            self.results_grid.controls.append(
                self.create_anime_card(anime)
            )

        # Hide loading overlay
        self.loading_overlay.visible = False
        self.loading_overlay.update()
        self.results_grid.update()

    def create_anime_card(self, anime):
        return ft.Card(
            elevation=5,
            content=ft.Container(
                content=ft.Column(
                    [
                        ft.Image(
                            src=anime.get("thumbnail") or "https://via.placeholder.com/150",
                            fit=ft.ImageFit.COVER if hasattr(ft, "ImageFit") else "cover",
                            expand=True,
                            border_radius=ft.border_radius.vertical(top=10)
                        ),
                        ft.Container(
                            content=ft.Text(
                                anime["title"],
                                size=14,
                                weight=ft.FontWeight.BOLD,
                                no_wrap=False,
                                max_lines=2,
                                overflow=ft.TextOverflow.ELLIPSIS,
                                text_align=ft.TextAlign.CENTER
                            ),
                            padding=5,
                            height=50,
                        )
                    ],
                    spacing=0,
                ),
                on_click=lambda e: self.on_anime_click(anime)
            )
        )

    
    def on_anime_click(self, anime):
        print(f"Clicked: {anime['title']}")
        print(f"🎭 Using mode: {self.current_mode}")  # DEBUG
        # Switch to detail view with selected mode
        detail_view = EpisodeDetailView(
            self.page, 
            anime, 
            on_back=self.restore_layout,
            mode=self.current_mode  # Pass the selected sub/dub mode
        )
        self.page.controls.clear()
        self.page.add(detail_view)
        self.page.update()

    def restore_layout(self):
        self.page.controls.clear()
        self.page.add(self)
        self.page.update()
