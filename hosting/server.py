#!/usr/bin/env python3
"""
GDG CTF mini host: one stdlib-only process that serves

  /                      CTF portal: both challenges, downloads, hints, flag checker
  /waypoint/             "Waypoint" traveller pin-board (Chakravyuh OSINT legs)
  /drive/<token>/        stand-in "shared drive" holding ps7_capture.pcap

No third-party packages. Configuration through environment variables:

  HOST              bind address                 (default 0.0.0.0)
  PORT              port                         (default 8080)
  CTF_ROOT          folder holding the challenge folders  (default: parent of this file)
  DRIVE_TOKEN       path token of the drive page (default 1Mz7vYhAbhimanyu-PS7rk)
  ENABLE_PORTAL     "0" to serve only /waypoint and /drive (e.g. when using CTFd)
"""
import html, json, os, re, threading, time, urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.environ.get("CTF_ROOT", os.path.join(HERE, "..")))
DATA = os.path.join(HERE, "data")
DRIVE_TOKEN = os.environ.get("DRIVE_TOKEN", "1Mz7vYhAbhimanyu-PS7rk")
ENABLE_PORTAL = os.environ.get("ENABLE_PORTAL", "1") != "0"
PCAP = os.path.join(ROOT, "advanced-chakravyuh", "drive", "ps7_capture.pcap")


def load(name):
    with open(os.path.join(DATA, name), encoding="utf-8") as f:
        return json.load(f)


CHALS = {c["id"]: c for c in load("challenges.json")["challenges"]}
FLAGS = load("flags.json")
PLACES = load("waypoint.json")["places"]
PLACE_BY_ID = {p["id"]: p for p in PLACES}
FILES = {f"/files/{c['id']}/{f['name']}": os.path.join(ROOT, f["path"])
         for c in CHALS.values() for f in c["files"]}

_lock = threading.Lock()
_attempts = {}          # (ip, chal) -> count
_rate = {}              # ip -> [timestamps]

E = html.escape

# --------------------------------------------------------------------------- styles
PORTAL_CSS = """
:root{--bg:#14110f;--card:#1f1a16;--ink:#f3e9dc;--mut:#b9a993;--acc:#e0a240;--red:#c0452f;--ok:#5fb37a;--line:#3a3029}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.55 system-ui,Segoe UI,Roboto,sans-serif}
main{max-width:860px;margin:0 auto;padding:28px 16px 60px}
h1{font:700 30px/1.2 Georgia,serif;margin:0 0 4px}h2{font:700 22px Georgia,serif;margin:0}
.sub{color:var(--mut);margin:0 0 26px}
.card{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:20px;margin:0 0 22px}
.tag{display:inline-block;font-size:12px;padding:2px 8px;border-radius:99px;border:1px solid var(--line);color:var(--mut);margin-right:6px}
.lvl{color:var(--acc);border-color:var(--acc)}
a{color:var(--acc)}p{margin:10px 0}
details{border-top:1px solid var(--line);padding:8px 0}summary{cursor:pointer;color:var(--mut)}
form{display:flex;gap:8px;flex-wrap:wrap;margin-top:12px}
input[type=text]{flex:1;min-width:200px;padding:10px;border-radius:8px;border:1px solid var(--line);background:#120f0d;color:var(--ink);font-family:ui-monospace,Consolas,monospace}
button{padding:10px 16px;border-radius:8px;border:0;background:var(--acc);color:#1b130b;font-weight:700;cursor:pointer}
.msg{padding:10px 12px;border-radius:8px;margin-top:10px}.ok{background:#1d3324;color:var(--ok)}.bad{background:#3a1d17;color:#f0a090}.warn{background:#3a2e14;color:#f0cf80}
footer{color:var(--mut);font-size:13px;text-align:center}
"""

BOARD_CSS = """
:root{--bg:#f6f4ef;--ink:#1f2a2e;--mut:#62717a;--acc:#1f7a6d;--card:#fff;--line:#e2ddd2}
@media (prefers-color-scheme:dark){:root:not([data-theme=light]){--bg:#121816;--ink:#e6efec;--mut:#93a4a0;--acc:#4fc1ae;--card:#1a2220;--line:#2a3532}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.55 system-ui,Segoe UI,Roboto,sans-serif}
header{background:var(--acc);color:#fff;padding:14px 16px}header a{color:#fff;text-decoration:none;font-weight:800;font-size:20px}
header span{opacity:.85;margin-left:8px;font-size:14px}
main{max-width:760px;margin:0 auto;padding:22px 16px 50px}
form{display:flex;gap:8px;margin:0 0 20px}input{flex:1;padding:10px;border:1px solid var(--line);border-radius:8px;background:var(--card);color:var(--ink)}
button{padding:10px 16px;border:0;border-radius:8px;background:var(--acc);color:#fff;font-weight:700}
.place{display:block;background:var(--card);border:1px solid var(--line);border-radius:10px;padding:12px 14px;margin:0 0 10px;color:var(--ink);text-decoration:none}
.place small{color:var(--mut)}
.c{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:12px 14px;margin:0 0 10px}
.c b{color:var(--acc)}.c time{color:var(--mut);font-size:13px;margin-left:8px}
.c p{margin:6px 0 0;word-break:break-word;font-family:ui-monospace,Consolas,monospace;font-size:14px}
.mut{color:var(--mut)}
"""

DRIVE_CSS = """
:root{--bg:#f8fafd;--ink:#1f1f1f;--mut:#5f6368;--line:#dadce0;--acc:#0b57d0}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.5 system-ui,Segoe UI,Roboto,sans-serif}
main{max-width:760px;margin:0 auto;padding:26px 16px}
.row{display:flex;justify-content:space-between;gap:10px;flex-wrap:wrap;background:#fff;border:1px solid var(--line);border-radius:10px;padding:14px}
a{color:var(--acc)}.mut{color:var(--mut)}
"""


def page(title, css, body, theme=None):
    return (f"<!doctype html><html lang=en><head><meta charset=utf-8>"
            f"<meta name=viewport content='width=device-width,initial-scale=1'>"
            f"<title>{E(title)}</title><style>{css}</style></head><body>{body}</body></html>").encode()


# --------------------------------------------------------------------------- views
def portal(msgs=None):
    msgs = msgs or {}
    cards = []
    for c in CHALS.values():
        files = " ".join(f"<a href='/files/{c['id']}/{E(f['name'])}' download>{E(f['name'])}</a>" for f in c["files"])
        hints = "".join(f"<details><summary>Hint {i + 1}</summary><p>{E(h)}</p></details>"
                        for i, h in enumerate(c["hints"]))
        lim = f" &middot; {c['max_attempts']} attempts" if c.get("max_attempts") else ""
        cards.append(f"""<section class=card id='{c['id']}'>
<span class='tag lvl'>{E(c['level'])}</span><span class=tag>{E(c['category'])}</span><span class=tag>{c['points']} pts{lim}</span>
<h2 style='margin-top:10px'>{E(c['name'])}</h2><p>{E(c['story'])}</p>
<p><b>Files:</b> {files}</p>{hints}
<form method=post action='/submit#{c['id']}'><input type=hidden name=chal value='{c['id']}'>
<input type=text name=flag placeholder='GDG{{...}}' autocomplete=off required><button>Submit</button></form>
{msgs.get(c['id'], '')}</section>""")
    body = (f"<main><h1>GDG CTF</h1><p class=sub>Two challenges: one to learn on, one to get lost in. "
            f"Flag format <code>GDG{{...}}</code>. Everything here is fictional; no real systems or people.</p>"
            f"{''.join(cards)}<footer>Waypoint board: <a href='/waypoint/'>/waypoint</a></footer></main>")
    return page("GDG CTF", PORTAL_CSS, body)


def check_flag(ip, chal, flag):
    c = CHALS.get(chal)
    if not c:
        return "<div class='msg bad'>Unknown challenge.</div>"
    flag = flag.strip()
    with _lock:
        now = time.time()
        _rate[ip] = [t for t in _rate.get(ip, []) if now - t < 60] + [now]
        if len(_rate[ip]) > 20:
            return "<div class='msg warn'>Slow down: too many submissions in a minute.</div>"
        lim = c.get("max_attempts") or 0
        used = _attempts.get((ip, chal), 0)
        if lim and used >= lim:
            return "<div class='msg bad'>No attempts left for this challenge.</div>"
        if flag == FLAGS[chal]["flag"]:
            return "<div class='msg ok'>Correct! You found the way out.</div>"
        _attempts[(ip, chal)] = used + 1
        left = f" ({lim - used - 1} attempts left)" if lim else ""
        if flag in FLAGS[chal]["decoys"]:
            return f"<div class='msg warn'>That is one of Shakuni's loaded dice: a decoy flag.{left}</div>"
        return f"<div class='msg bad'>Wrong flag.{left}</div>"


def board_home(q=None):
    res = ""
    if q is not None:
        hits = search(q)
        if len(q.strip()) < 4:
            res = "<p class=mut>Type at least 4 letters of a place name.</p>"
        elif not hits:
            res = f"<p class=mut>No pins for &ldquo;{E(q)}&rdquo;. Waypoint searches place names only.</p>"
        else:
            res = "".join(f"<a class=place href='/waypoint/place/{p['id']}'><b>{E(p['name'])}</b><br>"
                          f"<small>{E(p['region'])} &middot; {len(p['comments'])} notes</small></a>" for p in hits)
    body = (f"<header><a href='/waypoint/'>Waypoint</a><span>notes travellers pin to places</span></header><main>"
            f"<form action='/waypoint/search'><input name=q placeholder='Search a place name' value='{E(q or '')}'>"
            f"<button>Search</button></form>{res or '<p class=mut>Search by place name to read what travellers pinned there.</p>'}</main>")
    return page("Waypoint", BOARD_CSS, body)


def search(q):
    q = (q or "").strip().lower()
    if len(q) < 4:
        return []
    return [p for p in PLACES if q in p["name"].lower() or any(q in a.lower() for a in p["aliases"])]


def board_place(p):
    cs = "".join(f"<div class=c><b>@{E(c['user'])}</b><time>{E(c['date'])}</time><p>{E(c['text'])}</p></div>"
                 for c in p["comments"])
    body = (f"<header><a href='/waypoint/'>Waypoint</a><span>notes travellers pin to places</span></header><main>"
            f"<h1 style='margin:0'>{E(p['name'])}</h1><p class=mut>{E(p['region'])}</p>{cs}</main>")
    return page(f"{p['name']} - Waypoint", BOARD_CSS, body)


def drive_page():
    size = os.path.getsize(PCAP) if os.path.exists(PCAP) else 0
    body = (f"<main><h2>Shared with you: PS7-shift-logs</h2><p class=mut>Owner: parth_sarathi &middot; view only</p>"
            f"<div class=row><span>ps7_capture.pcap</span><span class=mut>{size // 1024} KB</span>"
            f"<a href='ps7_capture.pcap' download>Download</a></div></main>")
    return page("PS7-shift-logs - Drive", DRIVE_CSS, body)


# --------------------------------------------------------------------------- handler
class H(BaseHTTPRequestHandler):
    server_version = "gdg-ctf/1.0"

    def log_message(self, fmt, *args):
        print("%s %s" % (self.client_address[0], fmt % args), flush=True)

    def send(self, code, body, ctype="text/html; charset=utf-8", extra=None):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("X-Content-Type-Options", "nosniff")
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def send_file(self, path, ctype, name):
        with open(path, "rb") as f:
            data = f.read()
        self.send(200, data, ctype, {"Content-Disposition": f'attachment; filename="{name}"'})

    def jsend(self, obj, code=200):
        self.send(code, json.dumps(obj, ensure_ascii=False).encode(), "application/json; charset=utf-8")

    def nf(self):
        self.send(404, b"not found", "text/plain")

    def do_HEAD(self):
        self.do_GET()

    def do_GET(self):
        u = urllib.parse.urlsplit(self.path)
        path, qs = u.path, urllib.parse.parse_qs(u.query)
        if path == "/" and ENABLE_PORTAL:
            return self.send(200, portal())
        if path in FILES and ENABLE_PORTAL:
            ctype = "image/png" if path.endswith(".png") else "application/octet-stream"
            return self.send_file(FILES[path], ctype, os.path.basename(path))
        if path in ("/waypoint", "/waypoint/"):
            return self.send(200, board_home())
        if path == "/waypoint/search":
            return self.send(200, board_home(qs.get("q", [""])[0]))
        m = re.fullmatch(r"/waypoint/place/([0-9a-f]{8})", path)
        if m and m.group(1) in PLACE_BY_ID:
            return self.send(200, board_place(PLACE_BY_ID[m.group(1)]))
        if path == "/waypoint/api/search":
            hits = [{"id": p["id"], "name": p["name"], "region": p["region"]} for p in search(qs.get("q", [""])[0])]
            return self.jsend({"results": hits})
        m = re.fullmatch(r"/waypoint/api/place/([0-9a-f]{8})", path)
        if m and m.group(1) in PLACE_BY_ID:
            p = PLACE_BY_ID[m.group(1)]
            return self.jsend({"id": p["id"], "name": p["name"], "region": p["region"], "comments": p["comments"]})
        if path == f"/drive/{DRIVE_TOKEN}":
            return self.send(301, b"", extra={"Location": path + "/"})
        if path == f"/drive/{DRIVE_TOKEN}/":
            return self.send(200, drive_page())
        if path == f"/drive/{DRIVE_TOKEN}/ps7_capture.pcap":
            return self.send_file(PCAP, "application/vnd.tcpdump.pcap", "ps7_capture.pcap")
        if path == "/healthz":
            return self.send(200, b"ok", "text/plain")
        return self.nf()

    def do_POST(self):
        if self.path.split("#")[0] != "/submit" or not ENABLE_PORTAL:
            return self.nf()
        n = min(int(self.headers.get("Content-Length") or 0), 4096)
        form = urllib.parse.parse_qs(self.rfile.read(n).decode("utf-8", "replace"))
        chal, flag = form.get("chal", [""])[0], form.get("flag", [""])[0]
        self.send(200, portal({chal: check_flag(client_ip(self), chal, flag)}))


def client_ip(h):
    """Player IP for the attempt limit.
    Behind Cloudflare, CF-Connecting-IP is set by Cloudflare itself. Behind Render (or any
    reverse proxy), the proxy APPENDS the real client IP to X-Forwarded-For, so only the
    LAST entry is trustworthy: a player can fake the first ones to dodge the limit."""
    cf = h.headers.get("CF-Connecting-IP")
    if cf:
        return cf.strip()
    xff = h.headers.get("X-Forwarded-For")
    if xff:
        return xff.split(",")[-1].strip()
    return h.client_address[0]


def main():
    host, port = os.environ.get("HOST", "0.0.0.0"), int(os.environ.get("PORT", "8080"))
    for p in list(FILES.values()) + [PCAP]:
        if not os.path.exists(p):
            raise SystemExit(f"missing {p}: run the build scripts first")
    print(f"GDG CTF on http://{host}:{port}  (portal={'on' if ENABLE_PORTAL else 'off'}, drive=/drive/{DRIVE_TOKEN}/)")
    ThreadingHTTPServer((host, port), H).serve_forever()


if __name__ == "__main__":
    main()
