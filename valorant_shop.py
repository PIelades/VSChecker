"""
Personal Valorant daily shop checker (Windows).

Requirements: pip install requests

How it works:
  - First run: you paste your Riot "ssid" cookie once (see SETUP below).
    It is saved to riot_session.json and refreshed on every run.
  - After that it logs in with the cookie, so the Riot Client can be closed.
  - The shop is cached in shop_cache.json until the daily reset.

SETUP (one time):
  1. In your browser, open the AUTH_URL below (or just go to
     https://auth.riotgames.com/authorize?... via the link printed by this script)
     and log in with "Stay signed in" ticked.
  2. Press F12 -> Application (Chrome/Edge) or Storage (Firefox) -> Cookies
     -> https://auth.riotgames.com -> copy the value of the cookie named "ssid".
  3. Run this script and paste it when asked.

SECURITY: riot_session.json is basically a key to your account.
Never share it or upload it (add it to .gitignore if you use git).

Uses unofficial endpoints, so it may break if Riot changes them.
"""
import base64
import json
import os
import ssl
import sys
import time
from datetime import timedelta
from urllib.parse import parse_qs, urljoin, urlparse

import requests
import urllib3
from requests.adapters import HTTPAdapter

urllib3.disable_warnings()  # only needed for the local Riot Client fallback

SHARD = "eu"  # eu / na / ap / kr
HERE = os.path.dirname(os.path.abspath(__file__))
CACHE_FILE = os.path.join(HERE, "shop_cache.json")
SESSION_FILE = os.path.join(HERE, "riot_session.json")
LOCKFILE = os.path.join(
    os.environ.get("LOCALAPPDATA", ""), "Riot Games", "Riot Client", "Config", "lockfile"
)

AUTH_URL = (
    "https://auth.riotgames.com/authorize"
    "?redirect_uri=https%3A%2F%2Fplayvalorant.com%2Fopt_in"
    "&client_id=play-valorant-web-prod"
    "&response_type=token%20id_token&scope=account%20openid&nonce=1"
)

CIPHERS = ":".join(
    [
        "ECDHE-ECDSA-AES128-GCM-SHA256",
        "ECDHE-RSA-AES128-GCM-SHA256",
        "ECDHE-ECDSA-CHACHA20-POLY1305",
        "ECDHE-RSA-CHACHA20-POLY1305",
        "ECDHE-ECDSA-AES256-GCM-SHA384",
        "ECDHE-RSA-AES256-GCM-SHA384",
    ]
)


class TLSAdapter(HTTPAdapter):
    """Riot's auth server can reject Python's default TLS setup; use a browser-like one."""

    def init_poolmanager(self, *args, **kwargs):
        ctx = ssl.create_default_context()
        try:
            ctx.set_ciphers(CIPHERS)
        except ssl.SSLError:
            pass
        kwargs["ssl_context"] = ctx
        return super().init_poolmanager(*args, **kwargs)


def make_session():
    s = requests.Session()
    s.mount("https://", TLSAdapter())
    s.headers["User-Agent"] = (
        "RiotClient/63.0.9.4909983.4789131 rso-auth (Windows;10;;Professional, x64)"
    )
    return s


# ---------- session cookie storage ----------

def load_cookies(s):
    try:
        with open(SESSION_FILE) as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return False
    for c in data:
        s.cookies.set(c["name"], c["value"], domain=c["domain"], path=c.get("path", "/"))
    return bool(data)


def save_cookies(s):
    data = [
        {"name": c.name, "value": c.value, "domain": c.domain, "path": c.path}
        for c in s.cookies
    ]
    with open(SESSION_FILE, "w") as f:
        json.dump(data, f, indent=2)


def first_time_setup(s):
    print("First-time setup: I need your Riot 'ssid' cookie (see the top of this file).")
    ssid = input("Paste your ssid cookie value: ").strip().strip('"')
    if not ssid:
        sys.exit("No cookie entered.")
    s.cookies.set("ssid", ssid, domain="auth.riotgames.com", path="/")


# ---------- getting tokens ----------

def cookie_tokens(s):
    """Re-authenticate with the saved cookie. Returns (access, entitlement, puuid) or None."""
    debug = True  # always show what Riot answers (tokens are redacted)
    if debug:
        names = [c.name for c in s.cookies]
        print(f"[debug] cookies loaded: {names}")
    url = AUTH_URL
    location = ""
    for hop in range(6):  # follow redirects by hand so we can read the URL fragment
        r = s.get(url, allow_redirects=False)
        location = r.headers.get("Location", "")
        if debug:
            shown = urlparse(location)._replace(fragment="", query="").geturl()  # no tokens
            print(f"[debug] hop {hop}: HTTP {r.status_code} -> {shown or '(no redirect)'}")
            if not location:
                print(f"[debug] body: {r.text[:200]!r}")
        if not location:
            return None
        if "access_token=" in location:
            break
        url = urljoin(url, location)
    else:
        return None  # kept bouncing to the login page: cookie is dead

    access = parse_qs(urlparse(location).fragment)["access_token"][0]
    save_cookies(s)  # Riot rotates the cookies on each login, so keep the new ones

    auth = {"Authorization": f"Bearer {access}"}
    ent = s.post("https://entitlements.auth.riotgames.com/api/token/v1", headers=auth, json={})
    ent.raise_for_status()
    info = s.get("https://auth.riotgames.com/userinfo", headers=auth)
    info.raise_for_status()
    return access, ent.json()["entitlements_token"], info.json()["sub"]


def local_tokens():
    """Fallback: ask a running Riot Client for tokens."""
    try:
        with open(LOCKFILE) as f:
            _name, _pid, port, password, protocol = f.read().split(":")
    except FileNotFoundError:
        return None
    try:
        r = requests.get(
            f"{protocol}://127.0.0.1:{port}/entitlements/v1/token",
            auth=("riot", password),
            verify=False,
        )
        r.raise_for_status()
        d = r.json()
        return d["accessToken"], d["token"], d["subject"]
    except (requests.RequestException, KeyError, ValueError):
        return None  # client open but not ready (e.g. Valorant not running)


def get_tokens():
    s = make_session()
    if not load_cookies(s):
        first_time_setup(s)

    tokens = cookie_tokens(s)
    if tokens:
        return tokens

    print("Cookie login failed (cookie expired, or Riot blocked the request).")
    tokens = local_tokens()
    if tokens:
        print("Using the running Riot Client instead.")
        return tokens
    sys.exit(
        "Could not log in. See the [debug] lines above for what Riot answered."
    )


# ---------- shop ----------

def client_version():
    r = requests.get("https://valorant-api.com/v1/version")
    return r.json()["data"]["riotClientVersion"]


def get_storefront(access, entitlement, puuid):
    platform = base64.b64encode(
        json.dumps(
            {
                "platformType": "PC",
                "platformOS": "Windows",
                "platformOSVersion": "10.0.19042.1.256.64bit",
                "platformChipset": "Unknown",
            }
        ).encode()
    ).decode()
    headers = {
        "Authorization": f"Bearer {access}",
        "X-Riot-Entitlements-JWT": entitlement,
        "X-Riot-ClientVersion": client_version(),
        "X-Riot-ClientPlatform": platform,
    }
    url = f"https://pd.{SHARD}.a.pvp.net/store/v3/storefront/{puuid}"
    r = requests.post(url, headers=headers, json={})  # v3 is POST-only
    r.raise_for_status()
    return r.json()


def skin_info(uuid):
    r = requests.get(f"https://valorant-api.com/v1/weapons/skinlevels/{uuid}")
    d = r.json()["data"]
    return d["displayName"], d["displayIcon"]


def load_cache():
    """Return the cached shop if it exists and hasn't reset yet."""
    try:
        with open(CACHE_FILE) as f:
            cache = json.load(f)
        if cache["expires_at"] > time.time():
            return cache
    except (FileNotFoundError, KeyError, json.JSONDecodeError):
        pass
    return None


def save_cache(skins, remaining_seconds):
    with open(CACHE_FILE, "w") as f:
        json.dump({"expires_at": time.time() + remaining_seconds, "skins": skins}, f, indent=2)


def fetch_shop():
    access, entitlement, puuid = get_tokens()
    store = get_storefront(access, entitlement, puuid)
    panel = store["SkinsPanelLayout"]

    # v3 may list skins under SingleItemOffers (UUIDs) and/or SingleItemStoreOffers
    uuids = list(panel.get("SingleItemOffers", []))
    if not uuids:
        uuids = [o["Rewards"][0]["ItemID"] for o in panel.get("SingleItemStoreOffers", [])]

    skins = []
    for uuid in uuids:
        name, icon = skin_info(uuid)
        skins.append({"name": name, "icon": icon})

    save_cache(skins, panel["SingleItemOffersRemainingDurationInSeconds"])
    return load_cache()


def main():
    # Run with --refresh to ignore the cache and fetch a fresh shop
    cache = None if "--refresh" in sys.argv else load_cache()
    source = "cached"
    if cache is None:
        cache = fetch_shop()
        source = "fresh"

    remaining = timedelta(seconds=int(cache["expires_at"] - time.time()))
    print(f"Daily shop ({source}, resets in {remaining}):\n")
    for skin in cache["skins"]:
        print(f"- {skin['name']}\n  {skin['icon']}")


if __name__ == "__main__":
    main()