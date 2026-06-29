"""
Multi-Account Proxy Manager
Supports multiple Webshare API keys (10 proxies each).
Aggregate all proxies into one big rotating pool.
"""
import requests
import random
import time
import logging
import threading
import os
import json

logger = logging.getLogger(__name__)

TEST_URL = "https://api.mail.tm/domains"
CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "proxy_config.json")
WEBSHARE_API = "https://proxy.webshare.io/api/v2"


class WebshareAccount:
    """Single Webshare account — 10 free proxies."""

    def __init__(self, api_key):
        self.api_key = api_key
        self._proxies = []
        self._lock = threading.Lock()

    def _headers(self):
        return {"Authorization": f"Token {self.api_key}"}

    def fetch_proxies(self):
        """Fetch all proxies from this account."""
        try:
            r = requests.get(f"{WEBSHARE_API}/proxy/list/", headers=self._headers(), timeout=15)
            if r.status_code == 200:
                results = r.json().get("results", [])
                proxies = []
                for p in results:
                    ip = p.get("ip_address", "")
                    port = p.get("port", "")
                    protocol = p.get("proxy_protocol", "http")
                    username = p.get("username", "")
                    password = p.get("password", "")
                    if ip and port:
                        proxies.append({
                            "url": f"{protocol}://{username}:{password}@{ip}:{port}",
                            "ip": ip,
                            "port": port,
                            "protocol": protocol,
                        })
                with self._lock:
                    self._proxies = proxies
                return len(proxies)
            elif r.status_code == 401:
                logger.warning(f"Webshare API key invalid")
            else:
                logger.warning(f"Webshare API error: {r.status_code}")
        except Exception as e:
            logger.warning(f"Webshare fetch failed: {e}")
        return 0

    def get_proxy_url(self):
        with self._lock:
            if self._proxies:
                return random.choice(self._proxies)["url"]
        return None

    def get_all_urls(self):
        with self._lock:
            return [p["url"] for p in self._proxies]

    @property
    def count(self):
        with self._lock:
            return len(self._proxies)


class ProxyManager:
    """
    Multi-source proxy manager.
    - Multiple Webshare accounts (10 proxies each)
    - Free proxy fallback
    - Custom proxy list
    """

    def __init__(self):
        self.enabled = False
        self.accounts = []          # List of WebshareAccount
        self.all_webshare = []      # Flattened proxy URLs from all accounts
        self._ws_lock = threading.Lock()
        self.free_working = []      # Tested working free proxies
        self.free_failed = set()
        self._free_lock = threading.Lock()
        self.custom_proxies = []
        self.mode = "webshare"

        self._load_config()

    # --- Config persistence ---

    def _load_config(self):
        try:
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, "r") as f:
                    config = json.load(f)
                keys = config.get("webshare_api_keys", [])
                if not keys and config.get("webshare_api_key"):
                    keys = [config["webshare_api_key"]]
                for key in keys:
                    self._add_account(key)
        except Exception as e:
            logger.warning(f"Failed to load config: {e}")

    def _save_config(self):
        try:
            config = {}
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, "r") as f:
                    config = json.load(f)
            config["webshare_api_keys"] = [a.api_key for a in self.accounts]
            with open(CONFIG_FILE, "w") as f:
                json.dump(config, f, indent=2)
        except Exception as e:
            logger.warning(f"Failed to save config: {e}")

    # --- Webshare accounts ---

    def _add_account(self, api_key):
        """Add a Webshare account and fetch its proxies."""
        # Check duplicate
        existing = [a.api_key for a in self.accounts]
        if api_key in existing:
            return 0

        acct = WebshareAccount(api_key)
        count = acct.fetch_proxies()
        if count > 0:
            self.accounts.append(acct)
            with self._ws_lock:
                self.all_webshare.extend(acct.get_all_urls())
            logger.info(f"Webshare: added account, {count} proxies (total: {len(self.all_webshare)})")
            return count
        return 0

    def add_webshare_key(self, api_key):
        """Add a Webshare API key. Returns proxy count or 0 on failure."""
        count = self._add_account(api_key)
        if count > 0:
            self._save_config()
        return count

    def remove_webshare_key(self, api_key):
        """Remove a Webshare API key."""
        self.accounts = [a for a in self.accounts if a.api_key != api_key]
        self._rebuild_webshare_list()
        self._save_config()

    def _rebuild_webshare_list(self):
        """Rebuild the flat proxy list from all accounts."""
        with self._ws_lock:
            self.all_webshare = []
            for acct in self.accounts:
                self.all_webshare.extend(acct.get_all_urls())

    # --- Proxy rotation ---

    def get_proxy(self):
        """Get next proxy. Cycles through Webshare pool, then free, then custom."""
        if not self.enabled:
            return None

        # Custom proxies (user-provided)
        if self.mode == "custom" and self.custom_proxies:
            return random.choice(self.custom_proxies)

        # Webshare (primary)
        if self.mode == "webshare" and self.all_webshare:
            with self._ws_lock:
                if self.all_webshare:
                    return random.choice(self.all_webshare)

        # Free proxy fallback
        with self._free_lock:
            if self.free_working:
                return random.choice(self.free_working)

        return None

    def mark_failed(self, proxy_str):
        """Mark a proxy as failed."""
        with self._free_lock:
            self.free_failed.add(proxy_str)
            if proxy_str in self.free_working:
                self.free_working.remove(proxy_str)

    def refresh_free_proxies(self, max_test=20):
        """Test and cache working free proxies."""
        sources = [
            ("http", "https://cdn.jsdelivr.net/gh/proxifly/free-proxy-list@main/proxies/protocols/http/data.txt"),
            ("http", "https://raw.githubusercontent.com/hproxy-com/free-proxy-list/main/http.txt"),
        ]
        candidates = []
        for proto, url in sources:
            try:
                r = requests.get(url, timeout=15)
                if r.status_code == 200:
                    for line in r.text.strip().split('\n'):
                        line = line.strip()
                        if line and not line.startswith('#'):
                            if '://' in line:
                                candidates.append(line)
                            elif ':' in line:
                                candidates.append(f"{proto}://{line}")
            except Exception:
                pass

        random.shuffle(candidates)
        working = []
        for proxy in candidates[:max_test]:
            if proxy in self.free_failed:
                continue
            try:
                r = requests.get(TEST_URL, proxies={"http": proxy, "https": proxy}, timeout=4, verify=False)
                if r.status_code == 200:
                    working.append(proxy)
                    if len(working) >= 5:
                        break
            except Exception:
                pass

        with self._free_lock:
            self.free_working = working
        return len(working)

    # --- Custom proxies ---

    def load_custom_proxies(self, proxy_list):
        with self._ws_lock:
            self.custom_proxies = []
            for line in proxy_list:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                if '://' not in line:
                    line = f"http://{line}"
                self.custom_proxies.append(line)
            self.mode = "custom"

    # --- Enable/Disable ---

    def enable(self):
        self.enabled = True

    def disable(self):
        self.enabled = False

    # --- Status ---

    def get_status(self):
        return {
            "enabled": self.enabled,
            "mode": self.mode,
            "webshare_accounts": len(self.accounts),
            "webshare_proxies": len(self.all_webshare),
            "free_working": len(self.free_working),
            "custom_count": len(self.custom_proxies),
        }

    def get_all_proxies_info(self):
        """Get detailed info about all Webshare proxies."""
        info = []
        for i, acct in enumerate(self.accounts):
            info.append({
                "account": i + 1,
                "api_key": acct.api_key[:8] + "...",
                "proxy_count": acct.count,
            })
        return info


proxy_manager = ProxyManager()
