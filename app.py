"""
Valorant shop UI. Missing packages (pywebview, requests) are installed automatically on first run.
Put this next to valorant_shop.py (same folder) and run:  python app.py
  python app.py --background   loads/refreshes the shop silently, then exits
  python app.py --console      keeps the console window open (for debugging)
Normally the app restarts itself without a console window. It also creates
"Valorant Shop.vbs" next to this file: double-click that to open the app with
no console window at all. Errors go to app_log.txt when there is no console.
"""
import base64, contextlib, io, json, os, subprocess, sys, time, traceback, webbrowser

HERE = os.path.dirname(os.path.abspath(__file__))


def _pythonw():
    p = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
    return p if os.path.exists(p) else None


if (__name__ == "__main__" and os.name == "nt" and "--console" not in sys.argv
        and os.path.basename(sys.executable).lower() == "python.exe"
        and sys.gettrace() is None and "debugpy" not in sys.modules and _pythonw()):
    # Started from a console window: start again without one and let the console close.
    subprocess.Popen([_pythonw(), os.path.abspath(__file__), *sys.argv[1:]], creationflags=0x00000008, close_fds=True)
    sys.exit(0)

_CONSOLE = sys.stdout is not None and sys.stderr is not None
if not _CONSOLE:  # no console: keep a log file instead
    sys.stdout = sys.stderr = open(os.path.join(HERE, "app_log.txt"), "w", buffering=1, encoding="utf-8")


def _crash(et, ev, tb):
    """Never fail silently: log the error and show it in a Windows popup."""
    msg = "".join(traceback.format_exception(et, ev, tb))
    try:
        print(msg)
    except Exception:
        pass
    if os.name == "nt" and "--background" not in sys.argv:
        try:
            import ctypes
            ctypes.windll.user32.MessageBoxW(None, msg[-1800:], "Valorant Shop crashed", 0x10)
        except Exception:
            pass


sys.excepthook = _crash

# ---------- first-run setup: install missing packages with pip ----------
NEEDED = {"requests": "requests", "webview": "pywebview"}  # import name -> pip name


def _missing():
    import importlib
    import importlib.util
    importlib.invalidate_caches()
    return [pkg for mod, pkg in NEEDED.items() if importlib.util.find_spec(mod) is None]


def _pip_install(pkgs):
    py = os.path.join(os.path.dirname(sys.executable), "python.exe")
    py = py if os.path.exists(py) else sys.executable
    quiet = not _CONSOLE
    flags = 0x08000000 if (os.name == "nt" and quiet) else 0  # no flashing console window

    def run(*args):
        if quiet:
            r = subprocess.run([py, "-m", *args], capture_output=True, text=True, creationflags=flags, timeout=900)
            return r.returncode, (r.stdout or "") + (r.stderr or "")
        return subprocess.run([py, "-m", *args], timeout=900).returncode, ""

    base = ["pip", "install", "--disable-pip-version-check", *pkgs]
    code, out = run(*base)
    if code != 0:  # pip itself might be missing: set it up and try once more
        run("ensurepip", "--upgrade")
        code, out = run(*base)
    if _missing():
        raise RuntimeError("Could not install: " + ", ".join(_missing()) + "\n\n"
                           "Try running this yourself in a terminal:\n"
                           f'"{py}" -m pip install ' + " ".join(pkgs) + "\n\n" + out[-1200:])


def _with_wait_window(fn):
    """Show a small 'please wait' window while fn runs (no console to show progress in)."""
    try:
        import threading
        import tkinter as tk
    except Exception:
        return fn()
    box = {}

    def work():
        try:
            fn()
        except BaseException as e:
            box["e"] = e

    t = threading.Thread(target=work, daemon=True)
    t.start()
    root = tk.Tk()
    root.title("Valorant Shop")
    root.resizable(False, False)
    root.attributes("-topmost", True)
    tk.Label(root, text="Installing what the app needs...\nThis only happens the first time.",
             padx=36, pady=26, font=("Segoe UI", 11)).pack()

    def poll():
        if t.is_alive():
            root.after(200, poll)
        else:
            root.destroy()

    poll()
    root.mainloop()
    if "e" in box:
        raise box["e"]


if __name__ == "__main__" and _missing():
    todo = _missing()
    if _CONSOLE:
        print("First run: installing " + ", ".join(todo) + " ...")
        _pip_install(todo)
    elif "--background" in sys.argv:
        _pip_install(todo)
    else:
        _with_wait_window(lambda: _pip_install(todo))

import requests, webview
import valorant_shop as vs

try:
    import winreg
except ImportError:
    winreg = None

HERE = os.path.dirname(os.path.abspath(__file__))
SETTINGS = os.path.join(HERE, "ui_settings.json")
CACHE = os.path.join(HERE, "ui_shop_cache.json")
WISH = os.path.join(HERE, "wishlist.json")
CACHE_V = 5
VP = "85ad13f7-3d1b-5128-9eb2-7cd8ee0b5741"
KC = "85ca954a-41f2-ce94-9b45-8ca3dd39a00d"  # Kingdom Credits
CHROMA = "3ad1b2b2-acdb-4524-852f-954a76ddae0a"  # skin variants (ownership lookups)
SKIN = "e7c63390-eda7-46e0-bb7a-a6abdacd2433"
BUDDY = "dd3bf334-87f3-40bd-b043-682a57a8dc3a"
SPRAY = "d5f120f8-ff8c-4aac-92ea-f2b5acbe9475"
CARD = "3f296c07-64c3-494c-923b-fe692a4fa1bd"
TITLE = "de7caa6b-adf7-4588-bbd1-143831e786c6"
FLEX = "03a572de-4234-31ed-d344-ababa488f981"
RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
DEFAULTS = {"bg": ["#ff4655", "#000000"], "border": "#ffffff", "dynamic": True, "speed": 3, "vol_ui": 50, "vol_prev": 60}


def _read(path):
    try:
        with open(path) as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def va(path, timeout=20):
    """Fetch from the community valorant-api.com database."""
    try:
        r = requests.get(f"https://valorant-api.com/v1/{path}", timeout=timeout)
        return r.json().get("data") if r.ok else None
    except Exception:
        return None


def va_cached(name, hours=24):
    """Big lists (all weapons, sprays, ...) are kept on disk for a day so the app opens fast."""
    path = os.path.join(HERE, f"cache_{name}.json")
    fresh = os.path.exists(path) and time.time() - os.path.getmtime(path) < hours * 3600
    data = _read(path) if fresh else None
    if not data:
        data = va(name, timeout=60)
        if data:
            try:
                with open(path, "w") as f:
                    json.dump(data, f)
            except OSError:
                pass
        else:
            data = _read(path)  # offline: an old copy is better than nothing
    return data


# Riot's data has no "limited" flag, so this is a best guess: skins with no store tier
# (battle pass, event and agent rewards) and esports / collab capsules never rotate into the shop.
LIMITED_WORDS = ("champions 20", "vct ", "arcane", "game changers")


def _limited(s):
    n = s["displayName"].lower()
    return not s.get("contentTierUuid") or any(w in n for w in LIMITED_WORDS)


class Api:
    _idx = None
    _weapons = None
    _acc = {}

    # ---------- item lookups ----------
    def _load(self):
        """Download the weapon + skin database once."""
        if Api._weapons is None:
            data = va_cached("weapons")
            if not data:
                return [], {}
            Api._idx = {l["uuid"]: (s, w["uuid"]) for w in data for s in w["skins"] for l in s["levels"]}
            Api._weapons = data
        return Api._weapons, Api._idx

    @staticmethod
    def _fmt_skin(s, weapon=None):
        lv = [{"id": l["uuid"], "name": l["displayName"], "icon": l["displayIcon"], "video": l["streamedVideo"]}
              for l in s["levels"]]
        ch = [{"id": x["uuid"], "name": x["displayName"], "icon": x["fullRender"] or x["displayIcon"],
               "swatch": x["swatch"] or x["displayIcon"], "video": x["streamedVideo"]} for x in s["chromas"]]
        icon = s["displayIcon"] or (lv[0]["icon"] if lv else None) or (ch[0]["icon"] if ch else None)
        return {"kind": "skin", "id": s["uuid"], "w": weapon, "name": s["displayName"], "icon": icon,
                "levels": lv, "chromas": ch}

    def _skin(self, level_uuid):
        hit = self._load()[1].get(level_uuid)
        return self._fmt_skin(*hit) if hit else None

    def _item(self, type_id, item_id):
        if type_id == SKIN:
            return self._skin(item_id)
        if type_id == BUDDY and (d := va(f"buddies/levels/{item_id}")):
            return {"kind": "buddy", "id": item_id, "name": d["displayName"], "icon": d["displayIcon"],
                    "levels": [{"name": d["displayName"], "icon": d["displayIcon"]}], "chromas": []}
        if type_id == SPRAY and (d := va(f"sprays/{item_id}")):
            big = d.get("animationGif") or d.get("fullTransparentIcon") or d["displayIcon"]
            return {"kind": "spray", "id": item_id, "name": d["displayName"],
                    "icon": d.get("fullTransparentIcon") or d["displayIcon"],
                    "levels": [{"name": d["displayName"], "icon": big}], "chromas": []}
        if type_id == CARD and (d := va(f"playercards/{item_id}")):
            return {"kind": "card", "id": item_id, "name": d["displayName"], "icon": d.get("wideArt") or d["displayIcon"],
                    "levels": [{"name": d["displayName"], "icon": d.get("largeArt") or d["displayIcon"]}], "chromas": []}
        if type_id == TITLE and (d := va(f"playertitles/{item_id}")):
            t = d.get("titleText") or d["displayName"]
            return {"kind": "title", "name": d["displayName"], "text": t,
                    "levels": [{"name": d["displayName"], "text": t}], "chromas": []}
        if type_id == FLEX and (d := va(f"flex/{item_id}")):
            return {"kind": "flex", "name": d["displayName"], "icon": d["displayIcon"],
                    "levels": [{"name": d["displayName"], "icon": d["displayIcon"]}], "chromas": []}
        return None

    # ---------- wishlist + full catalog ----------
    def get_wishlist(self):
        w = _read(WISH)
        return w if isinstance(w, dict) else {}

    def set_wishlist(self, w):
        with open(WISH, "w") as f:
            json.dump(w, f)

    def get_catalog(self):
        """Every weapon, grouped on the wishlist page."""
        out = []
        for w in self._load()[0]:
            out.append({"id": w["uuid"], "name": w["displayName"], "icon": w["displayIcon"],
                        "cat": (w.get("category") or "").split("::")[-1],
                        "cost": (w.get("shopData") or {}).get("cost") or 0})
        out.sort(key=lambda w: (w["cost"], w["name"]))
        return {"weapons": out,
                "error": None if out else "The skin list could not be downloaded. Check your internet connection."}

    def get_weapon_skins(self, weapon_id):
        w = next((w for w in self._load()[0] if w["uuid"] == weapon_id), None)
        out = []
        for s in (w or {}).get("skins", []):
            n = s["displayName"]
            if s["uuid"] == w.get("defaultSkinUuid") or n.startswith("Standard "):
                continue
            x = self._fmt_skin(s, w["uuid"])
            if "Random Favorite" in n:  # Riot's "pick one of my favourites each game" skin
                x.update(random=True, name="Random favorite skin", icon=x["icon"] or w["displayIcon"])
                out.append(x)
                continue
            if not x["icon"]:
                continue
            x["limited"] = _limited(s)
            out.append(x)
        out.sort(key=lambda x: (not x.get("random"), x["name"]))
        return out

    def get_accessories(self, kind):
        """All gun buddies, sprays or player cards."""
        if kind not in Api._acc:
            path = {"buddy": "buddies", "spray": "sprays", "card": "playercards", "title": "playertitles"}.get(kind)
            data = va_cached(path) if path else None
            if not data:
                return []
            out = []
            for d in data:
                if kind == "title":
                    t = d.get("titleText") or d.get("displayName")
                    if t:
                        out.append({"kind": "title", "id": d["uuid"], "name": d.get("displayName") or t, "text": t,
                                    "levels": [{"name": t, "text": t}], "chromas": []})
                    continue
                if kind == "buddy":
                    uid = ((d.get("levels") or [{}])[0]).get("uuid") or d["uuid"]  # the shop and loadout use the level id
                    icon = big = d.get("displayIcon")
                elif kind == "spray":
                    uid, icon = d["uuid"], d.get("fullTransparentIcon") or d.get("displayIcon")
                    big = d.get("animationGif") or icon
                else:
                    uid, icon = d["uuid"], d.get("wideArt") or d.get("displayIcon")
                    big = d.get("largeArt") or icon
                if icon:
                    out.append({"kind": kind, "id": uid, "name": d["displayName"], "icon": icon,
                                "levels": [{"name": d["displayName"], "icon": big}], "chromas": []})
            out.sort(key=lambda x: x["name"])
            Api._acc[kind] = out
        return Api._acc[kind]

    # ---------- Riot login ----------
    def has_session(self):
        return os.path.exists(vs.SESSION_FILE)

    def open_login_page(self):
        webbrowser.open(vs.AUTH_URL)

    def login(self, ssid):
        """Check a pasted ssid with Riot. On success the cookies are saved to riot_session.json."""
        ssid = (ssid or "").strip().strip('"').strip("'").strip()
        if ssid.lower().startswith("ssid="):
            ssid = ssid[5:].strip()
        if not ssid:
            return {"error": "Paste your ssid first."}
        log = io.StringIO()
        try:
            s = vs.make_session()
            s.cookies.set("ssid", ssid, domain="auth.riotgames.com", path="/")
            with contextlib.redirect_stdout(log):
                tokens = vs.cookie_tokens(s)  # saves the cookies itself when it works
            if not tokens:
                return {"error": "Riot did not accept this ssid. It sent the login back to the sign-in page.\n"
                                 "Copy a fresh ssid and try again. If your browser signs you out every time you "
                                 "reopen it (this happened in Chrome), log in with another browser such as Brave.\n\n"
                                 + log.getvalue()}
            try:
                os.remove(CACHE)
            except OSError:
                pass
            Api._tok = Api._owned = Api._name = None  # a different account may have logged in
            return {"ok": True}
        except Exception:
            return {"error": log.getvalue() + traceback.format_exc()}

    def logout(self):
        Api._tok = Api._owned = Api._name = None
        for p in (vs.SESSION_FILE, CACHE):
            try:
                os.remove(p)
            except OSError:
                pass

    _tok = None       # (tokens, time fetched)
    _ver = None
    _owned = None     # (data, time fetched)

    def _tokens(self, fresh=False):
        """Saved cookie first, then a running Riot Client. Never asks for input. Reused for 30 minutes."""
        if not fresh and Api._tok and time.time() - Api._tok[1] < 1800:
            return Api._tok[0]
        t = self._new_tokens()
        Api._tok = (t, time.time()) if t else None
        return t

    def _riot(self, method, path, body=None):
        """One signed request to Riot's game API. Returns a requests.Response, or None if not logged in."""
        r = None
        for attempt in (0, 1):
            t = self._tokens(fresh=bool(attempt))
            if not t:
                return None
            access, ent, puuid = t
            if Api._ver is None:
                Api._ver = vs.client_version()
            platform = base64.b64encode(json.dumps({
                "platformType": "PC", "platformOS": "Windows",
                "platformOSVersion": "10.0.19042.1.256.64bit", "platformChipset": "Unknown"}).encode()).decode()
            r = requests.request(method, f"https://pd.{vs.SHARD}.a.pvp.net" + path.format(puuid=puuid), json=body,
                                 timeout=25, headers={"Authorization": f"Bearer {access}",
                                                      "X-Riot-Entitlements-JWT": ent,
                                                      "X-Riot-ClientVersion": Api._ver,
                                                      "X-Riot-ClientPlatform": platform})
            if r.status_code == 401 or "BAD_CLAIMS" in r.text[:300]:
                continue  # token expired: get a new one and try once more
            break
        return r

    # ---------- inventory: what you own and what is equipped ----------
    _lo_ver = None
    _name = None

    def _loadout_req(self, method, body=None):
        """Riot moved the loadout from v2 to v3; use whichever one answers."""
        r = None
        for v in ([Api._lo_ver] if Api._lo_ver else ["v3", "v2"]):
            r = self._riot(method, "/personalization/" + v + "/players/{puuid}/playerloadout", body)
            if r is not None and r.status_code == 404 and not Api._lo_ver:
                continue
            if r is not None and r.ok:
                Api._lo_ver = v
            return r
        return r

    def _owned_items(self, fresh=False):
        if not fresh and Api._owned and time.time() - Api._owned[1] < 300:
            return Api._owned[0]
        out = {}
        for key, type_id in (("levels", SKIN), ("chromas", CHROMA), ("buddies", BUDDY), ("sprays", SPRAY),
                             ("cards", CARD), ("titles", TITLE)):
            r = self._riot("GET", "/store/v1/entitlements/{puuid}/" + type_id)
            if r is None:
                return None
            r.raise_for_status()
            d = r.json()
            ents = d.get("Entitlements")
            if ents is None:
                ents = [e for t in d.get("EntitlementsByTypes", []) for e in t.get("Entitlements", [])]
            out[key] = sorted({e["ItemID"].lower() for e in ents})
            if key == "buddies":  # every copy of a buddy has its own instance id, needed to equip it
                inst = {}
                for e in ents:
                    if e.get("InstanceID"):
                        inst.setdefault(e["ItemID"].lower(), []).append(e["InstanceID"])
                out["buddy_inst"] = inst
        Api._owned = (out, time.time())
        return out

    def _player_name(self):
        if Api._name is None:
            try:
                t = self._tokens()
                r = self._riot("PUT", "/name-service/v2/players", [t[2]])
                if r is not None and r.ok and r.json():
                    Api._name = r.json()[0].get("GameName") or ""
            except Exception:
                traceback.print_exc()
        return Api._name or ""

    def _describe_loadout(self, lo):
        """Turn Riot's loadout into names and pictures for the inventory page."""
        weapons, _ = self._load()
        skins = {s["uuid"]: (s, w) for w in weapons for s in w["skins"]}
        buddies = {l["uuid"]: b for b in (va_cached("buddies") or []) for l in b.get("levels", [])}
        sprays = {s["uuid"]: s for s in (va_cached("sprays") or [])}
        cards = {c["uuid"]: c for c in (va_cached("playercards") or [])}
        titles = {t["uuid"]: t for t in (va_cached("playertitles") or [])}
        guns = {}
        for g in lo.get("Guns", []):
            wid = (g.get("ID") or "").lower()
            hit = skins.get((g.get("SkinID") or "").lower())
            icon = name = None
            if hit:
                s, w = hit
                ch = next((c for c in s["chromas"] if c["uuid"] == (g.get("ChromaID") or "").lower()), None)
                lv = next((l for l in s["levels"] if l["uuid"] == (g.get("SkinLevelID") or "").lower()), None)
                icon = ((ch and (ch.get("fullRender") or ch.get("displayIcon"))) or (lv and lv.get("displayIcon"))
                        or s.get("displayIcon") or w.get("displayIcon"))
                name = s["displayName"]
            b = buddies.get((g.get("CharmLevelID") or "").lower())
            guns[wid] = {"skin": (g.get("SkinID") or "").lower(), "level": (g.get("SkinLevelID") or "").lower(),
                         "chroma": (g.get("ChromaID") or "").lower(), "icon": icon, "name": name,
                         "buddy": (g.get("CharmLevelID") or "").lower() or None,
                         "buddy_icon": b and b.get("displayIcon"), "buddy_name": b and b.get("displayName")}
        ident = lo.get("Identity") or {}
        c = cards.get((ident.get("PlayerCardID") or "").lower())
        t = titles.get((ident.get("PlayerTitleID") or "").lower())
        # spray wheel, in Riot's own order: old format "Sprays", new format "ActiveExpressions"
        wheel = []
        if "ActiveExpressions" in lo:
            slots = [((x.get("TypeID") or SPRAY).lower(), (x.get("AssetID") or "").lower())
                     for x in lo.get("ActiveExpressions") or []]
        else:
            slots = [(SPRAY, (x.get("SprayID") or "").lower()) for x in lo.get("Sprays") or []]
        for type_id, asset in slots:
            x = sprays.get(asset) if type_id == SPRAY else None
            if x:
                wheel.append({"kind": "spray", "id": asset, "name": x["displayName"],
                              "icon": x.get("fullTransparentIcon") or x.get("displayIcon")})
            else:
                f = va(f"flex/{asset}") if asset and type_id != SPRAY else None
                wheel.append({"kind": "other", "id": asset, "name": (f or {}).get("displayName") or "",
                              "icon": (f or {}).get("displayIcon")})
        return {"guns": guns, "wheel": wheel,
                "card": c and {"id": c["uuid"], "name": c["displayName"], "icon": c.get("largeArt") or c.get("displayIcon")},
                "title": t and {"id": t["uuid"], "text": t.get("titleText") or t.get("displayName") or ""}}

    def get_inventory(self, fresh=False):
        try:
            owned = self._owned_items(fresh)
            r = self._loadout_req("GET") if owned is not None else None
            if r is None:
                return {"error": "Not logged in."}
            if not r.ok:
                return {"error": f"Riot did not return your loadout (HTTP {r.status_code}). "
                                 "Riot may have changed how the loadout is read again."}
            _, idx = self._load()
            lv = set(owned["levels"])
            owned_skins = sorted({s["uuid"] for (s, _w) in idx.values() if any(l["uuid"] in lv for l in s["levels"])})
            favs = self._favs()
            return {"ok": True, "skins": owned_skins, **{k: v for k, v in owned.items() if k != "buddy_inst"},
                    "favs": favs if favs is not None else [], "favs_ok": favs is not None,
                    "name": self._player_name(), "loadout": self._describe_loadout(r.json())}
        except Exception as e:
            traceback.print_exc()
            return {"error": f"{type(e).__name__}: {e}"}

    # ---------- changing the loadout in the real game ----------
    def _change(self, mutate, check):
        """Read the loadout, change one thing, send it back, and confirm Riot applied it.
        Everything that is not being changed is sent back exactly as Riot gave it."""
        try:
            r = self._loadout_req("GET")
            if r is None or not r.ok:
                return {"error": f"Could not read your current loadout (HTTP {getattr(r, 'status_code', '?')})."}
            lo = r.json()
            if not lo.get("Guns") or not lo.get("Identity") or not ("Sprays" in lo or "ActiveExpressions" in lo):
                return {"error": "Riot's loadout looked different than expected, so nothing was changed."}
            note = {}
            err = mutate(lo, note)
            if err:
                return {"error": err}
            body = {k: v for k, v in lo.items() if k not in ("Subject", "Version")}
            r = self._loadout_req("PUT", body)
            if r is None or not r.ok:
                return {"error": f"Riot refused the change (HTTP {getattr(r, 'status_code', '?')}): "
                                 f"{(r.text[:300] if r is not None else '')}"}
            new = r.json()
            err = check(new)
            if err:
                return {"error": err}
            return {"ok": True, "loadout": self._describe_loadout(new), **note}
        except Exception as e:
            traceback.print_exc()
            return {"error": f"{type(e).__name__}: {e}"}

    @staticmethod
    def _gun(lo, weapon_id):
        return next((g for g in lo.get("Guns", []) if (g.get("ID") or "").lower() == weapon_id), None)

    def equip(self, weapon_id, skin_id, level_id, chroma_id=None):
        """Equip an owned skin (with a chosen level and variant) on one weapon."""
        try:
            weapons, _ = self._load()
            w = next((w for w in weapons if w["uuid"] == weapon_id), None)
            s = next((s for s in (w or {}).get("skins", []) if s["uuid"] == skin_id), None)
            if not s:
                return {"error": "That skin does not belong to this weapon."}
            if not any(l["uuid"] == level_id for l in s["levels"]):
                return {"error": "That level does not belong to this skin."}
            chromas = [c["uuid"] for c in s["chromas"]]
            chroma_id = chroma_id or (chromas[0] if chromas else None)
            if chroma_id not in chromas:
                return {"error": "That variant does not belong to this skin."}
            owned = self._owned_items(fresh=True)
            if owned is None:
                return {"error": "Not logged in."}
            if "Random Favorite" not in s["displayName"]:  # the random skin belongs to everyone
                if level_id not in owned["levels"]:
                    return {"error": "You do not own this skin level."}
                if chroma_id != chromas[0] and chroma_id not in owned["chromas"]:
                    return {"error": "You do not own this variant."}
        except Exception as e:
            traceback.print_exc()
            return {"error": f"{type(e).__name__}: {e}"}

        def mutate(lo, note):
            gun = self._gun(lo, weapon_id)
            if not gun:
                return "Riot's loadout looked different than expected, so nothing was changed."
            gun["SkinID"], gun["SkinLevelID"], gun["ChromaID"] = skin_id, level_id, chroma_id

        def check(new):
            if ((self._gun(new, weapon_id) or {}).get("SkinID") or "").lower() != skin_id:
                return "Riot answered, but the skin did not change."
        return self._change(mutate, check)

    def set_buddy(self, weapon_id, buddy_id=None):
        """Put an owned gun buddy on one weapon, or remove the buddy (buddy_id=None)."""
        try:
            parent = None
            if buddy_id:
                owned = self._owned_items(fresh=True)
                if owned is None:
                    return {"error": "Not logged in."}
                if buddy_id not in owned["buddies"]:
                    return {"error": "You do not own this gun buddy."}
                parent = next((b["uuid"] for b in (va_cached("buddies") or [])
                               if any(l["uuid"] == buddy_id for l in b.get("levels", []))), None)
                copies = owned.get("buddy_inst", {}).get(buddy_id, [])
                if not parent or not copies:
                    return {"error": "Riot did not list a usable copy of this gun buddy, so nothing was changed."}
        except Exception as e:
            traceback.print_exc()
            return {"error": f"{type(e).__name__}: {e}"}
        keys = ("CharmInstanceID", "CharmID", "CharmLevelID")

        def mutate(lo, note):
            gun = self._gun(lo, weapon_id)
            if not gun:
                return "Riot's loadout looked different than expected, so nothing was changed."
            if not buddy_id:
                for k in keys:
                    gun.pop(k, None)
                return
            if (gun.get("CharmLevelID") or "").lower() == buddy_id:
                return
            used = {(g.get("CharmInstanceID") or "").lower(): g for g in lo["Guns"] if g is not gun and g.get("CharmInstanceID")}
            free = [i for i in copies if i.lower() not in used]
            inst = free[0] if free else copies[0]
            if not free:  # every copy is on another weapon: move one over, like the game does
                other = used[inst.lower()]
                for k in keys:
                    other.pop(k, None)
                w = next((w for w in self._load()[0] if w["uuid"] == (other.get("ID") or "").lower()), None)
                note["moved_from"] = (w or {}).get("displayName") or "another weapon"
            gun["CharmInstanceID"], gun["CharmID"], gun["CharmLevelID"] = inst, parent, buddy_id

        def check(new):
            if ((self._gun(new, weapon_id) or {}).get("CharmLevelID") or "").lower() != (buddy_id or ""):
                return "Riot answered, but the gun buddy did not change."
        return self._change(mutate, check)

    def set_spray(self, slot, spray_id):
        """Change the spray in one slot of the spray wheel. Slots are Riot's own order."""
        try:
            slot = int(slot)
            owned = self._owned_items(fresh=True)
            if owned is None:
                return {"error": "Not logged in."}
            if spray_id not in owned["sprays"]:
                return {"error": "You do not own this spray."}
        except Exception as e:
            traceback.print_exc()
            return {"error": f"{type(e).__name__}: {e}"}

        def entry(lo):
            arr = lo.get("ActiveExpressions") if "ActiveExpressions" in lo else lo.get("Sprays")
            return arr[slot] if isinstance(arr, list) and 0 <= slot < len(arr) and isinstance(arr[slot], dict) else None

        def mutate(lo, note):
            e = entry(lo)
            if e is None:
                return "That spray slot is empty in Riot's data. Put any spray in it once in the game, then try again."
            if "ActiveExpressions" in lo:
                if "AssetID" not in e:
                    return "Riot's spray data looked different than expected, so nothing was changed."
                e["AssetID"], e["TypeID"] = spray_id, SPRAY
            else:
                e["SprayID"] = spray_id

        def check(new):
            e = entry(new) or {}
            if (e.get("AssetID") or e.get("SprayID") or "").lower() != spray_id:
                return "Riot answered, but the spray did not change."
        return self._change(mutate, check)

    def _set_identity(self, key, owned_key, item_id, what):
        try:
            owned = self._owned_items(fresh=True)
            if owned is None:
                return {"error": "Not logged in."}
            if item_id not in owned[owned_key]:
                return {"error": f"You do not own this {what}."}
        except Exception as e:
            traceback.print_exc()
            return {"error": f"{type(e).__name__}: {e}"}

        def mutate(lo, note):
            lo["Identity"][key] = item_id

        def check(new):
            if ((new.get("Identity") or {}).get(key) or "").lower() != item_id:
                return f"Riot answered, but the {what} did not change."
        return self._change(mutate, check)

    def set_title(self, title_id):
        return self._set_identity("PlayerTitleID", "titles", title_id, "title")

    def set_card(self, card_id):
        return self._set_identity("PlayerCardID", "cards", card_id, "player card")

    # ---------- favourites (synced with the game) ----------
    def _fav_raw(self):
        r = self._riot("GET", "/favorites/v1/players/{puuid}/favorites")
        if r is None or not r.ok:
            return None
        fc = r.json().get("FavoritedContent") or {}
        vals = fc.values() if isinstance(fc, dict) else fc
        return {(v.get("ItemID") or "").lower() for v in vals if isinstance(v, dict)}

    def _fav_ids(self):
        """Riot may store a favourite under the item's own id or its level id. Map every spelling to the
        id the app uses, and list the spellings to try for each item."""
        alias, spell, fam = {}, {}, {}
        for w in self._load()[0]:
            for s in w["skins"]:
                lv = [l["uuid"] for l in s["levels"]]
                spell[s["uuid"]] = [s["uuid"]] + lv[:1]
                fam[s["uuid"]] = "skin"
                for i in [s["uuid"]] + lv:
                    alias[i] = s["uuid"]
                for c in s["chromas"]:
                    alias[c["uuid"]] = c["uuid"]
                    spell[c["uuid"]] = [c["uuid"]]
        for b in va_cached("buddies") or []:
            lv = [l["uuid"] for l in b.get("levels", [])]
            if lv:
                spell[lv[0]] = [b["uuid"], lv[0]]
                fam[lv[0]] = "buddy"
                for i in [b["uuid"]] + lv:
                    alias[i] = lv[0]
        for name in ("sprays", "playercards"):
            for x in va_cached(name) or []:
                alias[x["uuid"]] = x["uuid"]
                spell[x["uuid"]] = [x["uuid"]]
        return alias, spell, fam

    def _favs(self, raw=None):
        raw = self._fav_raw() if raw is None else raw
        if raw is None:
            return None
        alias = self._fav_ids()[0]
        return sorted({alias[i] for i in raw if i in alias})

    def set_favorite(self, item_id, on):
        """Add or remove a favourite in the game, then read the list back to confirm it."""
        try:
            alias, spell, fam = self._fav_ids()
            raw = self._fav_raw()
            if raw is None:
                return {"error": "Your favorites could not be read from Riot."}
            if item_id not in spell:
                return {"error": "This item cannot be a favorite."}
            url, last = "/favorites/v1/players/{puuid}/favorites", ""
            if on:
                tries = spell[item_id]
                # follow whatever spelling the existing favourites already use
                if len(tries) > 1 and any(fam.get(alias.get(i)) == fam.get(item_id) and len(spell[alias[i]]) > 1
                                          and i == spell[alias[i]][1] for i in raw):
                    tries = tries[::-1]
                for cand in tries:
                    r = self._riot("POST", url, {"ItemID": cand})
                    last = f"HTTP {getattr(r, 'status_code', '?')}: {(r.text[:200] if r is not None else '')}"
                    if r is not None and r.ok:
                        break
            else:
                for cand in [i for i in raw if alias.get(i) == item_id]:
                    r = self._riot("DELETE", url + "/" + cand.replace("-", ""))
                    last = f"HTTP {getattr(r, 'status_code', '?')}: {(r.text[:200] if r is not None else '')}"
            favs = self._favs()
            if favs is None or (item_id in favs) != bool(on):
                return {"error": "Riot did not save the favorite. " + last, "favs": favs or []}
            return {"ok": True, "favs": favs}
        except Exception as e:
            traceback.print_exc()
            return {"error": f"{type(e).__name__}: {e}"}

    def _new_tokens(self):
        s = vs.make_session()
        if vs.load_cookies(s):
            with contextlib.redirect_stdout(io.StringIO()):
                t = vs.cookie_tokens(s)
            if t:
                return t
        return vs.local_tokens()

    # ---------- shop ----------
    def get_settings(self):
        return {**DEFAULTS, **(_read(SETTINGS) or {})}

    def save_settings(self, s):
        with open(SETTINGS, "w") as f:
            json.dump(s, f, indent=2)

    def get_shop(self, refresh=False):
        c = _read(CACHE)
        if c and not refresh and c.get("v") == CACHE_V and c["expires_at"] > time.time():
            return c
        try:
            if not self.has_session():
                return {"need_login": True}
            tokens = self._tokens()
            if not tokens:
                return {"need_login": True, "error": "Your saved Riot login has expired or stopped working. "
                                                     "Paste a fresh ssid to continue."}
            store = vs.get_storefront(*tokens)
            panel = store["SkinsPanelLayout"]
            offers = panel.get("SingleItemStoreOffers") or [
                {"Rewards": [{"ItemID": u}], "Cost": {}} for u in panel["SingleItemOffers"]
            ]
            skins = []
            for o in offers:
                x = self._skin(o["Rewards"][0]["ItemID"])
                if x:
                    x["price"] = o.get("Cost", {}).get(VP)
                    skins.append(x)

            bundles = []
            for b in (store.get("FeaturedBundle") or {}).get("Bundles", []):
                d = va(f"bundles/{b['DataAssetID']}")
                if not d:
                    continue
                items = []
                for it in b.get("Items", []):
                    info = it.get("Item", {})
                    x = self._item(info.get("ItemTypeID"), info.get("ItemID"))
                    if x:
                        x["price"] = it.get("DiscountedPrice", it.get("BasePrice"))
                        x["base"] = it.get("BasePrice")
                        items.append(x)
                items.sort(key=lambda x: (x["kind"] != "skin", -(x.get("price") or 0)))
                cost = b.get("TotalDiscountedCost") or b.get("TotalBaseCost") or {}
                bundles.append({"name": d["displayName"], "desc": d.get("extraDescription") or d.get("promoDescription") or "",
                                "icon": d.get("displayIcon2") or d.get("displayIcon"), "price": cost.get(VP),
                                "base": (b.get("TotalBaseCost") or {}).get(VP), "items": items,
                                "expires_at": time.time() + b.get("DurationRemainingInSeconds", 0)})

            # Night market (only present in the storefront while it is active)
            night = None
            try:
                bs = store.get("BonusStore") or {}
                items = []
                for o in bs.get("BonusStoreOffers", []):
                    off = o.get("Offer") or {}
                    x = self._skin(off["Rewards"][0]["ItemID"])
                    if x:
                        x["price"] = (o.get("DiscountCosts") or {}).get(VP)
                        x["base"] = (off.get("Cost") or {}).get(VP)
                        items.append(x)
                if items:
                    night = {"items": items,
                             "expires_at": time.time() + bs.get("BonusStoreRemainingDurationInSeconds", 0)}
            except Exception:
                traceback.print_exc()

            # Weekly accessory shop (paid with Kingdom Credits)
            acc = None
            try:
                ac = store.get("AccessoryStore") or {}
                items = []
                for o in ac.get("AccessoryStoreOffers", []):
                    off = o.get("Offer") or {}
                    r = off["Rewards"][0]
                    x = self._item(r.get("ItemTypeID"), r.get("ItemID"))
                    if x:
                        x["price"] = (off.get("Cost") or {}).get(KC)
                        x["cur"] = "kc"
                        items.append(x)
                if items:
                    acc = {"items": items,
                           "expires_at": time.time() + ac.get("AccessoryStoreRemainingDurationInSeconds", 0)}
            except Exception:
                traceback.print_exc()

            c = {"v": CACHE_V, "expires_at": time.time() + panel["SingleItemOffersRemainingDurationInSeconds"],
                 "skins": skins, "bundles": bundles, "night": night, "acc": acc}
            with open(CACHE, "w") as f:
                json.dump(c, f)
            return c
        except SystemExit as e:
            return {"error": str(e)}
        except Exception as e:
            return {"error": f"{type(e).__name__}: {e}"}

    # ---------- Windows startup ----------
    def get_startup(self):
        if not winreg:
            return False
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as k:
                winreg.QueryValueEx(k, "ValorantShop")
            return True
        except OSError:
            return False

    def set_startup(self, on):
        if not winreg:
            return False
        exe = sys.executable.replace("python.exe", "pythonw.exe")
        cmd = f'"{exe if os.path.exists(exe) else sys.executable}" "{os.path.join(HERE, "app.py")}" --background'
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE) as k:
            if on:
                winreg.SetValueEx(k, "ValorantShop", 0, winreg.REG_SZ, cmd)
            else:
                try:
                    winreg.DeleteValue(k, "ValorantShop")
                except OSError:
                    pass
        return self.get_startup()


def _make_launcher():
    """Write a double-clickable launcher that opens the app with no console window."""
    pw = _pythonw()
    if os.name != "nt" or not pw:
        return
    line = f'CreateObject("WScript.Shell").Run """{pw}"" ""{os.path.join(HERE, "app.py")}""", 0, False\n'
    path = os.path.join(HERE, "Valorant Shop.vbs")
    try:
        if not os.path.exists(path) or open(path).read() != line:
            with open(path, "w") as f:
                f.write(line)
    except OSError:
        pass


if __name__ == "__main__":
    if "--background" in sys.argv:
        # Silent mode (used by Windows startup): load/refresh the shop, then exit.
        shop = Api().get_shop()
        # hook for later, e.g. wishlist notifications: check shop["skins"] here
        sys.exit(0)
    _make_launcher()
    webview.create_window("Valorant Shop", os.path.join(HERE, "ui.html"), js_api=Api(),
                          width=1180, height=800, min_size=(860, 620))
    webview.start()
