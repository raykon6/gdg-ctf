#!/usr/bin/env python3
"""
Build script for the GDG beginner challenge "Postcard from Kestrel Point".

Produces ../dist/postcard.png. All data here is made up: a drawn lighthouse,
a fictional keeper, a synthetic tone. No real people, places or services.

Layers (in the order a player peels them):
  1. PNG tEXt "Comment"  -> base64 -> sentence with a ROT13'd zip password
  2. ZIP appended after the PNG IEND chunk (ZipCrypto, so every unzip tool works)
  3. foghorn.wav         -> the XOR key is drawn as text in the spectrogram
  4. logbook.txt         -> hex string = flag XOR key (repeating)

Needs: Python 3.9+, numpy, Pillow.   Run:  python build.py
"""
import base64, codecs, io, os, struct, time, wave, zlib, random

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from PIL.PngImagePlugin import PngInfo

FLAG = "GDG{l1ght_th3_w4y_thr0ugh_th3_l4y3rs}"
XOR_KEY = "LAMP"
ZIP_PASSWORD = "keeper_of_the_light"

HERE = os.path.dirname(os.path.abspath(__file__))
DIST = os.path.join(HERE, "..", "dist")
rng = random.Random(1897)          # fixed seed -> reproducible build


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------
def font(size, bold=True):
    """Any TTF we can find, else Pillow's built-in scalable font."""
    names = ["arialbd.ttf", "DejaVuSans-Bold.ttf", "LiberationSans-Bold.ttf"] if bold \
        else ["arial.ttf", "DejaVuSans.ttf", "LiberationSans-Regular.ttf"]
    dirs = ["C:/Windows/Fonts", "/usr/share/fonts/truetype/dejavu",
            "/usr/share/fonts/truetype/liberation", "/Library/Fonts"]
    for d in dirs:
        for n in names:
            p = os.path.join(d, n)
            if os.path.exists(p):
                return ImageFont.truetype(p, size)
    return ImageFont.load_default(size=size)


# --------------------------------------------------------------------------
# layer 4: logbook.txt
# --------------------------------------------------------------------------
def make_logbook():
    enc = bytes(b ^ ord(XOR_KEY[i % len(XOR_KEY)]) for i, b in enumerate(FLAG.encode()))
    return (
        "KESTREL POINT LIGHT - KEEPER'S LOGBOOK (fictional)\n"
        "==================================================\n"
        "12 Oct  Wind NW 4. Lens cleaned. Lamp lit 17:42.\n"
        "13 Oct  Fog from 03:10. Horn sounded for 5 hrs.\n"
        "14 Oct  Supply boat late. Paraffin low.\n"
        "15 Oct  Fog again. I have put the last entry somewhere safe.\n"
        "        Only someone who can SEE the foghorn will read it.\n"
        "\n"
        "LAST ENTRY (scrambled):\n"
        f"{enc.hex()}\n"
    ).encode()


# --------------------------------------------------------------------------
# layer 3: foghorn.wav with text drawn in the spectrogram
# --------------------------------------------------------------------------
def make_wav():
    sr = 44100
    text = f"KEY = {XOR_KEY}"
    f = font(64)
    w = int(f.getlength(text)) + 40
    h = 90
    img = Image.new("L", (w, h), 0)
    ImageDraw.Draw(img).text((20, 8), text, fill=255, font=f)
    # downsample rows -> frequency bins, columns -> time slices
    rows, cols = 60, w
    img = img.resize((cols, rows), Image.LANCZOS)
    px = np.asarray(img, dtype=np.float64) / 255.0       # [rows, cols]

    dur_text = 6.0
    lead = 1.5                                            # foghorn-only intro
    n_text = int(sr * dur_text)
    n_total = int(sr * (dur_text + 2 * lead))
    t = np.arange(n_total) / sr

    # foghorn: low tone with harmonics, slow swell
    horn = np.zeros(n_total)
    for k, a in [(1, 1.0), (2, 0.5), (3, 0.25), (4, 0.12)]:
        horn += a * np.sin(2 * np.pi * 165 * k * t)
    env = np.clip(np.sin(np.pi * t / t[-1]), 0, 1) ** 0.5
    horn *= env * 0.35

    # hidden text: rows mapped to 3 kHz .. 9 kHz (top row = highest)
    sig = np.zeros(n_total)
    f_lo, f_hi = 3000.0, 9000.0
    col_pos = np.linspace(0, cols - 1, n_text)
    start = int(sr * lead)
    phases = np.array([rng.random() * 2 * np.pi for _ in range(rows)])
    tt = t[start:start + n_text]
    for r in range(rows):
        amp = np.interp(col_pos, np.arange(cols), px[r])
        if amp.max() < 0.05:
            continue
        freq = f_hi - (f_hi - f_lo) * r / (rows - 1)
        sig[start:start + n_text] += amp * np.sin(2 * np.pi * freq * tt + phases[r])
    sig = sig / (np.abs(sig).max() + 1e-9) * 0.30

    mix = horn + sig
    mix += np.random.default_rng(7).normal(0, 0.004, n_total)   # a little hiss
    mix = mix / np.abs(mix).max() * 0.9
    pcm = (mix * 32767).astype("<i2").tobytes()

    buf = io.BytesIO()
    with wave.open(buf, "wb") as wv:
        wv.setnchannels(1)
        wv.setsampwidth(2)
        wv.setframerate(sr)
        wv.writeframes(pcm)
    return buf.getvalue()


# --------------------------------------------------------------------------
# layer 2: ZipCrypto (traditional PKWARE) archive, pure Python
# --------------------------------------------------------------------------
def _crc_byte(k, c):
    return zlib.crc32(bytes([c]), k ^ 0xFFFFFFFF) ^ 0xFFFFFFFF


class ZipCrypto:
    def __init__(self, pw: bytes):
        self.k = [0x12345678, 0x23456789, 0x34567890]
        for c in pw:
            self._update(c)

    def _update(self, c):
        k0, k1, k2 = self.k
        k0 = _crc_byte(k0, c)
        k1 = ((k1 + (k0 & 0xFF)) * 134775813 + 1) & 0xFFFFFFFF
        k2 = _crc_byte(k2, k1 >> 24)
        self.k = [k0, k1, k2]

    def encrypt(self, data: bytes) -> bytes:
        out = bytearray()
        for p in data:
            tmp = (self.k[2] | 2) & 0xFFFF
            out.append(p ^ (((tmp * (tmp ^ 1)) >> 8) & 0xFF))
            self._update(p)
        return bytes(out)


def make_zip(files, password: bytes):
    """files: list of (name, bytes). Deflate + ZipCrypto."""
    dos_time = (14 << 11) | (2 << 5) | 0           # 14:02:00
    dos_date = ((2025 - 1980) << 9) | (10 << 5) | 15
    local, central = bytearray(), bytearray()
    for name, data in files:
        crc = zlib.crc32(data) & 0xFFFFFFFF
        co = zlib.compressobj(9, zlib.DEFLATED, -15)
        comp = co.compress(data) + co.flush()
        hdr = bytes(rng.randrange(256) for _ in range(11)) + bytes([crc >> 24])
        enc = ZipCrypto(password).encrypt(hdr + comp)
        nb = name.encode()
        offset = len(local)
        local += struct.pack("<IHHHHHIIIHH", 0x04034B50, 20, 0x0001, 8, dos_time,
                             dos_date, crc, len(enc), len(data), len(nb), 0) + nb + enc
        central += struct.pack("<IHHHHHHIIIHHHHHII", 0x02014B50, 20, 20, 0x0001, 8,
                               dos_time, dos_date, crc, len(enc), len(data), len(nb),
                               0, 0, 0, 0, 0x20, offset) + nb
    eocd = struct.pack("<IHHHHIIH", 0x06054B50, 0, 0, len(files), len(files),
                       len(central), len(local), 0)
    return bytes(local + central + eocd)


# --------------------------------------------------------------------------
# layer 1: the postcard PNG
# --------------------------------------------------------------------------
def make_png():
    W, H = 900, 560
    img = Image.new("RGB", (W, H))
    d = ImageDraw.Draw(img)
    for y in range(H):                                   # dusk sky
        k = y / H
        d.line([(0, y), (W, y)], fill=(int(30 + 200 * k), int(40 + 90 * k), int(90 + 60 * k)))
    for i in range(70):                                  # stars
        x, y = rng.randrange(W), rng.randrange(int(H * 0.45))
        d.point((x, y), fill=(255, 255, 230))
    d.polygon([(0, 380), (W, 360), (W, H), (0, H)], fill=(20, 45, 80))   # sea
    for i in range(40):
        y = rng.randrange(390, H)
        x = rng.randrange(W)
        d.line([(x, y), (x + rng.randrange(20, 60), y)], fill=(60, 100, 150), width=2)
    d.polygon([(470, 380), (720, 340), (900, 360), (900, 420), (520, 420)], fill=(40, 35, 30))  # rock
    # beam
    d.polygon([(610, 125), (0, 40), (0, 210)], fill=(255, 240, 170))
    # tower (striped)
    top, base = 130, 365
    for i, y in enumerate(range(top, base, 30)):
        frac0 = (y - top) / (base - top)
        frac1 = min(1, (y + 30 - top) / (base - top))
        w0, w1 = 22 + 20 * frac0, 22 + 20 * frac1
        d.polygon([(610 - w0, y), (610 + w0, y), (610 + w1, y + 30), (610 - w1, y + 30)],
                  fill=(200, 30, 40) if i % 2 == 0 else (240, 240, 235))
    d.rectangle([590, 100, 630, 130], fill=(255, 230, 120))      # lantern room
    d.polygon([(582, 100), (638, 100), (610, 78)], fill=(30, 30, 30))
    d.rectangle([580, 128, 640, 134], fill=(30, 30, 30))
    d.text((40, 470), "Greetings from Kestrel Point!", font=font(42), fill=(255, 250, 235))
    d.text((42, 520), "wish you were here - the keeper", font=font(20, False), fill=(220, 220, 220))

    secret = ("The storeroom is locked. The password, in the old keeper's cipher (rot13): "
              + codecs.encode(ZIP_PASSWORD, "rot13"))
    meta = PngInfo()
    meta.add_text("Title", "Greetings from Kestrel Point")
    meta.add_text("Author", "The Keeper")
    meta.add_text("Comment", base64.b64encode(secret.encode()).decode())
    meta.add_text("Software", "LighthouseCam 1.0")
    buf = io.BytesIO()
    img.save(buf, "PNG", pnginfo=meta, optimize=True)
    return buf.getvalue()


def main():
    os.makedirs(DIST, exist_ok=True)
    wav = make_wav()
    log = make_logbook()
    z = make_zip([("storeroom/foghorn.wav", wav), ("storeroom/logbook.txt", log)],
                 ZIP_PASSWORD.encode())
    png = make_png()
    out = os.path.join(DIST, "postcard.png")
    with open(out, "wb") as fh:
        fh.write(png + z)
    print(f"wrote {out}  ({len(png)} PNG bytes + {len(z)} ZIP bytes)")


if __name__ == "__main__":
    main()
