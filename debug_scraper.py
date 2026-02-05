
import urllib.request
import re
from gui.core.scraper import AniScraper

def test_stream_link():
    scraper = AniScraper()
    # URL provided by user (One Piece Ep 1014)
    original_url = "https://goload.pro/streaming.php?id=MTg0NTY4&title=One+Piece&typesub=SUB&sub=&cover=aW1hZ2VzL2FuaW1lL09uZS1waWVjZS5qcGc="
    
    import subprocess
    import shutil
    
    # Test yt-dlp
    ytdlp_path = shutil.which("yt-dlp")
    if not ytdlp_path:
        print("Error: yt-dlp not found in PATH.")
        return

    print(f"Using yt-dlp: {ytdlp_path}")
    print("Extracting link via yt-dlp...")
    
    cmd = [
        ytdlp_path,
        "-g", # get url
        original_url
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='ignore')
        print(f"Return Code: {result.returncode}")
        print(f"Output: {result.stdout.strip()}")
        print(f"Error: {result.stderr.strip()}")
        
    except Exception as e:
        print(f"yt-dlp failed: {e}")

if __name__ == "__main__":
    test_stream_link()
