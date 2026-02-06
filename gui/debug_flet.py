import flet as ft
for d in dir(ft.Page):
    if "run" in d or "pub" in d or "update" in d:
        print(d)
