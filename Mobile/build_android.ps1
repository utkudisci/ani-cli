$ErrorActionPreference = "Stop"
$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"
$env:FLET_CLI_NO_RICH_OUTPUT = "1"

# Flet installs these toolchains under the current Windows user profile.
# Export their locations explicitly because Gradle does not always inherit
# Flet's temporary environment on a first-time installation.
$androidSdk = Join-Path $env:USERPROFILE "Android\sdk"
$jdk = Get-ChildItem -LiteralPath (Join-Path $env:USERPROFILE "java") -Directory -ErrorAction SilentlyContinue |
    Sort-Object LastWriteTime -Descending |
    Select-Object -First 1 -ExpandProperty FullName
if (Test-Path $androidSdk) {
    $env:ANDROID_HOME = $androidSdk
    $env:ANDROID_SDK_ROOT = $androidSdk
    $env:Path = (Join-Path $androidSdk "platform-tools") + ";" + $env:Path
}
if ($jdk -and (Test-Path $jdk)) {
    $env:JAVA_HOME = $jdk
    $env:Path = (Join-Path $jdk "bin") + ";" + $env:Path
}

$devMode = Get-ItemPropertyValue `
    -Path "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\AppModelUnlock" `
    -Name "AllowDevelopmentWithoutDevLicense" `
    -ErrorAction SilentlyContinue
if ($devMode -ne 1) {
    throw "Windows Geliştirici Modu gerekli: Ayarlar > Sistem > Geliştiriciler için > Geliştirici Modu seçeneğini açın, ardından betiği tekrar çalıştırın."
}

python -m pip install -r requirements.txt
$scriptsPath = python -c "import sysconfig; print(sysconfig.get_path('scripts'))"
$fletExe = Join-Path $scriptsPath "flet.exe"

if (-not (Test-Path -LiteralPath $fletExe)) {
    throw "Flet CLI bulunamadı: $fletExe"
}

& $fletExe doctor
& $fletExe build apk --arch arm64-v8a --yes --no-rich-output --no-compile-packages
