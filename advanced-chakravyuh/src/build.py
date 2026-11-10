#!/usr/bin/env python3
"""
Build script for the GDG advanced challenge "Chakravyuh"
(stego -> OSINT -> OT/ICS forensics -> OSINT, Mahabharata theme).

Everything is synthetic: a drawn image, a fictional water works
("Mayasabha Jal Kendra"), private 10.18.0.0/24 addresses, made-up board users
named after Mahabharata characters. The real-world places are public heritage
sites; nothing is posted to any real review site.

Outputs
  ../dist/chakravyuh.png             <- given to players
  ../drive/ps7_capture.pcap          <- served behind the "drive" link only
  ../../hosting/data/waypoint.json   <- board content (pins + comments)
  ../../hosting/data/flags.json      <- real + decoy flags for the checker

Usage
  python build.py [--drive-url URL]
  --drive-url  where you will host ps7_capture.pcap (Google Drive share link,
               or the bundled server's /drive/... page). Only waypoint.json
               depends on it, so you can rebuild later without changing the
               image or the pcap.

Needs: Python 3.9+, numpy, Pillow.
"""
import argparse, base64, json, math, os, random, struct

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from PIL.PngImagePlugin import PngInfo

HERE = os.path.dirname(os.path.abspath(__file__))
CH = os.path.normpath(os.path.join(HERE, ".."))
HOSTDATA = os.path.normpath(os.path.join(CH, "..", "hosting", "data"))

CHALLENGE_NAME = "Chakravyuh"          # layer-1 XOR key = the challenge name
CONCH_KEY = "PANCHAJANYA"              # layer-2 Vigenere key (Krishna's conch)
TRUSTED_1 = "parth_sarathi"
TRUSTED_2 = "vidura"
FLAG = "GDG{4bh1m4nyu_f0und_th3_3x1t_v14_m0dbu5}"
DEFAULT_DRIVE = "http://localhost:8080/drive/1Mz7vYhAbhimanyu-PS7rk/"

# Jyotisar (Wikipedia infobox): 29 57 41 N, 76 46 16 E
# Purana Qila (Wikipedia/DBpedia): 28.609444 N, 77.244167 E
PURANA_QILA = (28.609444, 77.244167)

DEFAULT_DRIVE2 = "https://drive.google.com/drive/folders/SECOND-DRIVE-FOLDER-ID"

# Every decoy is obviously a trap once read, so a player who finds one knows they
# took a wrong turn instead of wasting an attempt on it.
DEC_TEXT   = "GDG{dr0n4_s4ys_l00k_d33p3r}"
DEC_RED    = "GDG{wr0ng_ch4nn3l_p4rth4}"
DEC_JYO    = "GDG{sh4kuni_s4ys_n1c3_try}"
DEC_DURY   = "GDG{duryodh4n_n3v3r_t3lls_th3_truth}"
DEC_BRAHMA = "GDG{wr0ng_w4t3r_sh4kun1_w1ns}"
DEC_FC16   = "GDG{th3_plc_r3j3ct3d_th1s_l13}"
DEC_HR42   = "GDG{m4y4_s4bh4_1llus10n_n0t_r34l}"
DEC_PHOTO  = "GDG{y0u_f3ll_1n_th3_m4y4_p00l}"
DEC_PQ_SHA = "GDG{l04d3d_d1c3_r0ll3d_4g41n}"
DEC_PQ_KAR = "GDG{k4rn4_g1v3s_0nly_f4k3s}"
DEC_PQ_VID = "GDG{f4k3_v1dur_f4k3_fl4g}"
DEC_ZOO    = "GDG{t00_f4r_fr0m_1ndr4pr4sth4}"

DECOYS = {
    DEC_TEXT:   "PNG tEXt Comment",
    DEC_RED:    "PNG red-channel LSB",
    DEC_JYO:    "Waypoint / Jyotisar (shakuni)",
    DEC_DURY:   "Waypoint / Jyotisar (duryodhan, base64)",
    DEC_BRAHMA: "Waypoint / Brahma Sarovar (shakuni)",
    DEC_FC16:   "pcap: rejected FC16 write (strings bait)",
    DEC_HR42:   "pcap: honeypot holding register 42",
    DEC_PHOTO:  "photo EXIF XPComment",
    DEC_PQ_SHA: "Waypoint / Purana Qila (shakuni)",
    DEC_PQ_KAR: "Waypoint / Purana Qila (karna_daanveer)",
    DEC_PQ_VID: "Waypoint / Purana Qila (vidur - lookalike user)",
    DEC_ZOO:    "Waypoint / National Zoological Park (shakuni)",
}

rng = random.Random(18)                # 18 days of war -> fixed seed


def font(size, bold=True):
    names = ["georgiab.ttf", "arialbd.ttf", "DejaVuSerif-Bold.ttf", "DejaVuSans-Bold.ttf"] if bold \
        else ["georgia.ttf", "arial.ttf", "DejaVuSerif.ttf", "DejaVuSans.ttf"]
    for d in ["C:/Windows/Fonts", "/usr/share/fonts/truetype/dejavu", "/Library/Fonts"]:
        for n in names:
            p = os.path.join(d, n)
            if os.path.exists(p):
                return ImageFont.truetype(p, size)
    return ImageFont.load_default(size=size)


def xor(data: bytes, key: bytes) -> bytes:
    return bytes(b ^ key[i % len(key)] for i, b in enumerate(data))


def vigenere(text: str, key: str, decrypt=False) -> str:
    """CyberChef / dCode compatible: letters only, case kept, key advances on letters."""
    key = key.lower()
    out, j = [], 0
    for ch in text:
        if ch.isascii() and ch.isalpha():
            k = ord(key[j % len(key)]) - 97
            k = -k if decrypt else k
            base = 65 if ch.isupper() else 97
            out.append(chr((ord(ch) - base + k) % 26 + base))
            j += 1
        else:
            out.append(ch)
    return "".join(out)


_GH = "0123456789bcdefghjkmnpqrstuvwxyz"


def geohash(lat, lon, n=9):
    la, lo, bits, even, out = [-90.0, 90.0], [-180.0, 180.0], [], True, ""
    while len(out) < n:
        rngv, v = (lo, lon) if even else (la, lat)
        mid = (rngv[0] + rngv[1]) / 2
        if v >= mid:
            bits.append(1); rngv[0] = mid
        else:
            bits.append(0); rngv[1] = mid
        even = not even
        if len(bits) == 5:
            out += _GH[int("".join(map(str, bits)), 2)]; bits = []
    return out


# =========================================================================
# Layer 1 - the image
# =========================================================================
LAYER1_NOTE = (
    "|| CHAKRAVYUH : the first ring ||\n"
    "The charioteer spoke where the old banyan still stands.\n"
    "29\u00b057'41\"N 76\u00b046'16\"E\n"
    "Maps lie. Read the Waypoint board on this CTF server (/waypoint).\n"
    f"Only {TRUSTED_1} speaks the truth.\n"
)


def embed_lsb(arr, channel, payload: bytes):
    bits = np.unpackbits(np.frombuffer(payload, dtype=np.uint8))       # MSB first
    flat = arr[:, :, channel].reshape(-1)                               # row major (xy)
    assert len(bits) <= flat.size
    flat[:len(bits)] = (flat[:len(bits)] & 0xFE) | bits
    arr[:, :, channel] = flat.reshape(arr.shape[0], arr.shape[1])


def make_image():
    W = H = 1000
    img = Image.new("RGB", (W, H), (236, 220, 186))
    d = ImageDraw.Draw(img)
    # parchment speckle
    for _ in range(9000):
        x, y = rng.randrange(W), rng.randrange(H)
        c = rng.randrange(200, 232)
        d.point((x, y), fill=(c, c - 18, c - 50))
    cx, cy = W // 2, H // 2 + 30
    # seven rings with gates at rotating positions
    for k in range(7):
        r = 70 + k * 52
        gate = (k * 137 + 40) % 360
        d.arc([cx - r, cy - r, cx + r, cy + r], gate + 14, gate + 360 - 14,
              fill=(120, 28, 20), width=9)
        for s in range(0, 360, 30):                        # warrior marks on each ring
            if abs(((s - gate + 180) % 360) - 180) < 20:
                continue
            a = math.radians(s + k * 9)
            x, y = cx + r * math.cos(a), cy + r * math.sin(a)
            d.ellipse([x - 5, y - 5, x + 5, y + 5], fill=(60, 40, 20))
    # chakra at the centre
    d.ellipse([cx - 40, cy - 40, cx + 40, cy + 40], outline=(170, 110, 20), width=6)
    for s in range(0, 360, 30):
        a = math.radians(s)
        d.line([(cx, cy), (cx + 38 * math.cos(a), cy + 38 * math.sin(a))], fill=(170, 110, 20), width=3)
    # the lone path in
    d.line([(cx, H - 20), (cx, cy + 70 + 6 * 52 + 10)], fill=(40, 90, 140), width=5)
    d.text((W // 2, 40), "CHAKRAVYUH", font=font(64), fill=(110, 25, 15), anchor="mt")
    d.text((W // 2, 115), "seven rings  \u00b7  one way in  \u00b7  no way out",
           font=font(26, False), fill=(70, 45, 25), anchor="mt")

    arr = np.array(img, dtype=np.uint8)
    secret = base64.b64encode(xor(LAYER1_NOTE.encode(), CHALLENGE_NAME.encode())) + b"\x00"
    embed_lsb(arr, 2, secret)                                           # blue, bit 0
    decoy = base64.b64encode(DEC_RED.encode()) + b"\x00"
    embed_lsb(arr, 0, decoy)                                            # red, bit 0

    meta = PngInfo()
    meta.add_text("Title", "Chakravyuh")
    meta.add_text("Author", "Dronacharya")
    meta.add_text("Comment", DEC_TEXT)
    meta.add_text("Description", "Abhimanyu knew the way in. Do you know the way out?")
    out = os.path.join(CH, "dist", "chakravyuh.png")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    Image.fromarray(arr).save(out, pnginfo=meta)
    return out


# =========================================================================
# Layer 3 - the OT capture (Modbus/TCP), written byte by byte
# =========================================================================
HOSTS = {   # ip: (mac, ttl)
    "10.18.0.10": ("02:4d:59:00:00:0a", 64),    # PLC-A  pump station 7 (dosing)
    "10.18.0.11": ("02:4d:59:00:00:0b", 64),    # PLC-B  reservoir
    "10.18.0.20": ("02:4d:59:00:00:14", 64),    # HMI
    "10.18.0.30": ("02:4d:59:00:00:1e", 64),    # historian
    "10.18.0.66": ("02:5a:4b:55:4e:49", 128),   # rogue laptop
}
_ipid = {ip: rng.randrange(1, 60000) for ip in HOSTS}


def _csum(b: bytes) -> int:
    if len(b) % 2:
        b += b"\0"
    s = sum(struct.unpack(f"!{len(b)//2}H", b))
    while s >> 16:
        s = (s & 0xFFFF) + (s >> 16)
    return ~s & 0xFFFF


def _ip(a):
    return bytes(int(x) for x in a.split("."))


def _mac(m):
    return bytes.fromhex(m.replace(":", ""))


def tcp_frame(src, dst, sport, dport, seq, ack, flags, payload=b"", opts=b""):
    doff = (20 + len(opts)) // 4
    tcp = struct.pack("!HHIIBBHHH", sport, dport, seq & 0xFFFFFFFF, ack & 0xFFFFFFFF,
                      doff << 4, flags, 64240 if flags & 0x02 else 8192, 0, 0) + opts + payload
    pseudo = _ip(src) + _ip(dst) + struct.pack("!BBH", 0, 6, len(tcp))
    c = _csum(pseudo + tcp)
    tcp = tcp[:16] + struct.pack("!H", c) + tcp[18:]
    _ipid[src] = (_ipid[src] + 1) & 0xFFFF
    iph = struct.pack("!BBHHHBBH4s4s", 0x45, 0, 20 + len(tcp), _ipid[src], 0x4000,
                      HOSTS[src][1], 6, 0, _ip(src), _ip(dst))
    iph = iph[:10] + struct.pack("!H", _csum(iph)) + iph[12:]
    eth = _mac(HOSTS[dst][0]) + _mac(HOSTS[src][0]) + b"\x08\x00"
    fr = eth + iph + tcp
    return fr + b"\0" * max(0, 60 - len(fr))


class Pcap:
    def __init__(self, t0):
        self.t0, self.frames = t0, []

    def add(self, t, fr):
        self.frames.append((t, fr))

    def write(self, path):
        self.frames.sort(key=lambda x: x[0])
        with open(path, "wb") as f:
            f.write(struct.pack("<IHHiIII", 0xA1B2C3D4, 2, 4, 0, 0, 65535, 1))
            for t, fr in self.frames:
                ts = self.t0 + t
                sec = int(ts)
                f.write(struct.pack("<IIII", sec, int(round((ts - sec) * 1e6)) % 1000000, len(fr), len(fr)))
                f.write(fr)


class Conn:
    """One Modbus/TCP connection, client -> server:502."""
    MSS = b"\x02\x04\x05\xb4"

    def __init__(self, pc, cli, srv, t):
        self.pc, self.cli, self.srv = pc, cli, srv
        self.sport = rng.randrange(49152, 65000)
        self.cs, self.ss = rng.randrange(2**32), rng.randrange(2**32)
        pc.add(t, tcp_frame(cli, srv, self.sport, 502, self.cs, 0, 0x02, opts=self.MSS))
        pc.add(t + 0.0004, tcp_frame(srv, cli, 502, self.sport, self.ss, self.cs + 1, 0x12, opts=self.MSS))
        pc.add(t + 0.0006, tcp_frame(cli, srv, self.sport, 502, self.cs + 1, self.ss + 1, 0x10))
        self.cs += 1; self.ss += 1
        self.tid = rng.randrange(1, 4000)

    def req(self, t, pdu, uid=1, retrans_after=None):
        self.tid = (self.tid + 1) & 0xFFFF
        adu = struct.pack("!HHHB", self.tid, 0, len(pdu) + 1, uid) + pdu
        self.pc.add(t, tcp_frame(self.cli, self.srv, self.sport, 502, self.cs, self.ss, 0x18, adu))
        if retrans_after:   # same segment again: a TCP retransmission
            self.pc.add(t + retrans_after,
                        tcp_frame(self.cli, self.srv, self.sport, 502, self.cs, self.ss, 0x18, adu))
        self.cs += len(adu)
        return self.tid

    def resp(self, t, tid, pdu, uid=1):
        adu = struct.pack("!HHHB", tid, 0, len(pdu) + 1, uid) + pdu
        self.pc.add(t, tcp_frame(self.srv, self.cli, 502, self.sport, self.ss, self.cs, 0x18, adu))
        self.ss += len(adu)
        # delayed ACK from the client
        self.pc.add(t + 0.04, tcp_frame(self.cli, self.srv, self.sport, 502, self.cs, self.ss, 0x10))

    def close(self, t):
        self.pc.add(t, tcp_frame(self.cli, self.srv, self.sport, 502, self.cs, self.ss, 0x11))
        self.pc.add(t + 0.0004, tcp_frame(self.srv, self.cli, 502, self.sport, self.ss, self.cs + 1, 0x11))
        self.pc.add(t + 0.0006, tcp_frame(self.cli, self.srv, self.sport, 502, self.cs + 1, self.ss + 1, 0x10))


class PLC:
    def __init__(self, name):
        self.name = name
        self.hr = {i: 0 for i in range(0, 2048)}
        self.coils = [0] * 16
        self.t = 0.0

    def step(self, t):
        pass


def make_pcap(note: str):
    pc = Pcap(t0=1760494380.0)      # 2025-10-15 02:13:00 UTC
    DUR = 420.0
    plcA, plcB = PLC("A"), PLC("B")
    plcA.hr.update({40: 120, 41: 850, 42: 300, 43: 50})   # dose x100 ppm, hi, lo, alarm
    plcB.hr.update({0: 6120, 1: 1, 2: 0, 3: 412, 4: 0, 5: 7})

    def process(plc, t):
        if plc is plcA:
            lvl = int(612 + 140 * math.sin(t / 47) + rng.randrange(-3, 4))
            pump = 1 if math.sin(t / 47) < 0 else 0
            plc.hr.update({0: lvl, 1: pump, 2: 1 - pump, 3: int(380 + 40 * pump + rng.randrange(-5, 6)),
                           4: int(plc.hr[40] * 0.97 + rng.randrange(-2, 3)), 5: 731 + rng.randrange(-2, 3),
                           6: 2240 + rng.randrange(-15, 16), 7: 0, 8: int(t) & 0xFFFF, 9: 1})
            plc.coils[:8] = [pump, 1 - pump, 1, 0, 0, 1, 0, 1]
        else:
            plc.hr[0] = 6120 + int(30 * math.sin(t / 90)) + rng.randrange(-2, 3)

    def regs(plc, a, n):
        return b"".join(struct.pack("!H", plc.hr[a + i] & 0xFFFF) for i in range(n))

    events = []   # (t, order, fn)

    # --- legit traffic ---------------------------------------------------
    hmiA = Conn(pc, "10.18.0.20", "10.18.0.10", 0.020)
    hmiB = Conn(pc, "10.18.0.20", "10.18.0.11", 0.031)
    hisA = Conn(pc, "10.18.0.30", "10.18.0.10", 0.553)
    hisB = Conn(pc, "10.18.0.30", "10.18.0.11", 0.561)

    def poll_hmiA(t):
        process(plcA, t)
        tid = hmiA.req(t, struct.pack("!BHH", 3, 0, 10))
        hmiA.resp(t + 0.0031, tid, bytes([3, 20]) + regs(plcA, 0, 10))
        tid = hmiA.req(t + 0.050, struct.pack("!BHH", 1, 0, 8))
        bits = sum(b << i for i, b in enumerate(plcA.coils[:8]))
        hmiA.resp(t + 0.0528, tid, bytes([1, 1, bits]))
        tid = hmiA.req(t + 0.100, struct.pack("!BHH", 3, 40, 4))
        hmiA.resp(t + 0.1029, tid, bytes([3, 8]) + regs(plcA, 40, 4))

    def poll_hmiB(t):
        process(plcB, t)
        tid = hmiB.req(t, struct.pack("!BHH", 3, 0, 6))
        hmiB.resp(t + 0.0042, tid, bytes([3, 12]) + regs(plcB, 0, 6))

    def poll_his(conn, plc):
        def f(t):
            tid = conn.req(t, struct.pack("!BHH", 4, 0, 6))
            conn.resp(t + 0.0035, tid, bytes([4, 12]) + regs(plc, 0, 6))
        return f

    t = 0.2
    while t < DUR:
        events.append((t + rng.uniform(-0.004, 0.004), 0, poll_hmiA)); t += 1.0
    t = 0.7
    while t < DUR:
        events.append((t, 0, poll_hmiB)); t += 2.0
    t = 1.1
    while t < DUR:
        events.append((t, 0, poll_his(hisA, plcA)))
        events.append((t + 0.02, 0, poll_his(hisB, plcB))); t += 5.0

    # operator tweak of the dose setpoint (legit, from the HMI)
    def op_write(t):
        plcA.hr[40] = 125
        tid = hmiA.req(t, struct.pack("!BHH", 6, 40, 125))
        hmiA.resp(t + 0.004, tid, struct.pack("!BHH", 6, 40, 125))
    events.append((61.37, 1, op_write))

    # --- the rogue -------------------------------------------------------
    words40 = [int.from_bytes(note[i:i + 2].encode(), "big") for i in range(0, len(note), 2)]
    hp = DEC_HR42
    hp += " " * (len(hp) % 2)
    words42 = [int.from_bytes(hp[i:i + 2].encode(), "big") for i in range(0, len(hp), 2)]
    assert all(a != b for a, b in zip(words40, words40[1:])), "consecutive equal words"

    rogue = {}

    def rogue_open(t):
        rogue["c"] = Conn(pc, "10.18.0.66", "10.18.0.10", t)
    events.append((137.2, 2, rogue_open))

    def rogue_read(addr, n):
        def f(t):
            c = rogue["c"]
            tid = c.req(t, struct.pack("!BHH", 3, addr, n))
            c.resp(t + 0.0033, tid, bytes([3, 2 * n]) + regs(plcA, addr, n))
        return f

    def rogue_w6(addr, val, retrans=False, busy=False):
        def f(t):
            c = rogue["c"]
            tid = c.req(t, struct.pack("!BHH", 6, addr, val), retrans_after=0.212 if retrans else None)
            rt = t + (0.2141 if retrans else 0.0036)
            if busy:   # PLC busy -> exception 06, value NOT stored, rogue retries
                c.resp(rt, tid, bytes([0x86, 0x06]))
                tid2 = c.req(rt + 0.41, struct.pack("!BHH", 6, addr, val))
                plcA.hr[addr] = val
                c.resp(rt + 0.4137, tid2, struct.pack("!BHH", 6, addr, val))
            else:
                plcA.hr[addr] = val
                c.resp(rt, tid, struct.pack("!BHH", 6, addr, val))
        return f

    def rogue_bait(t):           # FC16 to an unmapped block -> exception 02
        c = rogue["c"]
        s = DEC_FC16.encode()
        s += b"\x00" * (2 - len(s) % 2)
        n = len(s) // 2
        tid = c.req(t, struct.pack("!BHHB", 16, 0x0F00, n, 2 * n) + s)
        c.resp(t + 0.0031, tid, bytes([0x90, 0x02]))

    t = 138.4
    events.append((t, 2, rogue_read(0, 10))); t += 0.9
    events.append((t, 2, rogue_read(40, 4))); t += 1.7
    retrans_idx = set(rng.sample(range(len(words40)), 3))
    busy_idx = rng.choice([i for i in range(len(words40)) if i not in retrans_idx])
    for i in range(max(len(words40), len(words42))):
        if i < len(words40):
            events.append((t, 2, rogue_w6(40, words40[i], i in retrans_idx, i == busy_idx)))
            t += rng.uniform(1.6, 2.4)
        if i < len(words42):
            events.append((t, 2, rogue_w6(42, words42[i])))
            t += rng.uniform(1.6, 2.4)
        if i == 6:
            events.append((t, 2, rogue_bait)); t += 1.3
    events.append((t, 2, rogue_w6(40, 125))); t += 1.1       # put things back
    events.append((t, 2, rogue_w6(42, 300))); t += 0.8
    events.append((t, 2, rogue_read(40, 4))); t += 0.6
    events.append((t, 2, lambda tt: rogue["c"].close(tt)))
    assert t < DUR - 10

    for t, _, fn in sorted(events, key=lambda e: (e[0], e[1])):
        fn(t)
    for c in (hmiA, hmiB, hisA, hisB):
        c.close(DUR + rng.uniform(0, 0.2))

    out = os.path.join(CH, "drive", "ps7_capture.pcap")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    pc.write(out)
    return out, len(pc.frames)


# =========================================================================
# Waypoint board content (layers 2 and 4)
# =========================================================================
def make_board(drive_url):
    layer2_plain = (f"Partha, the second ring is a shift log from Mayasabha Jal Kendra, "
                    f"pump station seven: {drive_url} "
                    f"The illusion lives in the dosing setpoint. Ignore what Shakuni writes.")
    layer2 = vigenere(layer2_plain, CONCH_KEY)
    assert vigenere(layer2, CONCH_KEY, decrypt=True) == layer2_plain

    pid = lambda: "%08x" % rng.getrandbits(32)
    places = [
        {"name": "Jyotisar", "aliases": ["Jyotisar Tirtha", "Jyotisar Kurukshetra"],
         "region": "Kurukshetra, Haryana", "comments": [
            ["karna_daanveer", "2025-09-02", "The banyan here is said to be a descendant of the one under which the Gita was spoken."],
            ["shakuni", "2025-09-14", f"Found it first. {DEC_JYO}"],
            ["duryodhan", "2025-09-20", base64.b64encode(DEC_DURY.encode()).decode()],
            [TRUSTED_1, "2025-10-01", "Blow my conch and the ring opens.  " + layer2],
            ["sanjaya", "2025-10-03", "Evening light and sound show tells the story of the eighteen days."],
        ]},
        {"name": "Brahma Sarovar", "aliases": ["Brahmsarovar"], "region": "Thanesar, Kurukshetra", "comments": [
            ["sanjaya", "2025-08-11", "Huge tank, busiest during the solar eclipse fair."],
            ["shakuni", "2025-09-15", DEC_BRAHMA],
            [TRUSTED_1, "2025-10-01", "Wrong water, Partha. Go where I spoke; the banyan still stands."],
        ]},
        {"name": "Sannihit Sarovar", "aliases": [], "region": "Kurukshetra", "comments": [
            ["sanjaya", "2025-07-30", "Smaller tank, a short ride from Brahma Sarovar."],
            ["duryodhan", "2025-09-21", "Nothing here. Or is there?"]]},
        {"name": "Sri Krishna Museum", "aliases": ["Krishna Museum Kurukshetra"], "region": "Kurukshetra", "comments": [
            ["sahadev", "2025-08-19", "Galleries on the Mahabharata; worth an hour."]]},
        {"name": "Kurukshetra Panorama and Science Centre", "aliases": ["Panorama Kurukshetra"],
         "region": "Kurukshetra", "comments": [
            ["nakul", "2025-08-21", "A 360 degree painting of the battlefield."],
            ["shakuni", "2025-09-16", "Try harder, the formation is not here."]]},
        {"name": "Bhishma Kund", "aliases": ["Narkatari", "Bhishma Kund Narkatari"], "region": "Kurukshetra", "comments": [
            ["sanjaya", "2025-08-02", "Said to be where Arjuna drew water for Bhishma on his bed of arrows."]]},
        {"name": "Hastinapur", "aliases": ["Hastinapura"], "region": "Meerut, Uttar Pradesh", "comments": [
            ["dhritarashtra", "2025-06-10", "The old capital. Very quiet now."],
            ["shakuni", "2025-09-17", "The dice were cast here first."]]},
        {"name": "Lakshagriha", "aliases": ["Barnawa", "Lakshagrah"], "region": "Baghpat, Uttar Pradesh", "comments": [
            ["bhim", "2025-07-07", "The house of lac. We left through the tunnel."]]},
        {"name": "Dwarkadhish Temple", "aliases": ["Dwarka", "Jagat Mandir"], "region": "Dwarka, Gujarat", "comments": [
            [TRUSTED_1, "2025-06-01", "Home. Nothing for you here, Partha."]]},
        {"name": "Purana Qila", "aliases": ["Purana Quila", "Old Fort Delhi"], "region": "New Delhi", "comments": [
            ["sanjaya", "2025-08-28", "Excavations here found grey ware sherds; some link the site to Indraprastha."],
            ["shakuni", "2025-09-18", f"Here it is, take it: {DEC_PQ_SHA}"],
            ["vidur", "2025-09-25", DEC_PQ_VID],
            ["karna_daanveer", "2025-09-29", f"I give freely: {DEC_PQ_KAR}"],
            [TRUSTED_2, "2025-10-05",
             "The Maya Sabha fooled Duryodhana, not you. The last ring is not on this board. "
             "Open this place on Google Maps, sign in, and search its reviews for the name "
             "of the formation you are trapped in. The truth of Indraprastha is written there."],
            ["duryodhan", "2025-10-06", "That pool was NOT there yesterday."],
        ]},
        {"name": "National Zoological Park", "aliases": ["Delhi Zoo"], "region": "New Delhi", "comments": [
            ["nakul", "2025-08-14", "Right next to the Old Fort walls."],
            ["shakuni", "2025-10-04", f"Close enough, take it: {DEC_ZOO}"]]},
        {"name": "Humayun's Tomb", "aliases": ["Humayun Tomb"], "region": "New Delhi", "comments": [
            ["sanjaya", "2025-08-15", "Mughal garden tomb, a short drive south-east."]]},
        {"name": "Bhimbetka", "aliases": ["Bhimbetka Rock Shelters"], "region": "Raisen, Madhya Pradesh", "comments": [
            ["bhim", "2025-07-01", "Named after me, apparently."]]},
    ]
    for p in places:
        p["id"] = pid()
        p["comments"] = [{"user": u, "date": d, "text": tx} for u, d, tx in p["comments"]]
    os.makedirs(HOSTDATA, exist_ok=True)
    with open(os.path.join(HOSTDATA, "waypoint.json"), "w", encoding="utf-8") as f:
        json.dump({"places": places}, f, indent=1, ensure_ascii=False)
    return layer2


# =========================================================================
# Ring 5 - the photo in the second drive (EXIF GPS -> Purana Qila)
# =========================================================================
def _dms(v):
    d = int(v); m = int((v - d) * 60); s = round(((v - d) * 60 - m) * 60, 2)
    return (float(d), float(m), float(s))


def make_photo():
    out = os.path.join(CH, "drive2", "mayasabha.jpg")
    if os.path.exists(out):      # already uploaded to Drive #2: keep it byte-identical
        return out + " (kept existing)"
    W, H = 1600, 1000
    img = Image.new("RGB", (W, H))
    d = ImageDraw.Draw(img)
    for y in range(H // 2):                                    # dusk sky
        k = y / (H / 2)
        d.line([(0, y), (W, y)], fill=(int(40 + 150 * k), int(30 + 80 * k), int(70 + 40 * k)))
    base, top = 520, 230
    d.rectangle([180, top, 1420, base], fill=(222, 200, 160))  # the hall
    d.rectangle([150, top - 30, 1450, top], fill=(190, 160, 110))
    for i in range(7):                                         # seven arches
        x0 = 230 + i * 170
        d.rectangle([x0, 330, x0 + 110, base], fill=(70, 45, 35))
        d.ellipse([x0, 275, x0 + 110, 385], fill=(70, 45, 35))
    for i in range(3):                                         # domes
        cx = 400 + i * 400
        d.ellipse([cx - 90, top - 150, cx + 90, top + 30], fill=(200, 175, 120))
        d.line([(cx, top - 150), (cx, top - 200)], fill=(170, 120, 40), width=6)
    d.rectangle([0, base, W, H], fill=(28, 60, 80))            # the pool
    hall = img.crop((0, 0, W, base)).transpose(Image.FLIP_TOP_BOTTOM)
    hall = Image.blend(hall, Image.new("RGB", hall.size, (28, 60, 80)), 0.55)
    img.paste(hall.crop((0, 0, W, H - base)), (0, base))       # reflection: floor or water?
    for _ in range(160):
        y = rng.randrange(base + 10, H)
        x = rng.randrange(W)
        d.line([(x, y), (x + rng.randrange(30, 120), y)], fill=(90, 130, 150), width=2)
    d.text((40, H - 70), "Maya Sabha - floor or water?", font=font(40), fill=(240, 230, 210))

    exif = Image.Exif()
    exif[0x010F] = "Mayasabha Jal Kendra"                      # Make
    exif[0x0110] = "PS7 shift camera"                          # Model
    exif[0x013B] = "Maya Danava"                               # Artist
    exif[0x010E] = "What the visitors say about this place is true. - Vidura"   # ImageDescription
    exif[0x0131] = "Indraprastha Imaging 1.0"                  # Software
    exif[0x0132] = "2025:10:05 18:42:07"                       # DateTime
    exif[0x9C9C] = DEC_PHOTO.encode("utf-16le") + b"\0\0"      # XPComment (decoy)
    gps = exif.get_ifd(0x8825)
    gps.update({0: b"\x02\x03\x00\x00", 1: "N", 2: _dms(PURANA_QILA[0]),
                3: "E", 4: _dms(PURANA_QILA[1]), 5: b"\x00", 6: 207.0})
    out = os.path.join(CH, "drive2", "mayasabha.jpg")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    img.save(out, "JPEG", quality=90, exif=exif)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--drive-url", default=DEFAULT_DRIVE)
    ap.add_argument("--drive2-url", default=DEFAULT_DRIVE2,
                    help="second Drive folder holding drive2/mayasabha.jpg (spelled out in the pcap)")
    a = ap.parse_args()
    if a.drive2_url == DEFAULT_DRIVE2:
        print("WARNING: --drive2-url not set; the pcap contains a placeholder link")

    png = make_image()
    note = a.drive2_url
    if len(note) % 2:
        note += " "
    pcap, nfr = make_pcap(note)
    photo = make_photo()
    make_board(a.drive_url)

    flags = {"chakravyuh": {"flag": FLAG, "decoys": DECOYS},
             "kestrel-point": {"flag": "GDG{l1ght_th3_w4y_thr0ugh_th3_l4y3rs}", "decoys": {}}}
    with open(os.path.join(HOSTDATA, "flags.json"), "w") as f:
        json.dump(flags, f, indent=1)
    print("image   :", png)
    print("pcap    :", pcap, f"({nfr} frames)")
    print("photo   :", photo)
    print("register string (HR40):", note)
    print("drive url in board:", a.drive_url)


if __name__ == "__main__":
    main()
