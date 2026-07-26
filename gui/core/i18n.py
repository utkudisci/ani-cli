from core.settings_manager import settings_manager


TRANSLATIONS = {
    "tr": {
        "settings": "Seçenekler", "close": "Kapat", "save": "Kaydet", "cancel": "İptal",
        "playback": "Oynatma", "default_mode": "Varsayılan mod", "default_player": "Varsayılan oynatıcı",
        "appearance": "Görünüm ve Dil", "theme": "Tema", "language": "Dil",
        "downloads": "İndirmeler", "download_location": "İndirme konumu", "browse": "Gözat…",
        "discord": "Discord RPC", "enable_discord": "Discord RPC'yi etkinleştir",
        "show_episode": "Bölüm numarasını göster", "show_title": "Anime adını göster",
        "setup": "Kurulum Sihirbazı", "health_logs": "Sağlık ve Loglar", "updates": "Güncellemeler",
        "auto_check": "Açılışta güncellemeleri kontrol et", "check_now": "Şimdi kontrol et",
        "run_checks": "Kontrolleri çalıştır", "export_diagnostics": "Tanılama paketini dışa aktar",
        "clear_logs": "Logları temizle", "search": "Anime ara…", "searching": "Aranıyor…",
        "no_stream": "Geçerli yayın bağlantısı bulunamadı.", "downloads_title": "İndirmeler",
        "continue_watching": "İzlemeye Devam Et", "favorites": "Favoriler",
        "no_recent": "Henüz izleme geçmişi yok.", "no_favorites": "Henüz favori eklenmedi.",
        "watch": "İzle", "download": "İndir", "loading_episodes": "Bölümler yükleniyor…",
        "no_downloads": "Aktif indirme yok",
    },
    "en": {
        "settings": "Settings", "close": "Close", "save": "Save", "cancel": "Cancel",
        "playback": "Playback", "default_mode": "Default mode", "default_player": "Default player",
        "appearance": "Appearance & Language", "theme": "Theme", "language": "Language",
        "downloads": "Downloads", "download_location": "Download location", "browse": "Browse…",
        "discord": "Discord RPC", "enable_discord": "Enable Discord RPC",
        "show_episode": "Show episode number", "show_title": "Show anime title",
        "setup": "Setup Wizard", "health_logs": "Health & Logs", "updates": "Updates",
        "auto_check": "Check for updates at startup", "check_now": "Check now",
        "run_checks": "Run checks", "export_diagnostics": "Export diagnostics bundle",
        "clear_logs": "Clear logs", "search": "Search anime…", "searching": "Searching…",
        "no_stream": "No valid stream link was found.", "downloads_title": "Downloads",
        "continue_watching": "Continue Watching", "favorites": "Favorites",
        "no_recent": "No recent anime yet.", "no_favorites": "No favorites yet.",
        "watch": "Watch", "download": "Download", "loading_episodes": "Loading episodes…",
        "no_downloads": "No active downloads",
    },
}


def tr(key, language=None):
    lang = language or settings_manager.get("appearance", "language") or "tr"
    return TRANSLATIONS.get(lang, TRANSLATIONS["en"]).get(key, key)
