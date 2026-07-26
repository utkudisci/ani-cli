TRANSLATIONS = {
    "tr": {
        "home": "Ana Sayfa", "favorites": "Favoriler", "downloads": "İndirilenler", "settings": "Ayarlar",
        "search": "Anime ara…", "searching": "Aranıyor…", "episodes": "Bölümler", "watch": "İzle",
        "download": "İndir", "continue": "İzlemeye Devam", "no_history": "Henüz izleme geçmişi yok.",
        "no_favorites": "Henüz favori eklenmedi.", "no_downloads": "Henüz indirme yok.",
        "resolving": "Yayın bağlantısı çözülüyor…", "providers_failed": "Tüm sağlayıcılar başarısız oldu.",
        "external_player": "Harici oynatıcıda aç", "mode": "Dil modu", "language": "Uygulama dili",
        "autoupdate": "Açılışta güncelleme kontrolü", "health": "Bağlantı kontrolü", "logs": "Loglar",
        "clear": "Temizle", "save": "Kaydet", "back": "Geri", "favorite_added": "Favorilere eklendi",
        "favorite_removed": "Favorilerden çıkarıldı", "retry": "Tekrar dene", "cancel": "İptal",
        "pause": "Duraklat", "resume": "Devam et", "open": "Aç", "quality": "Kalite",
    },
    "en": {
        "home": "Home", "favorites": "Favorites", "downloads": "Downloads", "settings": "Settings",
        "search": "Search anime…", "searching": "Searching…", "episodes": "Episodes", "watch": "Watch",
        "download": "Download", "continue": "Continue Watching", "no_history": "No watch history yet.",
        "no_favorites": "No favorites yet.", "no_downloads": "No downloads yet.",
        "resolving": "Resolving stream…", "providers_failed": "All providers failed.",
        "external_player": "Open in external player", "mode": "Audio mode", "language": "App language",
        "autoupdate": "Check for updates at startup", "health": "Connection check", "logs": "Logs",
        "clear": "Clear", "save": "Save", "back": "Back", "favorite_added": "Added to favorites",
        "favorite_removed": "Removed from favorites", "retry": "Retry", "cancel": "Cancel",
        "pause": "Pause", "resume": "Resume", "open": "Open", "quality": "Quality",
    },
}


def text(key, language="tr"):
    return TRANSLATIONS.get(language, TRANSLATIONS["en"]).get(key, key)
