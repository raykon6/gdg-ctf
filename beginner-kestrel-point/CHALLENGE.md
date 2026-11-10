# Postcard from Kestrel Point

| | |
|---|---|
| Level | Beginner (advanced beginner) |
| Category | Forensics / Steganography |
| Points | 150 |
| File | [`dist/postcard.png`](dist/postcard.png) |
| Flag format | `GDG{...}` |

## Story

A postcard has arrived at the GDG club room from the keeper of Kestrel Point, a
lighthouse that exists only in this CTF. In his last letter he swore he had written
his final log entry *"where only a sharp eye and a sharp ear can find it"*.

The postcard is all we have. Find the keeper's last entry.

## Hint ladder

1. A picture is more than its pixels. Read the file's metadata, and check what comes
   after the image data ends.
2. The `Comment` field is Base64, and the password inside it is ROT13'd. The bytes
   after the PNG `IEND` chunk start with `PK`, so it's a ZIP. Carve it, or just open the
   PNG with 7-Zip.
3. Open `foghorn.wav` in Audacity (Spectrogram view) or Sonic Visualiser and look
   between 3 and 9 kHz. Then use CyberChef: **From Hex**, then **XOR** with that key (UTF8).

## Skills practised

PNG metadata · Base64 / ROT13 · file carving (data after IEND) · password-protected ZIP ·
audio spectrogram steganography · repeating-key XOR
