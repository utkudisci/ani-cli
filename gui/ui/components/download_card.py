import flet as ft
from core.download_manager import DownloadItem, download_manager
from core.theme_manager import theme_manager

class DownloadCard(ft.Card):
    def __init__(self, item: DownloadItem):
        super().__init__()
        self.item = item
        
        # UI Elements
        self.title_text = ft.Text(
            f"{item.title} - Episode {item.episode}",
            weight=ft.FontWeight.BOLD,
            no_wrap=True,
            overflow=ft.TextOverflow.ELLIPSIS,
            expand=True
        )
        
        self.status_text = ft.Text(
            item.status.capitalize(),
            size=12,
            # Initial color set in refresh_theme
        )
        
        self.progress_bar = ft.ProgressBar(
            value=item.progress,
            height=4
        )
        
        self.meta_text = ft.Text(
            f"{int(item.progress * 100)}% • {item.speed} • {item.eta}",
            size=12,
        )
        
        # Action Buttons
        self.cancel_btn = ft.IconButton(
            ft.Icons.CANCEL,
            tooltip="Cancel Download",
            on_click=self.cancel_download
        )
        
        self.icon_view = ft.Icon(ft.Icons.DOWNLOAD_FOR_OFFLINE)

        # Apply initial theme
        self.refresh_theme()

        self.content = ft.Container(
            content=ft.Column([
                ft.Row([
                    self.icon_view,
                    self.title_text,
                    self.cancel_btn
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                self.progress_bar,
                ft.Row([
                    self.status_text,
                    self.meta_text
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
            ], spacing=5),
            padding=10
        )

    def cancel_download(self, e):
        download_manager.cancel_download(self.item.id)
        # Button disables immediately for feedback
        self.cancel_btn.disabled = True
        self.update()

    def refresh_theme(self):
        """Update colors based on current theme"""
        theme = theme_manager.get_theme()
        
        self.progress_bar.color = theme.primary
        self.progress_bar.bgcolor = theme.surface
        
        self.icon_view.color = theme.primary
        self.cancel_btn.icon_color = theme.error
        
        # Meta text usually secondary/greyish. Using theme.text with opacity or just theme.text
        self.meta_text.color = theme.text
        self.meta_text.opacity = 0.7
        
        # Status text color depends on status, handled in update_state but we set default here
        if self.item.status not in ["completed", "error"]:
             self.status_text.color = theme.text
             self.status_text.opacity = 0.7

        self.update()

    def update_state(self):
        """Update UI based on item state"""
        self.progress_bar.value = self.item.progress
        self.status_text.value = self.item.status.capitalize()
        # Show error message if present and state is error
        if self.item.status == "error" and self.item.error_msg:
            self.status_text.value = f"Error: {self.item.error_msg}"
            self.status_text.tooltip = self.item.error_msg
        
        theme = theme_manager.get_theme()
        self.status_text.color = theme.success if self.item.status == "completed" else theme.error if self.item.status == "error" else theme.text
        if self.item.status not in ["completed", "error"]:
            self.status_text.opacity = 0.7
        else:
            self.status_text.opacity = 1.0
            
        self.meta_text.value = f"{int(self.item.progress * 100)}% • {self.item.speed} • {self.item.eta}"
        
        if self.item.status in ["completed", "error", "cancelled"]:
            self.cancel_btn.visible = False
            self.progress_bar.visible = False if self.item.status == "cancelled" else True
            
        self.update()
