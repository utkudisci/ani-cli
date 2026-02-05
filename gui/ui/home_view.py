
import flet as ft
from core.history_manager import history_manager

class HomeView(ft.Column):
    def __init__(self, page: ft.Page, on_search=None, on_anime_click=None, on_mode_change=None):
        super().__init__(expand=True, spacing=20)
        # page is auto-available via self.page after mount
        self.on_search = on_search
        self.on_anime_click = on_anime_click
        self.on_mode_change = on_mode_change  # Callback when mode changes
        self.history = history_manager
        
        # Search field
        self.search_field = ft.TextField(
            hint_text="Search anime...",
            autofocus=True,
            on_submit=self.handle_search,
            expand=True,
            text_size=16,
            border_radius=10,
        )
        
        # Sub/Dub mode selection (default: sub)
        self.selected_mode = "sub"
        self.sub_button = ft.ElevatedButton(
            "SUB",
            bgcolor="blue",
            color="white",
            on_click=lambda e: self.set_mode("sub")
        )
        self.dub_button = ft.ElevatedButton(
            "DUB",
            bgcolor="grey700",  # Start unhighlighted with grey
            color="white",
            on_click=lambda e: self.set_mode("dub")
        )
        
        # Continue Watching Grid
        self.continue_watching_grid = ft.GridView(
            runs_count=5,
            max_extent=200,
            child_aspect_ratio=0.7,
            spacing=10,
            run_spacing=10,
            height=280,
        )
        
        # Favorites Grid
        self.favorites_grid = ft.GridView(
            runs_count=5,
            max_extent=200,
            child_aspect_ratio=0.7,
            spacing=10,
            run_spacing=10,
            height=280,
        )
        
        # Build UI
        self.controls = [
            # Header with search
            ft.Container(
                content=ft.Column([
                    ft.Text(
                        "Ani-CLI GUI",
                        size=32,
                        weight=ft.FontWeight.BOLD,
                        text_align=ft.TextAlign.CENTER,
                    ),
                    ft.Container(height=10),
                    ft.Row([
                        self.sub_button,
                        self.dub_button,
                    ], spacing=10),
                    ft.Container(height=5),
                    ft.Row([
                        self.search_field,
                        ft.IconButton(
                            icon=ft.Icons.SEARCH,
                            on_click=self.handle_search,
                            tooltip="Search",
                        ),
                    ]),
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                padding=20,
            ),
            
            # Continue Watching Section
            ft.Container(
                content=ft.Column([
                    ft.Row([
                        ft.Icon(ft.Icons.PLAY_CIRCLE_OUTLINE, size=24),
                        ft.Text("Continue Watching", size=20, weight=ft.FontWeight.BOLD),
                    ]),
                    ft.Container(height=10),
                    self.continue_watching_grid,
                ]),
                padding=20,
            ),
            
            # Favorites Section
            ft.Container(
                content=ft.Column([
                    ft.Row([
                        ft.Icon(ft.Icons.FAVORITE, size=24, color="red"),
                        ft.Text("Favorites", size=20, weight=ft.FontWeight.BOLD),
                    ]),
                    ft.Container(height=10),
                    self.favorites_grid,
                ]),
                padding=20,
            ),
        ]
        
        # Load data on initialization
        self.load_continue_watching()
        self.load_favorites()
    
    def load_continue_watching(self):
        """Load and display continue watching list"""
        self.continue_watching_grid.controls.clear()
        
        continue_list = self.history.get_continue_watching(limit=10)
        
        if not continue_list:
            # Show placeholder if empty
            self.continue_watching_grid.controls.append(
                ft.Text(
                    "No recent anime yet. Start watching something!",
                    color="grey",
                    italic=True,
                )
            )
        else:
            for anime in continue_list:
                self.continue_watching_grid.controls.append(
                    self.create_continue_card(anime)
                )
        # Update if already on page
        try:
            self.continue_watching_grid.update()
        except:
            pass  # Not yet added to page
    
    def create_continue_card(self, anime):
        """Create a card for continue watching anime"""
        return ft.Card(
            elevation=5,
            content=ft.Container(
                content=ft.Column([
                    ft.Image(
                        src=anime.get("thumbnail") or "https://via.placeholder.com/150",
                        fit="cover",
                        expand=True,
                        border_radius=ft.border_radius.vertical(top=10)
                    ),
                    ft.Container(
                        content=ft.Column([
                            ft.Text(
                                anime["title"],
                                size=12,
                                weight=ft.FontWeight.BOLD,
                                max_lines=2,
                                overflow=ft.TextOverflow.ELLIPSIS,
                            ),
                            ft.Text(
                                f"Ep {anime['last_episode']}",
                                size=10,
                                color="green",
                            ),
                        ], tight=True),
                        padding=5,
                        height=60,
                    )
                ], spacing=0),
                on_click=lambda e, a=anime: self.on_continue_click(a)
            )
        )
    
    def on_continue_click(self, anime):
        """Handle click on continue watching anime"""
        # Create anime data object for detail view
        anime_data = {
            "id": anime["id"],
            "title": anime["title"],
            "thumbnail": anime.get("thumbnail")
        }
        
        if self.on_anime_click:
            self.on_anime_click(anime_data)
    
    def load_favorites(self):
        """Load and display favorites list"""
        self.favorites_grid.controls.clear()
        
        favorites = self.history.get_favorites()
        
        if not favorites:
            # Show placeholder if empty
            self.favorites_grid.controls.append(
                ft.Text(
                    "No favorites yet. Add some from anime details!",
                    color="grey",
                    italic=True,
                )
            )
        else:
            for fav in favorites:
                self.favorites_grid.controls.append(
                    self.create_favorite_card(fav)
                )
        # Update if already on page
        try:
            self.favorites_grid.update()
        except:
            pass  # Not yet added to page
    
    def create_favorite_card(self, fav):
        """Create a card for favorited anime"""
        return ft.Card(
            elevation=5,
            content=ft.Container(
                content=ft.Column([
                    ft.Image(
                        src=fav.get("thumbnail") or "https://via.placeholder.com/150",
                        fit="cover",
                        expand=True,
                        border_radius=ft.border_radius.vertical(top=10)
                    ),
                    ft.Container(
                        content=ft.Text(
                            fav["title"],
                            size=12,
                            weight=ft.FontWeight.BOLD,
                            max_lines=2,
                            overflow=ft.TextOverflow.ELLIPSIS,
                            text_align=ft.TextAlign.CENTER,
                        ),
                        padding=5,
                        height=60,
                    )
                ], spacing=0),
                on_click=lambda e, f=fav: self.on_favorite_click(f)
            )
        )
    
    def on_favorite_click(self, fav):
        """Handle click on favorite anime"""
        anime_data = {
            "id": fav["id"],
            "title": fav["title"],
            "thumbnail": fav.get("thumbnail")
        }
        
        if self.on_anime_click:
            self.on_anime_click(anime_data)
    
    def set_mode(self, mode):
        """Switch between SUB and DUB mode"""
        self.selected_mode = mode
        
        # Notify app_layout about mode change
        if self.on_mode_change:
            self.on_mode_change(mode)
        
        # Update button colors with explicit values
        if mode == "sub":
            self.sub_button.bgcolor = "blue"
            self.sub_button.color = "white"
            self.dub_button.bgcolor = "grey700"  # Explicit grey color
            self.dub_button.color = "white"
        else:
            self.dub_button.bgcolor = "blue"
            self.dub_button.color = "white"
            self.sub_button.bgcolor = "grey700"  # Explicit grey color
            self.sub_button.color = "white"
        
        self.sub_button.update()
        self.dub_button.update()
    
    def handle_search(self, e):
        query = self.search_field.value.strip()
        if query and self.on_search:
            # Pass both query and selected mode
            print(f"🔍 Searching with mode: {self.selected_mode}")  # DEBUG
            self.on_search(query, self.selected_mode)
