import flet as ft
from ui.app_layout import AppLayout

def main(page: ft.Page):
    page.title = "Ani-Cli GUI"
    page.theme_mode = ft.ThemeMode.DARK
    page.padding = 10
    page.window_maximized = True
    

    app = AppLayout(page)
    page.add(app)

if __name__ == "__main__":
    ft.app(target=main)

