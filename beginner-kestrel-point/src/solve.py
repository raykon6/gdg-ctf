#!/usr/bin/env python3
"""
Reference solver for "Postcard from Kestrel Point".

Usage:  python solve.py ../dist/postcard.png [KEY]

Steps 1, 2 and 4 are automated. Step 3 (reading the key off the spectrogram)
is a visual step on purpose: this script saves spectrogram.png next to the
postcard and, if you do not pass KEY, stops there so you can read it.
"""
import base64, codecs, io, re, sys, wave, zipfile, os

import numpy as np

png_path = sys.argv[1] if len(sys.argv) > 1 else "../dist/postcard.png"
data = open(png_path, "rb").read()

# 1. PNG text chunks
pos, comment = 8, None
while pos < len(data):
    ln = int.from_bytes(data[pos:pos + 4], "big")
    typ = data[pos + 4:pos + 8]
    body = data[pos + 8:pos + 8 + ln]
    if typ == b"tEXt":
        k, v = body.split(b"\0", 1)
        print(f"[tEXt] {k.decode()}: {v.decode()}")
        if k == b"Comment":
            comment = v.decode()
    pos += 12 + ln
    if typ == b"IEND":
        break
iend_end = pos
msg = base64.b64decode(comment).decode()
print("[1] base64 ->", msg)
password = codecs.decode(msg.rsplit(": ", 1)[1], "rot13")
print("[1] rot13  ->", password)

# 2. trailing ZIP
tail = data[iend_end:]
print(f"[2] {len(tail)} bytes after IEND, starts with {tail[:4]!r}")
zf = zipfile.ZipFile(io.BytesIO(tail))
zf.setpassword(password.encode())
files = {n: zf.read(n) for n in zf.namelist()}
for n in files:
    print("    extracted", n, len(files[n]), "bytes")

# 3. spectrogram
wav = wave.open(io.BytesIO(files["storeroom/foghorn.wav"]))
sr = wav.getframerate()
x = np.frombuffer(wav.readframes(wav.getnframes()), "<i2").astype(float)
n, hop = 2048, 256
frames = np.lib.stride_tricks.sliding_window_view(x, n)[::hop] * np.hanning(n)
spec = np.abs(np.fft.rfft(frames, axis=1)).T          # [freq, time]
freqs = np.fft.rfftfreq(n, 1 / sr)
band = spec[(freqs > 2500) & (freqs < 9500)][::-1]     # high freq on top
img = 20 * np.log10(band + 1e-6)
img = np.clip((img - img.max() + 50) / 50, 0, 1)
try:
    from PIL import Image
    out = os.path.abspath("spectrogram.png")   # saved in the current folder
    Image.fromarray((img * 255).astype(np.uint8)).resize((img.shape[1], 300)).save(out)
    print("[3] spectrogram saved to", out)
except ImportError:
    pass

if len(sys.argv) < 3:
    print("[3] open spectrogram.png, read the key, then re-run with it as the 2nd argument")
    sys.exit(0)
key = sys.argv[2].encode()

# 4. XOR
hexline = re.findall(r"^[0-9a-f]{20,}$", files["storeroom/logbook.txt"].decode(), re.M)[0]
ct = bytes.fromhex(hexline)
print("[4] FLAG:", bytes(c ^ key[i % len(key)] for i, c in enumerate(ct)).decode())
