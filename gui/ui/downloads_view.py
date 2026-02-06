import flet as ft
from core.download_manager import download_manager
from core.theme_manager import theme_manager
from ui.components.download_card import DownloadCard

class DownloadsView(ft.Container):
    def __init__(self, page: ft.Page, on_close=None):
        super().__init__()
        self._page = page
        self.on_close = on_close
        self.download_cards = {}  # Map id -> DownloadCard
        
        # Style as overlay
        theme = theme_manager.get_theme()
        self.bgcolor = theme.surface
        self.border_radius = 10
        self.padding = 20
        self.margin = ft.margin.symmetric(horizontal=50, vertical=50)
        self.shadow = ft.BoxShadow(
            blur_radius=20,
            color="black" # Shadow usually stays black
        )

        
        self.download_cards = {}  # Map id -> DownloadCard
        
        self.content_list = ft.ListView(
            expand=True,
            spacing=10,
            padding=10,
        )
        
        self.content = ft.Column([
            ft.Row([
                ft.Text("Downloads", size=28, weight=ft.FontWeight.BOLD),
                ft.IconButton(ft.Icons.CLOSE, on_click=self._close_overlay)
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            self.content_list
        ], expand=True)
        
        self.expand = True
        
    def _close_overlay(self, e):
        if self.on_close:
            self.on_close()
        
    def did_mount(self):
        """Called when added to page"""
        # Subscribe to updates only when mounted
        download_manager.add_listener(self._on_manager_update)
        theme_manager.add_listener(self._on_theme_update)
        self._refresh_list()
        self._on_theme_update() # Apply current theme just in case

    def will_unmount(self):
        """Called when removed from page"""
        # Unsubscribe to prevent updates to unmounted control
        download_manager.remove_listener(self._on_manager_update)
        theme_manager.remove_listener(self._on_theme_update)

    def _refresh_list(self):
        """Rebuild the list from scratch (or update existing)"""
        # Simple implementation: Rebuild if count changes, otherwise update cards
        downloads = download_manager.get_all_downloads()
        
        # Sort: Downloading first, then pending, then others
        downloads.sort(key=lambda x: 0 if x.status == "downloading" else 1)
        
        # Check if we need to rebuild controls (new items added)
        current_ids = set(self.download_cards.keys())
        new_ids = set(d.id for d in downloads)
        
        if current_ids != new_ids:
            self.content_list.controls.clear()
            self.download_cards.clear()
            
            if not downloads:
                self.content_list.controls.append(
                    ft.Container(
                        content=ft.Column([
                            ft.Icon(ft.Icons.DOWNLOAD_DONE, size=64, color="grey"),
                            ft.Text("No active downloads", color="grey", size=16)
                        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                        alignment=ft.Alignment(0, 0),
                        expand=True,
                        padding=50
                    )
                )
            else:
                for item in downloads:
                    card = DownloadCard(item)
                    self.download_cards[item.id] = card
                    self.content_list.controls.append(card)
        else:
            # Just update existing cards
            for item in downloads:
                if item.id in self.download_cards:
                    self.download_cards[item.id].update_state()
        
        self.update()

    def _on_manager_update(self):
        """Called from background thread when downloads update"""
        # Schedule update on UI thread to prevent collisions
        if not self._page or not self.page:
             # If view is not mounted (self.page is None), do nothing
             return
             
        try:
            # Try to use run_task if available (Flet 0.21+) to schedule on UI loop
            if hasattr(self._page, "run_task"):
                self._page.run_task(self._handle_update_async)
            else:
                # Fallback for older Flet: just call synchronously
                self._handle_update_sync()
        except Exception as e:
            print(f"Error triggering update: {e}")

    async def _handle_update_async(self):
        """Async wrapper for update logic if run_task is used"""
        self._handle_update_sync()

    def _handle_update_sync(self):
        """Synchronous update logic"""
        try:
            self._refresh_list()
        except Exception as e:
            print(f"Error updating downloads view: {e}")
            import traceback
            traceback.print_exc()

    def _on_theme_update(self):
        """Update colors when theme changes"""
        theme = theme_manager.get_theme()
        self.bgcolor = theme.surface
        # Update styling of child controls if accessible or rebuild
        for card in self.download_cards.values():
            card.refresh_theme()
        self.update()
