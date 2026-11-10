# Postcard from Kestrel Point: solution (organisers only)

**Flag:** `GDG{l1ght_th3_w4y_thr0ugh_th3_l4y3rs}`

Four layers: metadata → appended ZIP → spectrogram → XOR.

```
postcard.png
├─ tEXt "Comment" ── base64 ── "...password (rot13): xrrcre_bs_gur_yvtug"  → keeper_of_the_light
└─ bytes after IEND = ZIP (ZipCrypto, password above)
   ├─ storeroom/foghorn.wav  → spectrogram reads "KEY = LAMP"
   └─ storeroom/logbook.txt  → hex  ──XOR "LAMP"──► flag
```

## Step 1: metadata

```bash
exiftool postcard.png
```

```
Comment : VGhlIHN0b3Jlcm9vbSBpcyBsb2NrZWQuIFRoZSBwYXNzd29yZCwgaW4gdGhlIG9sZCBrZWVwZXIncyBjaXBoZXIgKHJvdDEzKTogeHJyY3JlX2JzX2d1cl95dnR1Zw==
Warning : [minor] Trailer data after PNG IEND chunk
```

Note the warning: it's the second clue.

```bash
echo 'VGhlIHN0b3...' | base64 -d
# The storeroom is locked. The password, in the old keeper's cipher (rot13): xrrcre_bs_gur_yvtug
echo xrrcre_bs_gur_yvtug | tr 'A-Za-z' 'N-ZA-Mn-za-m'
# keeper_of_the_light
```

(CyberChef: **From Base64**, then **ROT13** on the last word.)

## Step 2: the appended ZIP

Any one of these works:

```bash
binwalk -e postcard.png                      # carves the ZIP at offset 16729
7z x postcard.png -pkeeper_of_the_light      # 7-Zip finds the archive by itself
unzip -P keeper_of_the_light postcard.png    # warns "16729 extra bytes", then extracts
```

You get `storeroom/foghorn.wav` and `storeroom/logbook.txt`.

`logbook.txt` ends with:

```
LAST ENTRY (scrambled):
0b050a2b20702a38381e39387f1e3a64351e39383e713837241e39387f1e216435723f2331
```

It also says *"Only someone who can SEE the foghorn will read it."*

## Step 3: look at the sound

Open `foghorn.wav` in **Audacity**, then click the track name and choose **Spectrogram**
(or use Sonic Visualiser: Layer > Add Spectrogram). The low foghorn tone sits at the
bottom, and between about 3 and 9 kHz the text **`KEY = LAMP`** is drawn across seconds
1.5–7.5.

Command-line alternative:

```bash
ffmpeg -i foghorn.wav -lavfi showspectrumpic=s=1000x400 spec.png
```

## Step 4: XOR

CyberChef recipe: **From Hex**, then **XOR** (key `LAMP`, UTF8, Standard scheme).

```python
ct = bytes.fromhex("0b050a2b20702a38381e39387f1e3a64351e39383e713837241e39387f1e216435723f2331")
print(bytes(c ^ b"LAMP"[i % 4] for i, c in enumerate(ct)).decode())
# GDG{l1ght_th3_w4y_thr0ugh_th3_l4y3rs}
```

## Rebuild and verify

```bash
cd src
python build.py                                  # -> ../dist/postcard.png (deterministic)
python solve.py ../dist/postcard.png LAMP        # prints the flag
```

`build.py` writes the ZipCrypto archive in pure Python, so no 7-Zip is needed to
build it. It was checked against Python `zipfile`, 7-Zip, Info-ZIP `unzip` and exiftool.
