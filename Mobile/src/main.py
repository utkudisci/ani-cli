import json
import os
import threading
import time
from datetime import datetime

import flet as ft
import flet_video as ftv
import requests

from core.api import AniApi
from core.downloads import download_manager
from core.i18n import text
from core.providers import provider_ranker
from core.storage import storage


class MobileApp:
    def __init__(self, page: ft.Page):
        self.page = page
        self.api = AniApi()
        self.language = storage.settings.get("language", "tr")
        self.mode = storage.settings.get("mode", "sub")
        self.current_anime = None
        self.current_episode = None
        self.video = None
        self.body = ft.Column(expand=True, spacing=0)
        self.page.title = "Ani-GUI Mobile"
        self.page.theme_mode = ft.ThemeMode.DARK if storage.settings.get("theme", "dark") == "dark" else ft.ThemeMode.LIGHT
        self.page.padding = 0
        self.page.bgcolor = "#10131A"
        self.page.on_error = lambda e: storage.log("error", "flet_error", error=str(e.data))
        self._build_navigation()
        self.page.add(ft.SafeArea(content=self.body, expand=True))
        download_manager.add_listener(self._downloads_updated)
        self.show_home()
        if storage.settings.get("check_updates", True):
            threading.Thread(target=self._background_update_check, daemon=True).start()

    def t(self, key): return text(key, self.language)

    def _build_navigation(self):
        self.page.navigation_bar = ft.NavigationBar(
            selected_index=0,
            destinations=[
                ft.NavigationBarDestination(ft.Icons.HOME, self.t("home"), selected_icon=ft.Icons.HOME_FILLED),
                ft.NavigationBarDestination(ft.Icons.FAVORITE_BORDER, self.t("favorites"), selected_icon=ft.Icons.FAVORITE),
                ft.NavigationBarDestination(ft.Icons.DOWNLOAD_OUTLINED, self.t("downloads"), selected_icon=ft.Icons.DOWNLOAD),
                ft.NavigationBarDestination(ft.Icons.SETTINGS_OUTLINED, self.t("settings"), selected_icon=ft.Icons.SETTINGS),
            ],
            on_change=self._navigate,
        )

    def _navigate(self, e):
        index = e.control.selected_index
        [self.show_home, self.show_favorites, self.show_downloads, self.show_settings][index]()

    def _set_view(self, controls, title="Ani-GUI Mobile", actions=None, show_nav=True, back=None):
        self.body.controls = controls
        self.page.appbar = ft.AppBar(
            title=ft.Text(title, weight=ft.FontWeight.BOLD),
            leading=ft.IconButton(ft.Icons.ARROW_BACK, on_click=lambda e: back()) if back else None,
            actions=actions or [], center_title=False, bgcolor="#171B25",
        )
        self.page.navigation_bar.visible = show_nav
        self.page.update()

    def _snack(self, message, error=False):
        bar = ft.SnackBar(content=ft.Text(message), bgcolor=ft.Colors.RED_800 if error else ft.Colors.BLUE_800)
        self.page.overlay.append(bar); bar.open = True; self.page.update()

    def _loading(self, message):
        dialog = ft.AlertDialog(modal=True, content=ft.Row([ft.ProgressRing(width=28, height=28), ft.Text(message, expand=True)]))
        self.page.overlay.append(dialog); dialog.open = True; self.page.update(); return dialog

    def _close_dialog(self, dialog):
        dialog.open = False
        try: self.page.update()
        except Exception: pass

    def show_home(self):
        self.page.navigation_bar.selected_index = 0
        query = ft.TextField(hint_text=self.t("search"), expand=True, border_radius=24, on_submit=lambda e: self.search(query.value))
        mode = ft.SegmentedButton(
            segments=[ft.Segment("sub", label=ft.Text("SUB")), ft.Segment("dub", label=ft.Text("DUB"))],
            selected={self.mode}, allow_multiple_selection=False,
            on_change=lambda e: self._mode_changed(e),
        )
        history = sorted(storage.library["history"].values(), key=lambda x: x.get("updated_at", ""), reverse=True)[:10]
        history_controls = [self._anime_tile(item, lambda anime=item: self.open_anime(anime)) for item in history]
        if not history_controls: history_controls = [ft.Text(self.t("no_history"), color=ft.Colors.GREY_500)]
        content = ft.ListView(
            controls=[
                ft.Container(content=ft.Column([
                    ft.Text("Ani-GUI", size=30, weight=ft.FontWeight.BOLD),
                    ft.Text("Mobile", size=14, color=ft.Colors.BLUE_300),
                    ft.Row([query, ft.IconButton(ft.Icons.SEARCH, on_click=lambda e: self.search(query.value))]),
                    mode,
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER), padding=16),
                ft.Container(content=ft.Text(self.t("continue"), size=20, weight=ft.FontWeight.BOLD), padding=ft.Padding.only(left=16, top=10)),
                *history_controls,
            ], expand=True, spacing=6,
        )
        self._set_view([content])

    def _mode_changed(self, e):
        selected = list(e.control.selected)
        if selected:
            self.mode = selected[0]; storage.settings["mode"] = self.mode; storage.save_settings()

    def search(self, query):
        query = (query or "").strip()
        if not query: return
        dialog = self._loading(self.t("searching"))
        def worker():
            try:
                results = self.api.search(query, self.mode)
                self._close_dialog(dialog)
                controls = [self._anime_tile(anime, lambda item=anime: self.open_anime(item), show_episodes=True) for anime in results]
                if not controls: controls = [ft.Text("Sonuç bulunamadı." if self.language == "tr" else "No results found.")]
                self._set_view([ft.ListView(controls=controls, expand=True, spacing=4)], title=f"{query} · {len(results)}", show_nav=False, back=self.show_home)
            except Exception as exc:
                self._close_dialog(dialog); storage.log("error", "search_failed", error=str(exc)); self._snack(str(exc), True)
        threading.Thread(target=worker, daemon=True).start()

    def _anime_tile(self, anime, callback, show_episodes=False):
        subtitle = None
        if show_episodes: subtitle = ft.Text(f"{anime.get('episodes', 0)} {self.t('episodes').lower()}")
        elif anime.get("episode"): subtitle = ft.Text(f"{self.t('episodes')} {anime['episode']}")
        image = ft.Image(src=anime.get("thumbnail"), width=62, height=82, fit=ft.BoxFit.COVER, border_radius=8) if anime.get("thumbnail") else ft.Icon(ft.Icons.MOVIE, size=42)
        return ft.Container(content=ft.ListTile(leading=image, title=ft.Text(anime["title"], max_lines=2, overflow=ft.TextOverflow.ELLIPSIS), subtitle=subtitle, trailing=ft.Icon(ft.Icons.CHEVRON_RIGHT), on_click=lambda e: callback()), padding=ft.Padding.symmetric(horizontal=6))

    def open_anime(self, anime):
        self.current_anime = anime
        dialog = self._loading("Bölümler yükleniyor…" if self.language == "tr" else "Loading episodes…")
        def worker():
            try:
                episodes = self.api.episodes(anime["id"], self.mode)
                self._close_dialog(dialog); self._show_anime_detail(anime, episodes)
            except Exception as exc:
                self._close_dialog(dialog); self._snack(str(exc), True)
        threading.Thread(target=worker, daemon=True).start()

    def _show_anime_detail(self, anime, episodes):
        favorite = storage.is_favorite(anime["id"])
        favorite_button = ft.IconButton(ft.Icons.FAVORITE if favorite else ft.Icons.FAVORITE_BORDER, icon_color=ft.Colors.RED_400, tooltip=self.t("favorites"))
        def toggle(e):
            added = storage.toggle_favorite(anime)
            favorite_button.icon = ft.Icons.FAVORITE if added else ft.Icons.FAVORITE_BORDER
            favorite_button.update(); self._snack(self.t("favorite_added" if added else "favorite_removed"))
        favorite_button.on_click = toggle
        header = ft.Container(content=ft.Row([
            ft.Image(src=anime.get("thumbnail"), width=105, height=145, fit=ft.BoxFit.COVER, border_radius=12),
            ft.Column([ft.Text(anime["title"], size=20, weight=ft.FontWeight.BOLD, max_lines=4), ft.Text(f"{len(episodes)} {self.t('episodes').lower()}"), favorite_button], expand=True),
        ]), padding=14)
        grid = ft.GridView(expand=True, max_extent=72, child_aspect_ratio=1.25, spacing=8, run_spacing=8, padding=12)
        for episode in episodes:
            grid.controls.append(ft.ElevatedButton(str(episode), on_click=lambda e, ep=episode: self._episode_actions(anime, ep)))
        self._set_view([header, ft.Divider(), grid], title=self.t("episodes"), show_nav=False, back=self.show_home)

    def _episode_actions(self, anime, episode):
        dialog = ft.AlertDialog(
            title=ft.Text(f"{anime['title']} · {episode}"),
            actions=[
                ft.ElevatedButton(self.t("watch"), icon=ft.Icons.PLAY_ARROW, on_click=lambda e: self._resolve_episode(dialog, anime, episode, False)),
                ft.OutlinedButton(self.t("download"), icon=ft.Icons.DOWNLOAD, on_click=lambda e: self._resolve_episode(dialog, anime, episode, True)),
                ft.TextButton(self.t("cancel"), on_click=lambda e: self._close_dialog(dialog)),
            ],
        )
        self.page.overlay.append(dialog); dialog.open = True; self.page.update()

    def _resolve_episode(self, action_dialog, anime, episode, download):
        self._close_dialog(action_dialog)
        loading = self._loading(self.t("resolving"))
        def worker():
            attempts = []
            try:
                embeds = provider_ranker.sort(self.api.embeds(anime["id"], episode, self.mode))
                stream = None
                for embed in embeds:
                    name = embed.get("sourceName", "Unknown"); started = time.monotonic()
                    stream = self.api.stream(embed); duration = time.monotonic() - started
                    provider_ranker.record(name, bool(stream), duration, self.api.last_error)
                    attempts.append(f"{name} ({duration:.1f}s): {self.api.last_error or 'OK'}")
                    if stream: break
                self._close_dialog(loading)
                if not stream:
                    self._show_error(self.t("providers_failed"), attempts); return
                storage.mark_watched(anime, episode)
                if download:
                    download_manager.start(stream, anime, episode); self._snack("İndirme başlatıldı." if self.language == "tr" else "Download started.")
                else:
                    self.show_player(anime, episode, stream)
            except Exception as exc:
                self._close_dialog(loading); storage.log("error", "episode_resolve_failed", error=str(exc)); self._show_error(str(exc), attempts)
        threading.Thread(target=worker, daemon=True).start()

    def _show_error(self, message, attempts=None):
        dialog = ft.AlertDialog(
            title=ft.Text("Hata" if self.language == "tr" else "Error"),
            content=ft.Container(content=ft.Text(message + ("\n\n" + "\n".join(attempts) if attempts else ""), selectable=True), width=500, height=260),
            actions=[ft.TextButton("OK", on_click=lambda e: self._close_dialog(dialog))], scrollable=True,
        )
        self.page.overlay.append(dialog); dialog.open = True; self.page.update()

    def show_player(self, anime, episode, stream):
        media = ftv.VideoMedia(stream, http_headers={"Referer": "https://mkissa.to", "User-Agent": AniApi.AGENT}, extras={"title": f"{anime['title']} · {episode}"})
        self.video = ftv.Video(
            playlist=[media], autoplay=True, wakelock=True, fit=ft.BoxFit.CONTAIN,
            controls=ftv.AdaptiveVideoControls(), expand=True,
            on_error=lambda e: self._show_error(str(e.data)),
        )
        external = ft.OutlinedButton(self.t("external_player"), icon=ft.Icons.OPEN_IN_NEW, on_click=lambda e: self.page.launch_url(stream))
        self._set_view([
            ft.Container(content=self.video, bgcolor=ft.Colors.BLACK, expand=True),
            ft.Container(content=ft.Row([external], alignment=ft.MainAxisAlignment.CENTER), padding=10),
        ], title=f"{anime['title']} · {episode}", show_nav=False, back=lambda: self.open_anime(anime))

    def show_favorites(self):
        self.page.navigation_bar.selected_index = 1
        items = list(storage.library["favorites"].values())
        controls = [self._anime_tile(item, lambda anime=item: self.open_anime(anime)) for item in items] or [ft.Text(self.t("no_favorites"), color=ft.Colors.GREY_500)]
        self._set_view([ft.ListView(controls=controls, expand=True)], title=self.t("favorites"))

    def show_downloads(self):
        self.page.navigation_bar.selected_index = 2
        controls = []
        for item in reversed(list(download_manager.items.values())):
            progress = ft.ProgressBar(value=item.get("progress", 0))
            actions = []
            if item.get("status") == "completed" and os.path.exists(item.get("path", "")):
                actions.append(ft.IconButton(ft.Icons.PLAY_ARROW, tooltip=self.t("open"), on_click=lambda e, data=item: self._play_download(data)))
            elif item.get("status") == "paused":
                actions.append(ft.IconButton(ft.Icons.PLAY_ARROW, tooltip=self.t("resume"), on_click=lambda e, item_id=item["id"]: download_manager.resume(item_id)))
            elif item.get("status") == "downloading":
                actions.append(ft.IconButton(ft.Icons.PAUSE, tooltip=self.t("pause"), on_click=lambda e, item_id=item["id"]: download_manager.pause(item_id)))
            actions.append(ft.IconButton(ft.Icons.DELETE, on_click=lambda e, item_id=item["id"]: download_manager.remove(item_id)))
            controls.append(ft.Card(content=ft.Container(content=ft.Column([
                ft.Row([ft.Text(f"{item['title']} · {item['episode']}", expand=True, max_lines=2), *actions]), progress,
                ft.Row([ft.Text(item.get("status", "")), ft.Text(f"{int(item.get('progress', 0)*100)}% · {item.get('speed')} · {item.get('eta')}")], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            ]), padding=12)))
        if not controls: controls = [ft.Text(self.t("no_downloads"), color=ft.Colors.GREY_500)]
        self._set_view([ft.ListView(controls=controls, expand=True)], title=self.t("downloads"))

    def _downloads_updated(self):
        if self.page.navigation_bar.selected_index == 2:
            try: self.show_downloads()
            except Exception: pass

    def _play_download(self, item):
        anime = {"id": item.get("anime_id"), "title": item["title"], "thumbnail": item.get("thumbnail")}
        self.show_player(anime, item["episode"], item["path"])

    def show_settings(self):
        self.page.navigation_bar.selected_index = 3
        language = ft.Dropdown(label=self.t("language"), value=self.language, options=[ft.dropdown.Option("tr", "Türkçe"), ft.dropdown.Option("en", "English")])
        mode = ft.Dropdown(label=self.t("mode"), value=self.mode, options=[ft.dropdown.Option("sub", "SUB"), ft.dropdown.Option("dub", "DUB")])
        quality = ft.Dropdown(label=self.t("quality"), value=storage.settings.get("quality", "best"), options=[ft.dropdown.Option("best", "Best"), ft.dropdown.Option("1080", "1080p"), ft.dropdown.Option("720", "720p"), ft.dropdown.Option("480", "480p")])
        updates = ft.Switch(label=self.t("autoupdate"), value=storage.settings.get("check_updates", True))
        status = ft.Text("")
        logs = ft.Text("\n".join(storage.logs(60)) or "—", size=10, selectable=True)

        def save(e):
            storage.settings.update({"language": language.value, "mode": mode.value, "quality": quality.value, "check_updates": updates.value})
            storage.save_settings(); self.language = language.value; self.mode = mode.value; self._build_navigation(); self.show_settings(); self._snack("Kaydedildi" if self.language == "tr" else "Saved")

        def health(e):
            status.value = self.t("searching"); self.page.update()
            def worker():
                result = self.api.health(); status.value = json.dumps(result, ensure_ascii=False); status.color = ft.Colors.GREEN_400 if result.get("ok") else ft.Colors.RED_400; self.page.update()
            threading.Thread(target=worker, daemon=True).start()

        def clear(e):
            try: storage.log_path.write_text("", encoding="utf-8")
            except Exception: pass
            logs.value = "—"; self.page.update()

        controls = [
            ft.ExpansionTile(title=ft.Text(self.t("settings")), leading=ft.Icons.TUNE, controls=[language, mode, quality, updates, ft.ElevatedButton(self.t("save"), icon=ft.Icons.SAVE, on_click=save)], expanded=True),
            ft.ExpansionTile(title=ft.Text(self.t("health")), leading=ft.Icons.MONITOR_HEART, controls=[ft.ElevatedButton(self.t("health"), icon=ft.Icons.REFRESH, on_click=health), status]),
            ft.ExpansionTile(title=ft.Text(self.t("logs")), leading=ft.Icons.BUG_REPORT, controls=[ft.Container(content=logs, height=220, padding=8, bgcolor="#20000000"), ft.TextButton(self.t("clear"), on_click=clear)]),
            ft.ListTile(leading=ft.Icon(ft.Icons.INFO), title=ft.Text("Ani-GUI Mobile 0.1.0"), subtitle=ft.Text(str(storage.root))),
        ]
        self._set_view([ft.ListView(controls=controls, expand=True)], title=self.t("settings"))

    def _background_update_check(self):
        try:
            response = requests.get("https://api.github.com/repos/utkudisci/Ani-GUI/commits/master", timeout=10)
            response.raise_for_status(); data = response.json()
            storage.log("info", "update_checked", remote=data.get("sha", "")[:7], message=data.get("commit", {}).get("message", "").splitlines()[0])
        except Exception as exc:
            storage.log("warning", "update_check_failed", error=str(exc))


def main(page: ft.Page):
    MobileApp(page)


if __name__ == "__main__":
    ft.run(main)
