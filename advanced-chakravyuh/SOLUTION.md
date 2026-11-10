# Chakravyuh: solution (organisers only)

**Flag:** `GDG{4bh1m4nyu_f0und_th3_3x1t_v14_m0dbu5}`. It is in **vidura's comment on the Purana
Qila pin** of the Waypoint board. (It was first planned as a Google Maps review, but
Google removed the review, so the flag moved to the board; see [GOOGLE_REVIEW.md](GOOGLE_REVIEW.md).)

## The seven rings at a glance

```
chakravyuh.png
 ├─ tEXt Comment ............................ fake  GDG{dr0n4_s4ys_l00k_d33p3r}
 ├─ red   LSB -> base64 ..................... fake  GDG{wr0ng_ch4nn3l_p4rth4}
 └─ blue  LSB -> base64 -> XOR "Chakravyuh"
        -> 29°57'41"N 76°46'16"E + "read the Waypoint board" + "trust parth_sarathi"
              │ reverse geocode
              ▼
 RING 2  Jyotisar, Kurukshetra (Waypoint pin)
          ├─ shakuni ................................. fake  GDG{sh4kuni_s4ys_n1c3_try}
          ├─ duryodhan (base64) ...................... fake  GDG{duryodh4n_n3v3r_t3lls_th3_truth}
          └─ parth_sarathi -> Vigenère key PANCHAJANYA (Krishna's conch)
                 -> Drive #1 link + "the illusion lives in the dosing setpoint"
              ▼
 RING 3  Drive #1: ps7_capture.pcap (Modbus/TCP)
          ├─ FC16 to 0x0F00, rejected (exception 02) ... fake  GDG{th3_plc_r3j3ct3d_th1s_l13}
          ├─ HR42 writes ................................ fake  GDG{m4y4_s4bh4_1llus10n_n0t_r34l}
          └─ HR40 (dosing setpoint) accepted writes from 10.18.0.66
                 -> spells the Drive #2 link
              ▼
 RING 4  Drive #2: mayasabha.jpg
          ├─ EXIF XPComment ............................ fake  GDG{y0u_f3ll_1n_th3_m4y4_p00l}
          ├─ ImageDescription: "What the visitors say about this place is true. - Vidura"
          └─ EXIF GPS 28°36'34"N 77°14'39"E
              │ reverse geocode
              ▼
 RING 5  Purana Qila, New Delhi (Waypoint pin)
          ├─ shakuni / karna_daanveer / vidur (look-alike) ... three fakes
          └─ vidura ("the one who never lies") .............. REAL FLAG
```

The Mahabharata theme carries the logic. Krishna (Parthasarathi, Arjuna's charioteer)
shows the way. The Maya Sabha, the palace of illusions where Duryodhana mistook a floor
for a pool, is the plant full of illusions and the photo. Shakuni's loaded dice are the
fake flags, and Vidura, who never lies, gives the final direction.

**Fake flag design:** each fake reads as a trap once you look at it (`n1c3_try`,
`n0t_r34l`, `wr0ng_ch4nn3l`…). A player who finds one knows they took a wrong turn
without spending an attempt, and nobody can submit a fake believing it's real.

---

## Ring 1: the image

```bash
exiftool chakravyuh.png      # Comment: GDG{dr0n4_s4ys_l00k_d33p3r}  <- fake
zsteg chakravyuh.png
```

```
b1,r,lsb,xy  .. "R0RHe3dyMG5nX2NoNG5uM2xfcDRydGg0fQ=="  -> GDG{wr0ng_ch4nn3l_p4rth4}  <- fake
b1,b,lsb,xy  .. "PxRBKDogPSs0Pho9KUtIQQIREEgl..."         <- the real stream
```

On Windows without zsteg: StegOnline (Extract Data, B bit 0, row order, MSB first), or
the Python in `src/solve.py`.

CyberChef: **From Base64**, then **XOR** (key `Chakravyuh`, UTF8). The description says
*"the first ring opens with the name of this challenge"*.

```
|| CHAKRAVYUH : the first ring ||
The charioteer spoke where the old banyan still stands.
29°57'41"N 76°46'16"E
Maps lie. Read the Waypoint board on this CTF server (/waypoint).
Only parth_sarathi speaks the truth.
```

## Ring 2: Jyotisar and the conch

`29°57'41"N 76°46'16"E` = 29.96139, 76.77111. Google Maps puts this at **Jyotisar,
Kurukshetra**, where the Gita was spoken under a banyan tree.

Search `Jyotisar` on the Waypoint board. The board searches place names only, so the
reverse-geocoding step can't be skipped. Ignore Shakuni and Duryodhan, and take
**parth_sarathi**'s comment: *"Blow my conch and the ring opens."* followed by ciphertext.

The ciphertext keeps its spaces, digits, case and URL punctuation, so only the letters
are shifted. The shift changes from letter to letter, so it's Vigenère, not Caesar.
Krishna's conch is **Panchajanya** (Bhagavad Gita 1.15).

CyberChef: **Vigenère Decode**, key `PANCHAJANYA`:

```
Partha, the second ring is a shift log from Mayasabha Jal Kendra, pump station seven:
https://drive.google.com/drive/folders/1ARDF5uYA_ApdaJ5r0jmgiKf7OaKLDsod?usp=sharing
The illusion lives in the dosing setpoint. Ignore what Shakuni writes.
```

Trap: the Brahma Sarovar pin, about 6 km off, has a Shakuni fake and parth_sarathi
saying *"Wrong water, Partha."*

## Ring 3: the pcap (OT/ICS forensics)

Download `ps7_capture.pcap` from Drive #1. It holds about 5,100 frames over 7 minutes,
Modbus/TCP on 10.18.0.0/24.

| host | role |
|---|---|
| 10.18.0.10 | PLC-A, pump station 7 (dosing) |
| 10.18.0.11 | PLC-B, reservoir |
| 10.18.0.20 | HMI: polls PLC-A every 1 s (FC3 HR0-9, FC1 coils, FC3 HR40-43) |
| 10.18.0.30 | historian: FC4 every 5 s |
| **10.18.0.66** | **rogue**: TTL 128 (Windows) in a TTL-64 network, appears at t≈137 s |

1. **Spot the stranger:** *Statistics → Conversations → IPv4*.
2. **Who writes:** `modbus.func_code == 6 || modbus.func_code == 16`. The HMI makes one
   legitimate write (HR40 120→125 at t≈61 s). Everything else comes from .66.
3. **The dosing setpoint is HR40.** The HMI reads HR40-43 every second, and the board
   message pointed at it.
   ```
   ip.src==10.18.0.66 && modbus.func_code==6 && modbus.reference_num==40
   ```
4. **Drop the illusions:**
   - **3 TCP retransmissions** (`tcp.analysis.retransmission`). Wireshark hides their
     Modbus layer, but scapy, raw parsing or `strings` count them twice.
   - **1 write rejected with exception 06 (Server Device Busy)**, then retried with the
     same value. Count it once.
   - The final write (`125`) only restores the setpoint.
   - FC16 to `0x0F00` is rejected with exception 02. Its plain-ASCII payload is the
     `strings` bait: `GDG{th3_plc_r3j3ct3d_th1s_l13}`.
   - HR42 spells `GDG{m4y4_s4bh4_1llus10n_n0t_r34l}`, the honeypot register.
5. **Decode:** each 16-bit value is two ASCII characters, big-endian.
   ```bash
   tshark -r ps7_capture.pcap -Y "ip.src==10.18.0.66 && modbus.func_code==6 && modbus.reference_num==40" \
          -T fields -e modbus.regval_uint16
   ```
   ```python
   v = "<paste values, busy retry counted once, without the final 125>"
   print(b"".join(int(x).to_bytes(2, "big") for x in v.split()))
   ```
   This prints the **Drive #2 link**. A doubled pair like `drdr` means you counted
   the rejected write or a retransmission.

   Another route that also works: watch the HMI's FC3 reads of HR40 change over time and
   collapse repeated values. The generator guarantees no two consecutive words are equal.

## Ring 4: the photo

Drive #2 holds `mayasabha.jpg`, a palace and its reflection: *"Maya Sabha, floor or water?"*

```bash
exiftool mayasabha.jpg
```

```
Make              : Mayasabha Jal Kendra
Artist            : Maya Danava
Image Description : What the visitors say about this place is true. - Vidura
XP Comment        : GDG{y0u_f3ll_1n_th3_m4y4_p00l}          <- fake
GPS Position      : 28 deg 36' 34.00" N, 77 deg 14' 39.00" E
```

Players must **download** the original file from Drive to read its EXIF. A screenshot
of the preview won't carry the metadata.

## Ring 5: Purana Qila on the board

28.60944, 77.24417 is **Purana Qila**, New Delhi, the Old Fort traditionally identified
with Indraprastha, where the Maya Sabha stood. Searching `Purana` or `Old Fort` on
Waypoint gives:

| user | comment |
|---|---|
| shakuni | `GDG{l04d3d_d1c3_r0ll3d_4g41n}`: fake |
| vidur (look-alike) | `GDG{f4k3_v1dur_f4k3_fl4g}`: fake |
| karna_daanveer | `GDG{k4rn4_g1v3s_0nly_f4k3s}`: fake |
| **vidura** | "The Maya Sabha fooled Duryodhana, not you. Abhimanyu never learned the way out of the Chakravyuh; you have. Take it, Partha: `GDG{4bh1m4nyu_f0und_th3_3x1t_v14_m0dbu5}`" (**real**) |

Next door, the National Zoological Park pin has `GDG{t00_f4r_fr0m_1ndr4pr4sth4}`, a fake
for anyone who stopped at roughly the right coordinates.

Which one to trust? The photo's description, *"What the visitors say about this place is
true. - Vidura"*, names him. The look-alike `vidur` and the other three flags all read as
obvious traps. The real flag is **`GDG{4bh1m4nyu_f0und_th3_3x1t_v14_m0dbu5}`**.

## All fakes (12)

The checker in `hosting/server.py` recognises each one and replies *"one of Shakuni's
loaded dice"*.

| # | fake flag | where |
|---|---|---|
| 1 | `GDG{dr0n4_s4ys_l00k_d33p3r}` | PNG tEXt Comment |
| 2 | `GDG{wr0ng_ch4nn3l_p4rth4}` | red-channel LSB |
| 3 | `GDG{sh4kuni_s4ys_n1c3_try}` | Jyotisar / shakuni |
| 4 | `GDG{duryodh4n_n3v3r_t3lls_th3_truth}` | Jyotisar / duryodhan (base64) |
| 5 | `GDG{wr0ng_w4t3r_sh4kun1_w1ns}` | Brahma Sarovar / shakuni |
| 6 | `GDG{th3_plc_r3j3ct3d_th1s_l13}` | pcap, rejected FC16 (strings bait) |
| 7 | `GDG{m4y4_s4bh4_1llus10n_n0t_r34l}` | pcap, HR42 honeypot |
| 8 | `GDG{y0u_f3ll_1n_th3_m4y4_p00l}` | photo EXIF XPComment |
| 9 | `GDG{l04d3d_d1c3_r0ll3d_4g41n}` | Purana Qila / shakuni |
| 10 | `GDG{k4rn4_g1v3s_0nly_f4k3s}` | Purana Qila / karna_daanveer |
| 11 | `GDG{f4k3_v1dur_f4k3_fl4g}` | Purana Qila / vidur |
| 12 | `GDG{t00_f4r_fr0m_1ndr4pr4sth4}` | National Zoological Park / shakuni |

## Rebuild and verify

```bash
cd src
python build.py --drive-url  "<Drive #1 folder link>" \
                --drive2-url "<Drive #2 folder link>"
python solve.py --pcap ../drive/ps7_capture.pcap      # runs every ring and prints the flag
```

`build.py` keeps an existing `drive2/mayasabha.jpg` so the uploaded copy stays identical.
Delete it to draw a fresh one.

Current links: Drive #1 = folder `1ARDF5uYA_ApdaJ5r0jmgiKf7OaKLDsod`, Drive #2 = file
`1ARTaX9zKLlrA-CbLZOA8GXcbEwfXfw6j` (direct link to the photo).

After a rebuild, re-upload **`drive/ps7_capture.pcap` to Drive #1**, because the pcap
contains the Drive #2 link. Then put **`drive2/mayasabha.jpg` in Drive #2** and restart
the server so it loads the new board text.

## Safety notes

- The pcap is fully synthetic: private 10.18.0.0/24 addresses, locally administered
  MACs, a fictional plant. Nothing in it is runnable.
- The photo is drawn by the build script. Its GPS points to a public monument.
- No third-party platform holds any part of the challenge apart from the two Google Drive
  links. The planned Google Maps review was removed by Google (2026-11-11), and the flag now
  lives on the CTF's own Waypoint board.
