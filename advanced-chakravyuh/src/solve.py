#!/usr/bin/env python3
"""
Reference solver for "Chakravyuh". Each stage prints what a player would see.

  python solve.py --png ../dist/chakravyuh.png --board http://localhost:8080
  python solve.py --png ../dist/chakravyuh.png --board-json ../../hosting/data/waypoint.json \
                  --pcap ../drive/ps7_capture.pcap

The two reverse-geocoding steps (coordinates -> place name) are human OSINT
steps; pass the names with --place1 / --place2 (defaults are the answers).
"""
import argparse, base64, json, re, struct, sys, urllib.parse, urllib.request
from collections import OrderedDict

import numpy as np
from PIL import Image

ap = argparse.ArgumentParser()
ap.add_argument("--png", default="../dist/chakravyuh.png")
ap.add_argument("--board", help="base URL of the CTF server, e.g. http://localhost:8080")
ap.add_argument("--board-json", default="../../hosting/data/waypoint.json")
ap.add_argument("--pcap", help="local pcap (otherwise downloaded from the drive link)")
ap.add_argument("--photo", default="../drive2/mayasabha.jpg", help="photo from the second drive")
ap.add_argument("--place1", default="Jyotisar")
ap.add_argument("--place2", default="Purana Qila")
a = ap.parse_args()


def banner(s):
    print("\n" + "=" * 70 + "\n" + s + "\n" + "=" * 70)


# ---------------------------------------------------------------- stage 1
banner("STAGE 1  image -> blue LSB -> base64 -> XOR(challenge name)")
img = Image.open(a.png)
print("tEXt chunks:", img.text)
arr = np.array(img.convert("RGB"))


def lsb_text(ch):
    bits = arr[:, :, ch].reshape(-1) & 1
    data = np.packbits(bits[: (bits.size // 8) * 8]).tobytes()
    return data.split(b"\0", 1)[0]


red, blue = lsb_text(0), lsb_text(2)
print("b1,r,lsb,xy :", red[:80], "->", base64.b64decode(red))
print("b1,b,lsb,xy :", blue[:60], "...")
raw = base64.b64decode(blue)
key = b"Chakravyuh"
note1 = bytes(c ^ key[i % len(key)] for i, c in enumerate(raw)).decode()
print(note1)
coords = re.search(r"(\d+)°(\d+)'(\d+)\"([NS]) (\d+)°(\d+)'(\d+)\"([EW])", note1).groups()
lat = int(coords[0]) + int(coords[1]) / 60 + int(coords[2]) / 3600
lon = int(coords[4]) + int(coords[5]) / 60 + int(coords[6]) / 3600
print(f"decimal: {lat:.5f}, {lon:.5f}   -> reverse geocode (human step): {a.place1}")


# ---------------------------------------------------------------- board helper
def board_search(q):
    if a.board:
        u = a.board.rstrip("/") + "/waypoint/api/search?q=" + urllib.parse.quote(q)
        return json.load(urllib.request.urlopen(u))["results"]
    places = json.load(open(a.board_json, encoding="utf-8"))["places"]
    ql = q.lower()
    return [p for p in places if ql in p["name"].lower() or any(ql in x.lower() for x in p["aliases"])]


def board_place(p):
    if a.board:
        return json.load(urllib.request.urlopen(a.board.rstrip("/") + "/waypoint/api/place/" + p["id"]))
    return p


def vig_dec(text, k):
    k, out, j = k.lower(), [], 0
    for ch in text:
        if ch.isascii() and ch.isalpha():
            base = 65 if ch.isupper() else 97
            out.append(chr((ord(ch) - base - (ord(k[j % len(k)]) - 97)) % 26 + base)); j += 1
        else:
            out.append(ch)
    return "".join(out)


# ---------------------------------------------------------------- stage 2
banner("STAGE 2  Waypoint board -> parth_sarathi -> Vigenere(PANCHAJANYA)")
place = board_place(board_search(a.place1)[0])
for c in place["comments"]:
    print(f"  [{c['user']}] {c['text'][:110]}")
msg = next(c["text"] for c in place["comments"] if c["user"] == "parth_sarathi")
ct = msg.split("  ", 1)[1]
pt = vig_dec(ct, "PANCHAJANYA")
print("\ndecrypted:", pt)
drive = re.search(r"https?://\S+", pt).group(0)
print("drive link:", drive)

# ---------------------------------------------------------------- stage 3
banner("STAGE 3  pcap -> accepted FC6 writes by the rogue to HR 40")
if a.pcap:
    pcap = open(a.pcap, "rb").read()
elif "drive.google.com" in drive:
    sys.exit("Google Drive folder: download ps7_capture.pcap from the link above in a browser, "
             "then re-run with --pcap <path>")
else:
    url = drive.rstrip("/") + "/ps7_capture.pcap"
    print("downloading", url)
    pcap = urllib.request.urlopen(url).read()

magic = struct.unpack("<I", pcap[:4])[0]
assert magic == 0xA1B2C3D4, "expect little-endian classic pcap"
off, frames = 24, []
while off < len(pcap):
    ts_s, ts_u, incl, _ = struct.unpack("<IIII", pcap[off:off + 16])
    frames.append((ts_s + ts_u / 1e6, pcap[off + 16: off + 16 + incl]))
    off += 16 + incl

seen_seg = set()
pending = {}              # (client, tid) -> request info
writes = []               # accepted FC6 writes, in time order
writers = {}
for ts, fr in frames:
    if fr[12:14] != b"\x08\x00":
        continue
    ihl = (fr[14] & 0xF) * 4
    tot = struct.unpack("!H", fr[16:18])[0]
    src, dst = ".".join(map(str, fr[26:30])), ".".join(map(str, fr[30:34]))
    t = 14 + ihl
    sp, dp, seq = struct.unpack("!HHI", fr[t:t + 8])
    doff = (fr[t + 12] >> 4) * 4
    payload = fr[t + doff: 14 + tot]
    if not payload or 502 not in (sp, dp):
        continue
    seg = (src, sp, dst, dp, seq)
    if seg in seen_seg:                       # TCP retransmission: same bytes again
        continue
    seen_seg.add(seg)
    tid, _, ln, uid = struct.unpack("!HHHB", payload[:7])
    pdu = payload[7:6 + ln]
    fc = pdu[0]
    if dp == 502:                             # request
        pending[(src, sp, tid)] = (ts, src, fc, pdu)
    else:                                     # response
        req = pending.pop((dst, dp, tid), None)
        if not req:
            continue
        if fc & 0x80:
            print(f"  {ts:.3f} exception fc={fc & 0x7F} code={pdu[1]} for request from {req[1]}")
            continue
        if fc == 6:
            addr, val = struct.unpack("!HH", req[3][1:5])
            writes.append((req[0], req[1], addr, val))
            writers.setdefault(req[1], set()).add(addr)

print("FC6 writers and target registers:", {k: sorted(v) for k, v in writers.items()})
for addr in (40, 42):
    vals = [v for _, s, ad, v in writes if s == "10.18.0.66" and ad == addr]
    raw = b"".join(struct.pack("!H", v) for v in vals)
    print(f"  HR{addr} by 10.18.0.66 -> {raw!r}")
vals = [v for _, s, ad, v in writes if s == "10.18.0.66" and ad == 40]
note3 = b"".join(struct.pack("!H", v) for v in vals).decode("latin-1")
drive2 = re.search(r"https?://[!-~]+", note3).group(0)
print("second drive link:", drive2)


# ---------------------------------------------------------------- stage 4
def exif_gps(path):
    ex = Image.open(path).getexif()
    print("  ImageDescription:", ex.get(0x010E))
    xp = ex.get(0x9C9C)
    if xp:
        print("  XPComment:", bytes(xp).decode("utf-16le").rstrip("\0"))
    g = ex.get_ifd(0x8825)
    dec = lambda t: float(t[0]) + float(t[1]) / 60 + float(t[2]) / 3600
    lat = dec(g[2]) * (1 if g[1] == "N" else -1)
    lon = dec(g[4]) * (1 if g[3] == "E" else -1)
    return lat, lon


banner("STAGE 4  second drive -> photo EXIF GPS -> place -> board -> Google Maps reviews")
plat, plon = exif_gps(a.photo)
print(f"GPS {plat:.5f}, {plon:.5f}  -> reverse geocode (human step): {a.place2}")
place = board_place(board_search(a.place2)[0])
for c in place["comments"]:
    print(f"  [{c['user']}] {c['text']}")
print("\nFinal step is manual: open the place on Google Maps, Reviews tab, find the GDG{...} review.")


