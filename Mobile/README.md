# Ani-GUI Mobile

Ani-GUI'nin Android için bağımsız Flet sürümüdür. Masaüstü klasörüne veya Windows araçlarına çalışma zamanında ihtiyaç duymaz.

## Özellikler

- SUB/DUB arama ve bölüm listesi
- Güncel Mkissa/AllAnime şifreli bölüm protokolü
- Başarı oranına göre akıllı sağlayıcı sıralaması
- Android uyumlu uygulama içi HLS/MP4 oynatıcı
- Harici oynatıcı yedeği
- Favoriler ve izleme geçmişi
- Uygulama özel depolamasına indirme, duraklatma ve devam ettirme
- Türkçe/İngilizce arayüz
- Sağlık kontrolü, kalıcı loglar ve güncelleme bilgisi

## Masaüstünde geliştirme testi

```powershell
python -m pip install -r requirements.txt
python src\main.py
```

## Android APK oluşturma

Windows'ta önce **Ayarlar > Sistem > Geliştiriciler için > Geliştirici Modu** seçeneğini açın. Flutter eklentileri derleme sırasında sembolik bağlantı kullandığı için bu ayar gereklidir.

Ardından önerilen tek komut:

```powershell
.\build_android.ps1
```

Elle derlemek isterseniz:

```powershell
$flet = Join-Path (python -c "import sysconfig; print(sysconfig.get_path('scripts'))") "flet.exe"
& $flet build apk --arch arm64-v8a --yes --no-rich-output --no-compile-packages
```

İlk derlemede Flet gerekirse Flutter, JDK 17 ve Android SDK'yı otomatik indirir. Çıktı `build\apk` altında oluşur. Varsayılan hedef güncel Android telefonların çoğunda kullanılan `arm64-v8a` mimarisidir. Eski 32-bit cihazlar veya emülatör için `--arch` değerini sırasıyla `armeabi-v7a` veya `x86_64` yapabilirsiniz.

Play Store için:

```powershell
& $flet build aab
```

Yayınlamadan önce imzalama anahtarını güvenli ortam değişkenleriyle yapılandırın. Keystore veya parolaları depoya eklemeyin.

## Android depolama modeli

Ayarlar, favoriler, geçmiş, loglar ve indirilen videolar `FLET_APP_STORAGE_DATA` altındaki uygulama özel alanında tutulur. Bu nedenle geniş depolama izni istenmez. Uygulama kaldırılırsa Android bu verileri silebilir.

## Not

İçerik sağlayıcıları zaman içinde protokol değiştirebilir. Sağlık ekranı ve sağlayıcı logları sorunları teşhis etmek için kullanılabilir.
