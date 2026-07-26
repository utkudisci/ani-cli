import os
import threading

import flet as ft

from core.diagnostics import diagnostics
from core.i18n import tr
from core.provider_manager import provider_manager
from core.settings_manager import settings_manager
from core.system_manager import system_manager
from core.theme_manager import theme_manager
from core.update_manager import update_manager


class SettingsView(ft.Container):
    def __init__(self, page: ft.Page, on_close=None):
        super().__init__()
        self._page = page
        self.on_close_callback = on_close
        self.current_settings = settings_manager.get_all()
        self.language = settings_manager.get("appearance", "language") or "tr"
        self.last_health = {}
        self.install_controls = {}
        self._build_ui()
        theme_manager.add_listener(self._on_theme_update)

    def _build_ui(self):
        self.mode_dropdown = ft.Dropdown(
            label=tr("default_mode", self.language),
            options=[ft.dropdown.Option("sub", "Sub"), ft.dropdown.Option("dub", "Dub")],
            value=settings_manager.get("playback", "default_mode"), width=300,
        )
        self.player_dropdown = ft.Dropdown(
            label=tr("default_player", self.language),
            options=[ft.dropdown.Option("mpv", "MPV"), ft.dropdown.Option("vlc", "VLC")],
            value=settings_manager.get("playback", "default_player"), width=300,
        )
        self.language_dropdown = ft.Dropdown(
            label=tr("language", self.language),
            options=[ft.dropdown.Option("tr", "Türkçe"), ft.dropdown.Option("en", "English")],
            value=self.language, width=300,
        )
        self.theme_dropdown = ft.Dropdown(
            label=tr("theme", self.language),
            options=[ft.dropdown.Option(key, theme.name) for key, theme in theme_manager.get_all_themes().items()],
            value=theme_manager.get_theme().key, width=300,
            on_select=self._on_theme_change,
        )
        self.download_location = ft.TextField(
            label=tr("download_location", self.language),
            value=settings_manager.get("downloads", "location"), read_only=True, expand=True,
        )
        self.rpc_enabled = ft.Switch(label=tr("enable_discord", self.language), value=settings_manager.get("discord_rpc", "enabled"))
        self.rpc_show_episode = ft.Switch(label=tr("show_episode", self.language), value=settings_manager.get("discord_rpc", "show_episode"))
        self.rpc_show_title = ft.Switch(label=tr("show_title", self.language), value=settings_manager.get("discord_rpc", "show_title"))
        self.auto_update = ft.Switch(label=tr("auto_check", self.language), value=settings_manager.get("updates", "check_automatically"))
        self.logging_enabled = ft.Switch(
            label="Tanılama loglarını etkinleştir" if self.language == "tr" else "Enable diagnostic logs",
            value=settings_manager.get("diagnostics", "logging_enabled"),
        )
        self.update_status = ft.Text("", size=12)
        self.health_controls = ft.Column(spacing=4)
        self.log_view = ft.Text("\n".join(diagnostics.tail(80)) or "Log yok.", size=10, selectable=True)
        self.export_status = ft.Text("", size=11)

        setup_controls = []
        for dependency, title, required in (
            ("mpv", "MPV", True),
            ("aria2c", "aria2c", False),
        ):
            setup_controls.append(self._dependency_row(dependency, title, required))
        setup_controls.extend([
            ft.Text(
                "yt-dlp ve Python paketleri requirements üzerinden yönetilir."
                if self.language == "tr" else
                "yt-dlp and Python packages are managed through requirements.",
                size=11, color=ft.Colors.GREY_400,
            ),
            ft.ElevatedButton(
                "Kurulumu tamamla" if self.language == "tr" else "Finish setup",
                icon=ft.Icons.CHECK_CIRCLE, on_click=self._finish_setup,
            ),
        ])

        tiles = [
            self._tile(tr("setup", self.language), ft.Icons.CONSTRUCTION, setup_controls,
                       expanded=not bool(settings_manager.get("setup", "completed"))),
            self._tile(tr("playback", self.language), ft.Icons.PLAY_CIRCLE, [self.mode_dropdown, self.player_dropdown]),
            self._tile(tr("appearance", self.language), ft.Icons.PALETTE, [self.theme_dropdown, self.language_dropdown]),
            self._tile(tr("downloads", self.language), ft.Icons.DOWNLOAD, [
                ft.Row([self.download_location, ft.ElevatedButton(tr("browse", self.language), icon=ft.Icons.FOLDER_OPEN, on_click=self._browse_folder)]),
                ft.Text("aria2c kuruluysa parçalı ve devam ettirilebilir indirme otomatik kullanılır.", size=11, color=ft.Colors.GREY_400),
            ]),
            self._tile(tr("discord", self.language), ft.Icons.DISCORD, [self.rpc_enabled, self.rpc_show_episode, self.rpc_show_title]),
            self._tile(tr("updates", self.language), ft.Icons.SYSTEM_UPDATE, [
                self.auto_update,
                ft.ElevatedButton(tr("check_now", self.language), icon=ft.Icons.REFRESH, on_click=self._check_updates),
                self.update_status,
                ft.Text("Güncellemeler otomatik uygulanmaz; kullanıcı dosyaları korunur.", size=11, color=ft.Colors.GREY_400),
            ]),
            self._tile(tr("health_logs", self.language), ft.Icons.MONITOR_HEART, [
                self.logging_enabled,
                ft.Row([
                    ft.ElevatedButton(tr("run_checks", self.language), icon=ft.Icons.PLAY_ARROW, on_click=self._run_health_checks),
                    ft.OutlinedButton(tr("export_diagnostics", self.language), icon=ft.Icons.ARCHIVE, on_click=self._export_diagnostics),
                    ft.IconButton(ft.Icons.DELETE_SWEEP, tooltip=tr("clear_logs", self.language), on_click=self._clear_logs),
                ], wrap=True),
                self.export_status,
                self.health_controls,
                ft.Container(content=self.log_view, bgcolor="#16000000", padding=8, border_radius=6, height=150),
            ]),
        ]

        self.content = ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Text(tr("settings", self.language), size=24, weight=ft.FontWeight.BOLD),
                    ft.IconButton(ft.Icons.CLOSE, on_click=self._close, tooltip=tr("close", self.language)),
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                ft.Divider(),
                ft.ListView(controls=tiles, spacing=6, expand=True),
                ft.Row([
                    ft.ElevatedButton(tr("save", self.language), icon=ft.Icons.SAVE, on_click=self._save_settings, bgcolor="#1976D2", color="#FFFFFF"),
                    ft.OutlinedButton(tr("cancel", self.language), icon=ft.Icons.CANCEL, on_click=self._close),
                ], alignment=ft.MainAxisAlignment.END),
            ], spacing=10),
            padding=24, bgcolor=theme_manager.get_theme().surface,
            border_radius=10, width=680, height=760,
        )
        self.settings_panel = self.content
        self.bgcolor = "rgba(0, 0, 0, 0.55)"
        self.alignment = ft.Alignment(0, 0)
        self.expand = True

    def _tile(self, title, icon, controls, expanded=False):
        return ft.ExpansionTile(
            title=ft.Text(title, weight=ft.FontWeight.W_600), leading=icon,
            controls=controls, controls_padding=ft.Padding.only(left=20, right=20, bottom=16),
            expanded=expanded, maintain_state=True,
        )

    def _dependency_row(self, dependency, title, required):
        installed = system_manager.find(dependency)
        status = ft.Text(size=12)
        progress = ft.ProgressBar(value=None, visible=False, expand=True)
        button = ft.ElevatedButton()
        container = ft.Container(content=button, border_radius=8)
        self.install_controls[dependency] = {"status": status, "progress": progress, "button": button, "container": container}
        self._paint_dependency(dependency, installed)
        subtitle = "Gerekli" if required else "İsteğe bağlı · hızlı ve devam ettirilebilir indirme"
        return ft.Container(content=ft.Column([
            ft.Row([ft.Column([ft.Text(title, weight=ft.FontWeight.BOLD), ft.Text(subtitle, size=10, color=ft.Colors.GREY_400)], expand=True), container]),
            progress, status,
        ], spacing=5), padding=8)

    def _paint_dependency(self, dependency, path=None):
        controls = self.install_controls[dependency]
        button, container, status, progress = controls["button"], controls["container"], controls["status"], controls["progress"]
        if path:
            button.content = "Kurulu" if self.language == "tr" else "Installed"
            button.icon = ft.Icons.VERIFIED
            button.bgcolor, button.color, button.elevation = ft.Colors.GREEN_600, ft.Colors.WHITE, 10
            button.on_click = None
            container.shadow = ft.BoxShadow(blur_radius=18, spread_radius=2, color="#8032CD32")
            status.value, status.color = str(path), ft.Colors.GREEN_400
            progress.visible = False
        else:
            button.content = "İndir ve kur" if self.language == "tr" else "Download & install"
            button.icon, button.bgcolor, button.color, button.elevation = ft.Icons.DOWNLOAD, None, None, 1
            button.on_click = lambda e, name=dependency: self._install_dependency(name)
            button.disabled = False
            container.shadow = None
            status.value, status.color = "Kurulu değil", ft.Colors.AMBER_400

    def _install_dependency(self, dependency):
        controls = self.install_controls[dependency]
        controls["button"].disabled = True
        controls["progress"].visible = True
        controls["status"].color = ft.Colors.BLUE_300
        controls["status"].value = "Winget hazırlanıyor…"
        self._page.update()

        def progress(elapsed, line):
            stage = "İndiriliyor / kuruluyor"
            lowered = line.lower()
            if "download" in lowered: stage = "İndiriliyor"
            elif "install" in lowered: stage = "Kuruluyor"
            controls["status"].value = f"{stage}… ({elapsed} sn)"
            try: self._page.update()
            except Exception: pass

        def worker():
            success, message = system_manager.run_install(dependency, progress)
            if success:
                self._paint_dependency(dependency, system_manager.find(dependency) or "Winget")
                if dependency == "aria2c":
                    try:
                        from core.download_manager import download_manager
                        download_manager.has_aria2 = bool(system_manager.find("aria2c"))
                    except Exception:
                        pass
            else:
                self._paint_dependency(dependency, None)
                controls["status"].value = f"Kurulum başarısız: {message}"
                controls["status"].color = ft.Colors.RED_300
            try: self._page.update()
            except Exception: pass

        threading.Thread(target=worker, daemon=True).start()

    def _run_health_checks(self, e):
        self.health_controls.controls = [ft.ProgressRing(width=24, height=24)]
        self._page.update()
        def worker():
            self.last_health = system_manager.health_check()
            self.health_controls.controls = [
                ft.Row([ft.Icon(ft.Icons.CHECK_CIRCLE if item["ok"] else ft.Icons.ERROR, color=ft.Colors.GREEN_400 if item["ok"] else ft.Colors.RED_400),
                        ft.Text(name, width=100, weight=ft.FontWeight.BOLD), ft.Text(item["detail"], size=11, expand=True)])
                for name, item in self.last_health.items()
            ]
            self.log_view.value = "\n".join(diagnostics.tail(80))
            try: self._page.update()
            except Exception: pass
        threading.Thread(target=worker, daemon=True).start()

    def _check_updates(self, e):
        self.update_status.value = "Kontrol ediliyor…"
        self._page.update()
        def worker():
            result = update_manager.check()
            if not result.get("ok"):
                self.update_status.value = f"Kontrol başarısız: {result.get('error')}"
                self.update_status.color = ft.Colors.RED_300
            elif result.get("update_available"):
                self.update_status.value = f"Yeni güncelleme var: {result['remote']} · {result.get('message', '')}"
                self.update_status.color = ft.Colors.AMBER_300
            else:
                self.update_status.value = "Uygulama güncel."
                self.update_status.color = ft.Colors.GREEN_400
            try: self._page.update()
            except Exception: pass
        threading.Thread(target=worker, daemon=True).start()

    def _export_diagnostics(self, e):
        try:
            path = diagnostics.export(health=self.last_health, provider_stats=provider_manager.snapshot())
            self.export_status.value = f"Tanılama paketi: {path}"
            self.export_status.color = ft.Colors.GREEN_400
        except Exception as exc:
            self.export_status.value = f"Dışa aktarma başarısız: {exc}"
            self.export_status.color = ft.Colors.RED_300
        self._page.update()

    def _clear_logs(self, e):
        diagnostics.clear()
        self.log_view.value = "Loglar temizlendi."
        self._page.update()

    def _finish_setup(self, e):
        settings_manager.set("setup", "completed", True)
        settings_manager.save_settings()
        snackbar = ft.SnackBar(content=ft.Text("Kurulum kontrolü tamamlandı."))
        self._page.overlay.append(snackbar); snackbar.open = True; self._page.update()

    def _browse_folder(self, e):
        def pick():
            try:
                from tkinter import Tk, filedialog
                root = Tk(); root.withdraw(); root.attributes("-topmost", True)
                selected = filedialog.askdirectory(title="Select Download Folder", initialdir=self.download_location.value or "C:\\")
                root.destroy()
                if selected:
                    self.download_location.value = selected; self._page.update()
            except Exception as exc:
                diagnostics.log("error", "settings", "Folder picker failed", error=str(exc))
        threading.Thread(target=pick, daemon=True).start()

    def _save_settings(self, e):
        settings_manager.set("playback", "default_mode", self.mode_dropdown.value)
        settings_manager.set("playback", "default_player", self.player_dropdown.value)
        settings_manager.set("downloads", "location", self.download_location.value)
        settings_manager.set("discord_rpc", "enabled", self.rpc_enabled.value)
        settings_manager.set("discord_rpc", "show_episode", self.rpc_show_episode.value)
        settings_manager.set("discord_rpc", "show_title", self.rpc_show_title.value)
        settings_manager.set("appearance", "theme", self.theme_dropdown.value)
        settings_manager.set("appearance", "language", self.language_dropdown.value)
        settings_manager.set("updates", "check_automatically", self.auto_update.value)
        settings_manager.set("diagnostics", "logging_enabled", self.logging_enabled.value)
        settings_manager.save_settings()
        theme_manager.set_theme(self.theme_dropdown.value, self._page)
        diagnostics.log("info", "settings", "Settings saved", language=self.language_dropdown.value)
        self._close(e)

    def _on_theme_change(self, e):
        self.theme_dropdown.value = e.data
        theme_manager.set_theme(e.data, self._page)

    def _on_theme_update(self):
        if hasattr(self, "settings_panel"):
            self.settings_panel.bgcolor = theme_manager.get_theme().surface
            try: self.settings_panel.update()
            except Exception: pass

    def _close(self, e=None):
        theme_manager.remove_listener(self._on_theme_update)
        if self.on_close_callback:
            self.on_close_callback()
