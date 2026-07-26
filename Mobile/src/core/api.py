import base64
import hashlib
import json
import re
import time

import requests
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from yt_dlp import YoutubeDL

from core.storage import storage


class AniApi:
    BASE_URL = "https://allanime.day"
    API_URL = "https://api.mkissa.net/api"
    REFERER = "https://mkissa.to"
    CDN_URL = "https://cdn.mkissa.net/all/mk/_app/immutable"
    QUERY_HASH = "f4662f4b7510b26795dd53ef824a0bf1740fbbc5d1273fab18222ac831bca8d0"
    AGENT = "Mozilla/5.0 (Linux; Android 14; Mobile; rv:150.0) Gecko/150.0 Firefox/150.0"

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": self.AGENT, "Referer": self.REFERER, "Origin": self.REFERER})
        self._api_key = None
        self._api_epoch = None
        self.last_error = None

    def _graphql(self, query, variables):
        response = self.session.post(self.API_URL, json={"variables": variables, "query": query}, timeout=(7, 20))
        response.raise_for_status()
        data = response.json()
        if data.get("errors"):
            raise RuntimeError(data["errors"][0].get("message", "GraphQL request failed"))
        return data

    def search(self, query, mode="sub"):
        gql = """query($search: SearchInput $limit: Int $page: Int $translationType: VaildTranslationTypeEnumType $countryOrigin: VaildCountryOriginEnumType) { shows(search: $search limit: $limit page: $page translationType: $translationType countryOrigin: $countryOrigin) { edges { _id name availableEpisodes airedStart thumbnail __typename } } }"""
        variables = {"search": {"allowAdult": False, "allowUnknown": False, "query": query}, "limit": 40, "page": 1, "translationType": mode, "countryOrigin": "ALL"}
        edges = self._graphql(gql, variables).get("data", {}).get("shows", {}).get("edges", [])
        return [{"id": item["_id"], "title": item["name"], "episodes": item.get("availableEpisodes", {}).get(mode, 0), "thumbnail": item.get("thumbnail")} for item in edges]

    def episodes(self, show_id, mode="sub"):
        gql = "query($showId: String!) { show(_id: $showId) { _id availableEpisodesDetail } }"
        details = self._graphql(gql, {"showId": show_id}).get("data", {}).get("show", {}).get("availableEpisodesDetail", {})
        values = details.get(mode, [])
        return sorted(values, key=lambda value: float(value) if str(value).replace(".", "", 1).isdigit() else float("inf"))

    def _fetch_key(self):
        page = self.session.get(self.REFERER, timeout=(7, 20)); page.raise_for_status()
        epoch = re.search(r'"epoch":(\d+)', page.text)
        part_b = re.search(r'"partB":"([^"]+)"', page.text)
        app_url = re.search(re.escape(self.CDN_URL) + r'/entry/app\.[A-Za-z0-9_.-]+\.js', page.text)
        if not all((epoch, part_b, app_url)): raise RuntimeError("API key metadata unavailable")
        app = self.session.get(app_url.group(0), timeout=(7, 20)); app.raise_for_status()
        chunks = re.findall(r'"\.\./chunks/([A-Za-z0-9_.-]+\.js)"', app.text)[:5]
        mask = None
        for chunk in chunks:
            response = self.session.get(f"{self.CDN_URL}/chunks/{chunk}", timeout=(7, 20)); response.raise_for_status()
            match = re.search(r'(?<![0-9a-f])[0-9a-f]{64}(?![0-9a-f])', response.text)
            if match:
                mask = bytes.fromhex(match.group(0)); break
        secret = base64.b64decode(part_b.group(1))
        if not mask or len(secret) != 32: raise RuntimeError("API key mask unavailable")
        self._api_epoch = int(epoch.group(1))
        self._api_key = bytes(a ^ b for a, b in zip(mask, secret))

    def _aa_req(self):
        if self._api_key is None: self._fetch_key()
        timestamp = int(time.time()) // 300 * 300 * 1000
        iv = hashlib.sha256(f"{self._api_epoch}:{self.QUERY_HASH}:{timestamp}".encode()).digest()[:12]
        payload = json.dumps({"v": 1, "ts": timestamp, "epoch": self._api_epoch, "qh": self.QUERY_HASH}, separators=(",", ":")).encode()
        return base64.b64encode(b"\x01" + iv + AESGCM(self._api_key).encrypt(iv, payload, None)).decode()

    def _decode_episode(self, data):
        encoded = data.get("tobeparsed") or data.get("data", {}).get("tobeparsed")
        if not encoded: return data
        raw = base64.b64decode(encoded)
        decoded = json.loads(AESGCM(self._api_key).decrypt(raw[1:13], raw[13:], None))
        return decoded if "data" in decoded else {"data": decoded}

    def embeds(self, show_id, episode, mode="sub"):
        variables = {"showId": show_id, "translationType": mode, "episodeString": str(episode)}
        extensions = {"persistedQuery": {"version": 1, "sha256Hash": self.QUERY_HASH}, "aaReq": self._aa_req()}
        response = self.session.get(self.API_URL, params={"variables": json.dumps(variables, separators=(",", ":")), "extensions": json.dumps(extensions, separators=(",", ":"))}, timeout=(7, 20))
        response.raise_for_status()
        data = self._decode_episode(response.json())
        if data.get("errors"): raise RuntimeError(data["errors"][0].get("message", "Episode request failed"))
        return data.get("data", {}).get("episode", {}).get("sourceUrls", [])

    @staticmethod
    def _decrypt_source(url):
        if not url.startswith("--"): return url
        mapping = {
            "01":"9","00":"8","0f":"7","0e":"6","0d":"5","0c":"4","0b":"3","0a":"2","09":"1","08":"0",
            "42":"z","41":"y","40":"x","4f":"w","4e":"v","4d":"u","4c":"t","4b":"s","4a":"r","49":"q","48":"p",
            "57":"o","56":"n","55":"m","54":"l","53":"k","52":"j","51":"i","50":"h","5f":"g","5e":"f","5d":"e",
            "5c":"d","5b":"c","5a":"b","59":"a","62":"Z","61":"Y","60":"X","6f":"W","6e":"V","6d":"U","6c":"T",
            "6b":"S","6a":"R","69":"Q","68":"P","77":"O","76":"N","75":"M","74":"L","73":"K","72":"J","71":"I",
            "70":"H","7f":"G","7e":"F","7d":"E","7c":"D","7b":"C","7a":"B","79":"A","15":"-","16":".",
            "67":"_","46":"~","02":":","17":"/","07":"?","1b":"#","63":"[","65":"]","78":"@","19":"!","1c":"$",
            "1e":"&","10":"(","11":")","12":"*","13":"+","14":",","03":";","05":"=","1d":"%",
        }
        encoded = url[2:]
        result = "".join(mapping.get(encoded[index:index + 2], encoded[index:index + 2]) for index in range(0, len(encoded), 2))
        return result.replace("/clock", "/clock.json")

    def _yt_dlp(self, url):
        try:
            with YoutubeDL({"quiet": True, "no_warnings": True, "socket_timeout": 10, "http_headers": {"Referer": self.REFERER}}) as ydl:
                info = ydl.extract_info(url, download=False)
            candidate = info.get("url") if info else None
            return candidate if candidate and candidate != url and "/embed" not in candidate else None
        except Exception as exc:
            self.last_error = str(exc)
            return None

    def stream(self, embed):
        self.last_error = None
        source = embed.get("sourceUrl")
        if not source:
            self.last_error = "Missing source URL"; return None
        path = self._decrypt_source(source)
        full_url = path if path.startswith("http") else f"{self.BASE_URL}{path if path.startswith('/') else '/' + path}"
        if "tools.fast4speed.rsvp" in full_url: return full_url
        try:
            response = self.session.get(full_url, timeout=(5, 10)); response.raise_for_status()
            try:
                data = response.json()
                links = data.get("links", [])
                hls = next((item.get("link") or item.get("url") for item in links if item.get("hls")), None)
                if hls: return hls
                if links: return links[0].get("link") or links[0].get("url")
            except ValueError:
                body = response.text.replace("},{", "}\n{")
                for line in body.splitlines():
                    if "hardsub_lang\":\"en-US" in line:
                        match = re.search(r'"url"\s*:\s*"([^"]+)"', line)
                        if match: return match.group(1).replace("\\u002F", "/")
                    match = re.search(r'link"\s*:\s*"([^"]+)".*resolutionStr', line)
                    if match: return match.group(1).replace("\\u002F", "/")
                extracted = self._yt_dlp(full_url)
                if extracted: return extracted
                self.last_error = self.last_error or "Provider returned an HTML page without media"
                return None
            self.last_error = "Provider JSON did not contain media"
        except Exception as exc:
            self.last_error = str(exc)
            storage.log("warning", "stream_provider_error", provider=embed.get("sourceName"), error=str(exc))
        return None

    def health(self):
        started = time.monotonic()
        try:
            response = self.session.get(self.REFERER, timeout=(5, 10))
            return {"ok": response.ok, "status": response.status_code, "seconds": round(time.monotonic() - started, 2)}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}
