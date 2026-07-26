
import requests
import json
import re
import base64
import hashlib
import time
from typing import List, Dict, Optional
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from yt_dlp import YoutubeDL

class AniScraper:
    BASE_URL = "https://allanime.day"
    API_URL = "https://api.mkissa.net/api"
    REFERER = "https://mkissa.to"
    CDN_URL = "https://cdn.mkissa.net/all/mk/_app/immutable"
    QUERY_HASH = "f4662f4b7510b26795dd53ef824a0bf1740fbbc5d1273fab18222ac831bca8d0"
    AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:150.0) Gecko/20100101 Firefox/150.0"

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": self.AGENT,
            "Referer": self.REFERER,
            "Origin": self.REFERER,
        })
        self._api_key = None
        self._api_epoch = None
        self.last_error = None

    def _graphql(self, query: str, variables: Dict) -> Dict:
        response = self.session.post(
            self.API_URL,
            json={"variables": variables, "query": query},
            timeout=20,
        )
        response.raise_for_status()
        data = response.json()
        if data.get("errors"):
            raise RuntimeError(data["errors"][0].get("message", "GraphQL request failed"))
        return data

    def _fetch_api_key(self) -> None:
        page = self.session.get(self.REFERER, timeout=20)
        page.raise_for_status()

        epoch_match = re.search(r'"epoch":(\d+)', page.text)
        part_b_match = re.search(r'"partB":"([^"]+)"', page.text)
        app_match = re.search(
            re.escape(self.CDN_URL) + r'/entry/app\.[A-Za-z0-9_.-]+\.js',
            page.text,
        )
        if not (epoch_match and part_b_match and app_match):
            raise RuntimeError("Could not discover mkissa API key metadata")

        app = self.session.get(app_match.group(0), timeout=20)
        app.raise_for_status()
        chunks = re.findall(r'"\.\./chunks/([A-Za-z0-9_.-]+\.js)"', app.text)[:5]

        mask_hex = None
        for chunk in chunks:
            response = self.session.get(f"{self.CDN_URL}/chunks/{chunk}", timeout=20)
            response.raise_for_status()
            match = re.search(r'(?<![0-9a-f])[0-9a-f]{64}(?![0-9a-f])', response.text)
            if match:
                mask_hex = match.group(0)
                break

        if not mask_hex:
            raise RuntimeError("Could not discover mkissa API key mask")

        part_b = base64.b64decode(part_b_match.group(1))
        mask = bytes.fromhex(mask_hex)
        if len(part_b) != 32 or len(mask) != 32:
            raise RuntimeError("Invalid mkissa API key material")

        self._api_epoch = int(epoch_match.group(1))
        self._api_key = bytes(a ^ b for a, b in zip(mask, part_b))

    def _make_aa_req(self) -> str:
        if self._api_key is None or self._api_epoch is None:
            self._fetch_api_key()

        timestamp = int(time.time()) // 300 * 300 * 1000
        iv_seed = f"{self._api_epoch}:{self.QUERY_HASH}:{timestamp}".encode()
        iv = hashlib.sha256(iv_seed).digest()[:12]
        payload = json.dumps(
            {"v": 1, "ts": timestamp, "epoch": self._api_epoch, "qh": self.QUERY_HASH},
            separators=(",", ":"),
        ).encode()
        encrypted = AESGCM(self._api_key).encrypt(iv, payload, None)
        return base64.b64encode(b"\x01" + iv + encrypted).decode()

    def _decode_episode_response(self, data: Dict) -> Dict:
        encoded = data.get("tobeparsed") or data.get("data", {}).get("tobeparsed")
        if not encoded:
            return data
        if self._api_key is None:
            raise RuntimeError("Missing mkissa response decryption key")

        raw = base64.b64decode(encoded)
        if len(raw) < 30 or raw[0] != 1:
            raise RuntimeError("Invalid encrypted mkissa response")
        decrypted = AESGCM(self._api_key).decrypt(raw[1:13], raw[13:], None)
        decoded = json.loads(decrypted)
        return decoded if "data" in decoded else {"data": decoded}

    def _extract_with_ytdlp(self, url: str) -> Optional[str]:
        try:
            with YoutubeDL({
                "quiet": True,
                "no_warnings": True,
                "socket_timeout": 10,
                "http_headers": {"Referer": self.REFERER},
            }) as ydl:
                info = ydl.extract_info(url, download=False)
            candidate = info.get("url") if info else None
            if candidate and candidate != url and "/embed" not in candidate:
                print("Found stream URL with yt-dlp")
                return candidate
        except Exception as exc:
            print(f"yt-dlp could not extract this provider: {exc}")
        return None

    def search_anime(self, query: str, mode: str = "sub") -> List[Dict]:
        """
        Searches for anime.
        Equivalent to `search_anime` in shell script.
        """
        search_gql = """
        query( $search: SearchInput $limit: Int $page: Int $translationType: VaildTranslationTypeEnumType $countryOrigin: VaildCountryOriginEnumType ) {
            shows( search: $search limit: $limit page: $page translationType: $translationType countryOrigin: $countryOrigin ) {
                edges { _id name availableEpisodes __typename thumbnail }
            }
        }
        """
        
        variables = {
            "search": {
                "allowAdult": False,
                "allowUnknown": False,
                "query": query
            },
            "limit": 40,
            "page": 1,
            "translationType": mode,
            "countryOrigin": "ALL"
        }

        try:
            data = self._graphql(search_gql, variables)
            
            results = []
            if "data" in data and "shows" in data["data"]:
                for edge in data["data"]["shows"]["edges"]:
                    results.append({
                        "id": edge["_id"],
                        "title": edge["name"],
                        "episodes": edge.get("availableEpisodes", {}).get(mode, 0),
                        "thumbnail": edge.get("thumbnail") # New: Get thumbnail!
                    })
            return results
        except Exception as e:
            print(f"Error searching anime: {e}")
            return []

    def get_episodes_list(self, show_id: str, mode: str = "sub") -> List[str]:
        """
        Gets list of available episode numbers.
        Equivalent to `episodes_list` in shell script.
        """
        episodes_list_gql = """
        query ($showId: String!) {
            show( _id: $showId ) {
                _id availableEpisodesDetail
            }
        }
        """

        variables = {"showId": show_id}

        try:
            data = self._graphql(episodes_list_gql, variables)

            if "data" in data and "show" in data["data"]:
                details = data["data"]["show"]["availableEpisodesDetail"]
                if mode in details:
                    # The API returns a list of strings, e.g. ["1", "2", "3"]
                    # We should probably sort them numerically if possible
                    eps = details[mode]
                    # Sort numerically if they are numbers, otherwise keep as is
                    try:
                        eps.sort(key=lambda x: float(x))
                    except ValueError:
                        eps.sort()
                    return eps
            return []
        except Exception as e:
            print(f"Error getting episodes list: {e}")
            return []

    def get_episode_embeds(self, show_id: str, episode_string: str, mode: str = "sub") -> List[Dict]:
        """
        Gets the embed URLs for a specific episode.
        Equivalent to `get_episode_url` query part.
        """
        variables = {
            "showId": show_id,
            "translationType": mode,
            "episodeString": episode_string
        }
        
        try:
            response = self.session.get(
                self.API_URL,
                params={
                    "variables": json.dumps(variables),
                    "extensions": json.dumps({
                        "persistedQuery": {"version": 1, "sha256Hash": self.QUERY_HASH},
                        "aaReq": self._make_aa_req(),
                    }, separators=(",", ":")),
                },
                timeout=20,
            )
            response.raise_for_status()
            data = self._decode_episode_response(response.json())
            if data.get("errors"):
                raise RuntimeError(data["errors"][0].get("message", "Episode request failed"))
            
            sources = []
            if "data" in data and "episode" in data["data"]:
                ep_data = data["data"]["episode"]
                if ep_data and "sourceUrls" in ep_data:
                    for source in ep_data["sourceUrls"]:
                        # source is like {"sourceUrl": "--crypt...", "priority": 1.0, "sourceName": "Luf-Mp4"}
                        # We need to decrypt/clean the sourceUrl if it starts with --
                        if source.get("sourceUrl"):
                             sources.append(source)
            return sources
            
        except Exception as e:
            print(f"Error getting episode embeds: {e}")
            return []
    
    
    def _decrypt_source(self, url: str) -> str:
        """
        Decrypts the source URL.
        Ported from `provider_init` in ani-cli.
        """
        # Hex to char mapping
        mapping = {
            "01": "9", "00": "8", "0f": "7", "0e": "6", "0d": "5", "0c": "4",
            "0b": "3", "0a": "2", "09": "1", "08": "0", "42": "z", "41": "y",
            "40": "x", "4f": "w", "4e": "v", "4d": "u", "4c": "t", "4b": "s",
            "4a": "r", "49": "q", "48": "p", "57": "o", "56": "n", "55": "m",
            "54": "l", "53": "k", "52": "j", "51": "i", "50": "h", "5f": "g",
            "5e": "f", "5d": "e", "5c": "d", "5b": "c", "5a": "b", "59": "a",
            "62": "Z", "61": "Y", "60": "X", "6f": "W", "6e": "V", "6d": "U",
            "6c": "T", "6b": "S", "6a": "R", "69": "Q", "68": "P", "77": "O",
            "76": "N", "75": "M", "74": "L", "73": "K", "72": "J", "71": "I",
            "70": "H", "7f": "G", "7e": "F", "7d": "E", "7c": "D", "7b": "C",
            "7a": "B", "79": "A",
            
            # Symbols
            "15": "-", "16": ".", "67": "_", "46": "~", "02": ":", "17": "/",
            "07": "?", "1b": "#", "63": "[", "65": "]", "78": "@", "19": "!",
            "1c": "$", "1e": "&", "10": "(", "11": ")", "12": "*", "13": "+",
            "14": ",", "03": ";", "05": "=", "1d": "%",
        }

        # Only the custom "--" values use ani-cli's substitution cipher.
        # Normal provider URLs must pass through unchanged.
        if not url.startswith("--"):
            return url
        url = url[2:]

        # 2. Split into 2-char chunks and map
        decoded_chars = []
        for i in range(0, len(url), 2):
            chunk = url[i:i+2]
            if chunk in mapping:
                decoded_chars.append(mapping[chunk])
            else:
                # If not found, keep as is? Or maybe it's raw char?
                # The sed script only maps specific patterns. 
                # Ideally we should decode from hex if it's standard hex, but this is a specific cypher.
                # If not in mapping, let's assume it failed or is skipped.
                # Wait, sed 's/../&\n/g' splits EVERYTHING.
                # Then only specific lines are replaced.
                # So if it's "FF" and not in mapping, it remains "FF".
                # But looking at the mapping, it covers A-Z, a-z, 0-9 and symbols.
                # So mostly everything should be covered.
                decoded_chars.append(chunk)

        result = "".join(decoded_chars)
        
        # 3. Replace /clock with /clock.json
        result = result.replace("/clock", "/clock.json")
        return result

    def get_stream_link(self, source_embed: Dict) -> Optional[str]:
        """
        Given a source embed object (from get_episode_embeds), returns the final stream URL (m3u8/mp4).
        Equivalent to `get_links` in ani-cli.
        """
        self.last_error = None
        source_url = source_embed.get("sourceUrl")
        if not source_url:
            self.last_error = "Provider did not return a source URL"
            return None
            
        # Decrypt first
        decrypted_path = self._decrypt_source(source_url)
        if not decrypted_path.startswith("http"):
            # Check for protocol-relative URL (e.g., //vidstreaming.io/...)
            if decrypted_path.startswith("//"):
                full_url = f"https:{decrypted_path}"
            # If relative, append to BASE_URL
            elif decrypted_path.startswith("/"):
                 full_url = f"{self.BASE_URL}{decrypted_path}"
            else:
                 full_url = f"{self.BASE_URL}/{decrypted_path}"
        else:
            full_url = decrypted_path

        if "tools.fast4speed.rsvp" in full_url:
            return full_url

        print(f"Fetching stream details from: {full_url}")

        try:
            # Provider pages are third-party services and some of them can stop
            # responding entirely. Never let one provider block the play queue.
            response = self.session.get(full_url, timeout=(5, 10))
            response.raise_for_status()
            
            try:
                data = response.json()
            except (json.JSONDecodeError, ValueError):
                # Fallback: Try to regex scrape the response text (EXACTLY like ani-cli does)
                # ani-cli: sed 's|},{|\n|g' | sed -nE 's|.*link":"([^"]*)".*"resolutionStr":"([^"]*)".*|\2 >\1|p'
                
                print(f"JSON parsing failed. Trying ani-cli style line-based parsing...")
                text = response.text
                
                # Step 1: Mimic sed 's|},{|\n|g' - split JSON objects into separate lines
                # This is THE KEY to ani-cli's success!
                text = text.replace('},{', '}\n{')
                
                # Step 2: Search each line (like ani-cli's sed does)
                for line in text.split('\n'):
                    # Priority 1: HLS with en-US hardsub (best quality)
                    # Pattern: hls","url":"...","hardsub_lang":"en-US"
                    if 'hls' in line and 'hardsub_lang":"en-US"' in line:
                        hls_match = re.search(r'"url"\s*:\s*"([^"]*)"', line)
                        if hls_match:
                            link = hls_match.group(1).replace('\\u002F', '/')
                            print(f"Found HLS link: {link}")
                            return link
                    
                    # Priority 2: Standard link with resolution
                    # Pattern: link":"...","resolutionStr":"..."
                    if 'link"' in line and 'resolutionStr"' in line:
                        link_match = re.search(r'link"\s*:\s*"([^"]*)"', line)
                        if link_match:
                            link = link_match.group(1).replace('\\u002F', '/')
                            print(f"Found standard link: {link}")
                            return link
                
                # Step 3: If line-based parsing failed, try common player patterns
                # (for sites that use different JSON structure)
                print("Line-based parsing failed. Trying common player patterns...")
                common_patterns = [
                    (r'file\s*:\s*["\']([^"\']+)["\']', 'file'),
                    (r'source\s*:\s*["\']([^"\']+)["\']', 'source'),
                    (r'src\s*:\s*["\']([^"\']+)["\']', 'src'),
                    (r'link"\s*:\s*"([^"]*)"', 'link'),  # Any link (last resort)
                ]
                
                for pattern, name in common_patterns:
                    match = re.search(pattern, text)
                    if match:
                        link = match.group(1).replace('\\u002F', '/')
                        if link.startswith('http') or link.startswith('//'):
                            print(f"Found {name} pattern link: {link}")
                            return link
                
                # Step 4: Check if response is HTML/redirect (invalid!)
                # If it's HTML or redirect page, this provider failed - return None to try next provider
                if '<html' in text.lower() or 'redirecting' in text.lower() or '<script' in text.lower():
                    extracted = self._extract_with_ytdlp(full_url)
                    if extracted:
                        return extracted
                    print(f"⚠ Response is HTML/redirect page, not a valid stream URL!")
                    print(f"⚠ This provider is blocked or requires JavaScript. Skipping...")
                    self.last_error = "Provider requires JavaScript or returned an HTML page"
                    return None
                
                # Step 5: Last resort - if it looks like a valid URL, return for yt-dlp
                # Only return if it's an actual media URL (not HTML page)
                if full_url.startswith('http') and not any(ext in full_url.lower() for ext in ['.html', '.php?', '.asp']):
                    print(f"Returning raw URL for yt-dlp to attempt: {full_url}")
                    return full_url
                
                print(f"❌ No valid video link found from this provider.")
                self.last_error = "No media URL found in provider response"
                return None

            # The response JSON structure varies.
            # Ideally we look for "links" -> [ { "link": "...", "resolutionStr": "..." } ]
            
            if "links" in data:
                # Setup logic to pick best quality or return all?
                # For now let's return the first link or HLS
                # HLS is usually better for streaming
                
                # Check for HLS first
                for link in data["links"]:
                    if "hls" in link and link["hls"]:
                         return link["link"] # This is usually the m3u8
                
                # Fallback to mp4
                if len(data["links"]) > 0:
                    return data["links"][0]["link"]
            
            self.last_error = "Provider JSON did not contain usable links"
            return None

        except Exception as e:
            print(f"Error fetching stream link: {e}")
            self.last_error = str(e)
            return None

if __name__ == "__main__":
    # Simple test
    scraper = AniScraper()
    print("Searching for 'One Piece'...")
    results = scraper.search_anime("One Piece")
    if results:
        print(f"Found {len(results)} results")
        first = results[0]
        print(f"First result: {first['title']} ({first['id']})")
        
        print("Getting episodes...")
        eps = scraper.get_episodes_list(first['id'])
        print(f"Found {len(eps)} episodes. First 5: {eps[:5]}")
        
        if eps:
            ep_no = eps[0]
            print(f"Getting embeds for Episode {ep_no}...")
            embeds = scraper.get_episode_embeds(first['id'], ep_no)
            if embeds:
                print(f"Found {len(embeds)} embeds.")
                # Try to get stream for first embed
                stream_url = scraper.get_stream_link(embeds[0])
                print(f"Stream URL: {stream_url}")
