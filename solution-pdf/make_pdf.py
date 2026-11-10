#!/usr/bin/env python3
"""Builds ../GDG_CTF_Solutions.pdf from the captured command outputs (txt/) and screenshots (shots/)."""
import os, re
from xml.sax.saxutils import escape

from PIL import Image as PILImage
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch, mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (Image, KeepTogether, PageBreak, Paragraph, SimpleDocTemplate,
                                Spacer, Table, TableStyle, CondPageBreak)

HERE = os.path.dirname(os.path.abspath(__file__))
TXT, SHOTS = os.path.join(HERE, "txt"), os.path.join(HERE, "shots")
OUT = os.path.join(HERE, "..", "GDG_CTF_Solutions.pdf")

F = "C:/Windows/Fonts/"
pdfmetrics.registerFont(TTFont("Body", F + "arial.ttf"))
pdfmetrics.registerFont(TTFont("Body-B", F + "arialbd.ttf"))
pdfmetrics.registerFont(TTFont("Body-I", F + "ariali.ttf"))
pdfmetrics.registerFont(TTFont("Head", F + "georgiab.ttf"))
pdfmetrics.registerFont(TTFont("Mono", F + "consola.ttf"))
pdfmetrics.registerFont(TTFont("Mono-B", F + "consolab.ttf"))
pdfmetrics.registerFontFamily("Body", normal="Body", bold="Body-B", italic="Body-I", boldItalic="Body-B")

INK = colors.HexColor("#1f1a17")
MUTED = colors.HexColor("#6b625a")
ACC = colors.HexColor("#8b2e1a")       # maroon
ACC2 = colors.HexColor("#1f6f66")      # teal (beginner)
GOLD = colors.HexColor("#b07a1c")
CODEBG = colors.HexColor("#f5f2ec")
CODEBR = colors.HexColor("#ddd4c6")
FAKEBG = colors.HexColor("#fbeeea")
OKBG = colors.HexColor("#e9f4ee")

PAGE_W, PAGE_H = A4
MARGIN = 18 * mm
CONTENT_W = PAGE_W - 2 * MARGIN

S = {
    "title": ParagraphStyle("title", fontName="Head", fontSize=30, leading=36, textColor=INK, alignment=TA_CENTER),
    "sub": ParagraphStyle("sub", fontName="Body", fontSize=13, leading=18, textColor=MUTED, alignment=TA_CENTER),
    "part": ParagraphStyle("part", fontName="Head", fontSize=22, leading=27, textColor=ACC, spaceAfter=4),
    "h2": ParagraphStyle("h2", fontName="Head", fontSize=14.5, leading=19, textColor=INK, spaceBefore=12, spaceAfter=4),
    "h3": ParagraphStyle("h3", fontName="Body-B", fontSize=11, leading=15, textColor=ACC, spaceBefore=8, spaceAfter=3),
    "body": ParagraphStyle("body", fontName="Body", fontSize=10, leading=14.2, textColor=INK, spaceAfter=5),
    "small": ParagraphStyle("small", fontName="Body", fontSize=8.6, leading=11.5, textColor=MUTED),
    "cap": ParagraphStyle("cap", fontName="Body-I", fontSize=8.6, leading=11, textColor=MUTED, alignment=TA_CENTER, spaceAfter=8),
    "code": ParagraphStyle("code", fontName="Mono", fontSize=7.9, leading=10.2, textColor=INK),
    "cell": ParagraphStyle("cell", fontName="Body", fontSize=9, leading=12, textColor=INK),
    "cellmono": ParagraphStyle("cellmono", fontName="Mono", fontSize=8.4, leading=11, textColor=INK),
    "cellb": ParagraphStyle("cellb", fontName="Body-B", fontSize=9, leading=12, textColor=colors.white),
}

story = []
P = lambda t, s="body": story.append(Paragraph(t, S[s] if isinstance(s, str) else s))
SP = lambda h=6: story.append(Spacer(1, h))


# ------------------------------------------------------------------ helpers
def mono(t):
    return f'<font face="Mono" size="9">{escape(t)}</font>'


def clean(name, subs=()):
    raw = open(os.path.join(TXT, name + ".txt"), encoding="utf-8", errors="replace").read()
    lines = []
    for ln in raw.splitlines():
        if "Couldn't load plugin" in ln:
            continue
        if "\r" in ln or ".. b1," in ln:                      # zsteg progress noise
            parts = [p.strip() for p in re.split(r"\r|(?=b\d,[rgb]+,[lm]sb,xy)", ln) if "text:" in p]
            lines += parts if parts else [ln]
            continue
        lines.append(ln.rstrip())
    txt = "\n".join(lines).strip("\n")
    for a, b in subs:
        txt = txt.replace(a, b)
    return txt


def wrap(txt, width=108):
    out = []
    for ln in txt.split("\n"):
        while len(ln) > width:
            cut = ln.rfind(" ", 0, width)
            if cut < width * 0.6:          # no good space (base64, URLs): hard break
                cut = width
            out.append(ln[:cut])
            ln = "    " + ln[cut:].lstrip(" ")
        out.append(ln)
    return out


def code(txt, bg=CODEBG):
    """Terminal-style block: '$ cmd' lines in bold."""
    rows = []
    for ln in wrap(txt):
        e = escape(ln).replace(" ", "&nbsp;") or "&nbsp;"
        if ln.startswith("$ "):
            e = f'<font face="Mono-B" color="#8b2e1a">$</font><font face="Mono-B">{e[1:]}</font>'
        rows.append(e)
    para = Paragraph("<br/>".join(rows), S["code"])
    t = Table([[para]], colWidths=[CONTENT_W])
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), bg), ("BOX", (0, 0), (-1, -1), 0.6, CODEBR),
                           ("LEFTPADDING", (0, 0), (-1, -1), 7), ("RIGHTPADDING", (0, 0), (-1, -1), 7),
                           ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 6)]))
    story.append(t)
    SP(6)


def run(name, subs=()):
    code(clean(name, subs))


def shot(fname, caption, max_w=CONTENT_W, max_h=3.55 * inch):
    path = os.path.join(SHOTS, fname)
    w, h = PILImage.open(path).size
    sc = min(max_w / w, max_h / h)
    img = Image(path, width=w * sc, height=h * sc)
    frame = Table([[img]], colWidths=[w * sc + 2])
    frame.setStyle(TableStyle([("BOX", (0, 0), (-1, -1), 0.6, CODEBR), ("LEFTPADDING", (0, 0), (-1, -1), 1),
                               ("RIGHTPADDING", (0, 0), (-1, -1), 1), ("TOPPADDING", (0, 0), (-1, -1), 1),
                               ("BOTTOMPADDING", (0, 0), (-1, -1), 1)]))
    story.append(KeepTogether([frame, Spacer(1, 3), Paragraph(caption, S["cap"])]))


def note(text, bg=FAKEBG, border=colors.HexColor("#e2b8ab")):
    t = Table([[Paragraph(text, S["cell"])]], colWidths=[CONTENT_W])
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), bg), ("BOX", (0, 0), (-1, -1), 0.6, border),
                           ("LEFTPADDING", (0, 0), (-1, -1), 8), ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                           ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 6)]))
    story.append(t)
    SP(6)


def fake(t):
    note(f'<b>Fake flag:</b> {mono(t)}  : read it, it admits it is a trap. Do not submit.')


def good(t):
    note(t, bg=OKBG, border=colors.HexColor("#a9d2bb"))


def table(rows, widths, header=True, mono_cols=()):
    data = []
    for i, r in enumerate(rows):
        row = []
        for j, c in enumerate(r):
            st = "cellb" if (header and i == 0) else ("cellmono" if j in mono_cols else "cell")
            row.append(Paragraph(c if (header and i == 0) else c, S[st]))
        data.append(row)
    t = Table(data, colWidths=widths, repeatRows=1 if header else 0)
    style = [("GRID", (0, 0), (-1, -1), 0.4, CODEBR), ("VALIGN", (0, 0), (-1, -1), "TOP"),
             ("LEFTPADDING", (0, 0), (-1, -1), 5), ("RIGHTPADDING", (0, 0), (-1, -1), 5),
             ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 4)]
    if header:
        style += [("BACKGROUND", (0, 0), (-1, 0), ACC)]
    for i in range(1 if header else 0, len(data)):
        if i % 2 == 0:
            style.append(("BACKGROUND", (0, i), (-1, i), colors.HexColor("#faf8f4")))
    t.setStyle(TableStyle(style))
    story.append(t)
    SP(8)


def step(title, need=1.6 * inch):
    story.append(CondPageBreak(need))
    P(title, "h3")


def ring(title, need=2.4 * inch):
    story.append(CondPageBreak(need))
    P(title, "h2")


def zsteg_clean():
    raw = open(os.path.join(TXT, "a02_zsteg.txt"), encoding="utf-8", errors="replace").read()
    cmd = raw.splitlines()[0]
    hits = re.findall(r'(b1,[rb],lsb,xy)\s+\.\. (text: "[^"]*")', raw)
    return cmd + "\n" + "\n".join(f"{a:<20}.. {b}" for a, b in hits)


def conv_clean():
    raw = clean("a06_conv")
    cmd = raw.splitlines()[0]
    rows = [f"{'Conversation':<32}{'Frames':>8}{'Start (s)':>12}{'Duration (s)':>14}"]
    for ln in raw.splitlines():
        m = re.match(r"\s*(\S+)\s+<->\s+(\S+)\s+.*?(\d+)\s+[\d,.]+\s*\S*B?\S*\s+([\d.]+)\s+([\d.]+)\s*$", ln)
        if m:
            a, b, fr, st, du = m.groups()
            rows.append(f"{a + ' <-> ' + b:<32}{fr:>8}{float(st):>12.1f}{float(du):>14.1f}")
    return cmd + "\n# (tshark's byte columns dropped to fit the page; values unchanged)\n" + "\n".join(rows)


# ================================================================== COVER
SP(120)
P("GDG CTF", "title")
SP(6)
P("Solution Guide", ParagraphStyle("t2", parent=S["title"], fontSize=20, leading=26, textColor=ACC))
SP(18)
P("Postcard from Kestrel Point (Beginner)  &middot;  Chakravyuh (Advanced)", "sub")
SP(40)
table([["Challenge", "Level", "Category", "Flag"],
       ["Postcard from Kestrel Point", "Beginner", "Forensics / Stego", mono("GDG{l1ght_th3_w4y_thr0ugh_th3_l4y3rs}")],
       ["Chakravyuh", "Advanced", "Stego + OSINT + OT/ICS", mono("GDG{4bh1m4nyu_f0und_th3_3x1t_v14_m0dbu5}")]],
      [1.75 * inch, 0.8 * inch, 1.45 * inch, CONTENT_W - 4.0 * inch])
SP(10)
P("Every command in this guide was run against the real challenge files, and every output shown is the "
  "tool's actual output. Screenshots are from the live challenge: the Waypoint board, both Google Drive "
  "links, CyberChef, Google Maps and the final review.", "body")
SP(8)
P("<b>Tools used</b> (all free): exiftool, binwalk, unzip / 7-Zip, ffmpeg or Audacity, zsteg, tshark / Wireshark, "
  "Python 3, strings, CyberChef (gchq.github.io/CyberChef), Google Maps.", "body")
SP(8)
P("All systems in both challenges are fictional: a synthetic Modbus capture on private addresses, a drawn "
  "image and photo, and made-up board users. The only real places are two public heritage sites.", "small")
story.append(PageBreak())

# ================================================================== PART 1
P("Part 1 &nbsp;&middot;&nbsp; Postcard from Kestrel Point", "part")
P("<b>Level:</b> Beginner &nbsp;&nbsp; <b>File:</b> postcard.png &nbsp;&nbsp; "
  "<b>Flag:</b> " + mono("GDG{l1ght_th3_w4y_thr0ugh_th3_l4y3rs}"), "body")
P("<i>A postcard from the keeper of Kestrel Point, a lighthouse that exists only in this CTF. He hid his "
  "last log entry \"where only a sharp eye and a sharp ear can find it\".</i>", "body")
P("Chain at a glance", "h2")
code("postcard.png\n"
     " +- tEXt Comment --base64--> \"...password (rot13): xrrcre_bs_gur_yvtug\" --rot13--> keeper_of_the_light\n"
     " +- bytes after IEND = password-protected ZIP\n"
     "      +- storeroom/foghorn.wav   --spectrogram-->  \"KEY = LAMP\"\n"
     "      +- storeroom/logbook.txt   --hex, XOR LAMP-->  GDG{l1ght_th3_w4y_thr0ugh_th3_l4y3rs}")
shot("postcard.png", "Figure 1. The challenge file: looks like an ordinary postcard.", max_h=2.6 * inch)

step("Step 1: Read the metadata")
P("A picture is more than its pixels. exiftool shows a Base64-looking <b>Comment</b> and warns that there is "
  "data after the end of the PNG (the IEND chunk), which is the second clue.")
run("b01_exiftool")

step("Step 2: Decode the comment (Base64, then ROT13)")
run("b02_base64")
P("The password is in \"the old keeper's cipher\", ROT13 (each letter shifted by 13):")
run("b03_rot13")
good(f"<b>Password:</b> {mono('keeper_of_the_light')}")

step("Step 3: Find and open the hidden ZIP")
P("binwalk shows a ZIP archive starting at offset 16729, right after the PNG ends. unzip (or 7-Zip) can open "
  "the PNG directly; it warns about the extra bytes in front and extracts anyway.")
run("b04_binwalk")
run("b05_unzip")
run("b06_logbook")
P("The last entry is hex-encoded and scrambled. The note says only someone who can <b>see</b> the foghorn can read it.")

step("Step 4: Look at the sound (spectrogram)", need=3.4 * inch)
P("Open <b>foghorn.wav</b> in Audacity (track menu &rarr; Spectrogram) or Sonic Visualiser, or render it with ffmpeg. "
  "The low foghorn tone is at the bottom; between about 3 and 9 kHz the key is written as text.")
run("b07_spectro")
shot("spectrogram.png", "Figure 2. Spectrogram of foghorn.wav: the key KEY = LAMP is drawn between 3 and 9 kHz.", max_h=2.7 * inch)

step("Step 5: XOR the last entry with the key")
P("CyberChef recipe: <b>From Hex</b> &rarr; <b>XOR</b> (key LAMP, UTF8). The same in one line of Python:")
run("b08_xor")
shot("cc_lamp_xor.jpg", "Figure 3. CyberChef: From Hex, then XOR with LAMP, gives the flag.")
good(f"<b>Flag:</b> {mono('GDG{l1ght_th3_w4y_thr0ugh_th3_l4y3rs}')}")
story.append(PageBreak())

# ================================================================== PART 2
P("Part 2 &nbsp;&middot;&nbsp; Chakravyuh", "part")
P("<b>Level:</b> Advanced &nbsp;&nbsp; <b>File:</b> chakravyuh.png &nbsp;&nbsp; <b>Attempts:</b> 10 &nbsp;&nbsp; "
  "<b>Flag:</b> " + mono("GDG{4bh1m4nyu_f0und_th3_3x1t_v14_m0dbu5}"), "body")
P("<i>Dronacharya has laid the Chakravyuh. Abhimanyu knew the way in but not the way out. A rogue machine "
  "has been whispering to a PLC in the Mayasabha Jal Kendra, a water works that exists only in this CTF. "
  "Follow the charioteer, and trust only those he tells you to trust. Shakuni has scattered loaded dice "
  "(fake flags) everywhere. The first ring opens with the name of this challenge.</i>", "body")
P("Chain at a glance", "h2")
code("Ring 1  chakravyuh.png --blue LSB--> base64 --XOR 'Chakravyuh'--> 29 57'41\"N 76 46'16\"E\n"
     "Ring 2  Google Maps: Jyotisar --> Waypoint board --> parth_sarathi --Vigenere PANCHAJANYA--> Drive #1\n"
     "Ring 3  ps7_capture.pcap --rogue 10.18.0.66, accepted FC6 writes to HR40--> Drive #2 link\n"
     "Ring 4  mayasabha.jpg --EXIF GPS--> 28 36'34\"N 77 14'39\"E = Purana Qila\n"
     "Ring 5  Waypoint board: Purana Qila --> vidura: 'search the Google Maps reviews for the formation'\n"
     "Ring 6  Google Maps: Purana Qila reviews --search 'Chakravyuh'--> FLAG")
P("The theme carries the logic: Krishna (Parthasarathi, Arjuna's charioteer) shows the way; the Maya Sabha, "
  "the palace of illusions, is the OT plant and the photo; Shakuni's loaded dice are the fake flags; and "
  "Vidura, who never lies, gives the final direction. Each of the 12 fake flags says it is fake once you read it.", "body")

# ---------------- Ring 1
ring("Ring 1: the image", 4.6 * inch)
shot("chakravyuh.png", "Figure 4. chakravyuh.png: the seven-ring formation.", max_h=2.5 * inch)
step("Step 1: Metadata")
run("a01_exiftool")
fake("GDG{dr0n4_s4ys_l00k_d33p3r}")
step("Step 2: Check every colour plane's lowest bit (zsteg)")
P("zsteg finds text in two planes: the red channel and the blue channel (bit 0, row order).")
code(zsteg_clean())
run("a03_red")
fake("GDG{wr0ng_ch4nn3l_p4rth4}")
P("The blue stream decodes to bytes that aren't text, so it is encrypted. The full string:")
run("a04_blue")
step("Step 3: Decrypt with the challenge name")
P("\"The first ring opens with the name of this challenge\", so the key is <b>Chakravyuh</b>. CyberChef: "
  "<b>From Base64</b> &rarr; <b>XOR</b> (key Chakravyuh, UTF8), or in Python:")
blue = open(os.path.join(HERE, "blue_b64.txt")).read().strip()
run("a05_xor", subs=[(blue, "$BLUE")])
shot("cc_chak_xor.jpg", "Figure 5. CyberChef: From Base64, then XOR with Chakravyuh, reveals the first coordinates.")
good("<b>Result:</b> coordinates 29&deg;57'41\"N 76&deg;46'16\"E, an instruction to read the <b>Waypoint board</b>, "
     "and the one user to trust: <b>parth_sarathi</b>.")

# ---------------- Ring 2
ring("Ring 2: Jyotisar and the conch", 4.6 * inch)
step("Step 4: Reverse-geocode the coordinates", need=3.4 * inch)
P("Paste the coordinates into Google Maps. The pin lands on <b>Jyotisar Tirth, Kurukshetra</b>, where the "
  "Bhagavad Gita was spoken under a banyan tree (\"where the old banyan still stands\").")
shot("map_jyotisar.jpg", "Figure 6. Google Maps: 29\u00b057'41\"N 76\u00b046'16\"E is Jyotisar Tirth.")
step("Step 5: Read the Waypoint board", need=3.4 * inch)
P("Open <b>/waypoint</b> on the CTF server and search <b>Jyotisar</b>. The board only searches by place name, "
  "never by coordinates, so the reverse-geocoding step can't be skipped.")
shot("board_jyotisar.jpg", "Figure 7. Waypoint, Jyotisar pin. Only parth_sarathi's comment matters.")
fake("GDG{sh4kuni_s4ys_n1c3_try}")
P("duryodhan's base64 decodes to " + mono("GDG{duryodh4n_n3v3r_t3lls_th3_truth}") + ", also fake.")
step("Step 6: Identify the cipher and find the key")
P("In parth_sarathi's text, spaces, digits, capital letters and :// are untouched, and uvapb:// has exactly the "
  "shape of https://, but each letter is shifted by a different amount. That is a <b>Vigen&egrave;re</b> cipher. "
  "\"Blow my conch\": Krishna's conch is <b>Panchajanya</b> (Bhagavad Gita 1.15). CyberChef: "
  "<b>Vigen&egrave;re Decode</b>, key PANCHAJANYA.")
shot("cc_vigenere.jpg", "Figure 8. CyberChef Vigen\u00e8re Decode with PANCHAJANYA gives the Drive #1 link and the clue 'the dosing setpoint'.")
good("<b>Result:</b> Drive #1 link, plus two clues: <i>\"The illusion lives in the dosing setpoint\"</i> and "
     "<i>\"Ignore what Shakuni writes\"</i>.")
note("<b>Trap:</b> the nearby Brahma Sarovar pin has " + mono("GDG{wr0ng_w4t3r_sh4kun1_w1ns}") +
     " and parth_sarathi saying \"Wrong water, Partha\".")

# ---------------- Ring 3
ring("Ring 3: the OT capture", 3.4 * inch)
shot("drive1.jpg", "Figure 9. Drive #1: ps7_capture.pcap (413 KB).", max_h=2.2 * inch)
step("Step 7: Find the stranger on the OT network")
P("Statistics &rarr; Conversations &rarr; IPv4 in Wireshark (or tshark below). Four hosts poll the PLCs for the "
  "whole 7 minutes; <b>10.18.0.66</b> appears only at t = 137 s. Its TTL of 128 (Windows) stands out in a "
  "network where everything else is 64.")
code(conv_clean())
run("a07_ttl")
step("Step 8: Who writes to the PLC?")
P("Function code 6 = Write Single Register, 16 = Write Multiple Registers. The HMI (10.18.0.20) makes one "
  "legitimate write. The rogue writes to holding registers <b>40</b> and <b>42</b>, and makes one FC16 write "
  "to 3840 (0x0F00). Lines from 10.18.0.10 are the PLC's replies.")
run("a08_writers")
step("Step 9: Find the illusions")
P("Two writes were refused. Exception code 2 (Illegal Data Address) rejected the FC16 write. Exception code 6 "
  "(Server Device Busy) rejected one FC6 write, which the rogue then retried. There are also three TCP "
  "retransmissions of rogue requests.")
run("a09_exceptions")
run("a10_retrans")
P("The refused FC16 write is plain ASCII, so it is what a quick <b>strings</b> search finds:")
run("a11_strings")
fake("GDG{th3_plc_r3j3ct3d_th1s_l13}")
step("Step 10: Take only the writes the PLC accepted, on the dosing setpoint (HR40)")
P("The cleanest filter is the <b>PLC's own echo replies</b> to the rogue. A successful FC6 reply repeats the "
  "register and value, so rejected writes (exceptions) and retransmissions drop out automatically. "
  "The last value, 125, only restores the original setpoint.")
run("a12_accepted")
P("Each 16-bit register holds two ASCII characters (big-endian). Drop the final 125 and convert:")
run("a13_decode40")
good("<b>Result:</b> the Drive #2 link: " + mono("https://drive.google.com/file/d/1ARTaX9zKLlrA-CbLZOA8GXcbEwfXfw6j/view"))
P("What goes wrong if you take the rogue's <i>requests</i> instead of the PLC's accepted replies: the "
  "busy-rejected write is counted twice, and the link breaks (" + mono("...lrA-CbCbLZOA8...") + "):", "body")
code(clean("a15_naive"), bg=FAKEBG)
P("The other register, HR42, is the honeypot:")
run("a14_decode42")
fake("GDG{m4y4_s4bh4_1llus10n_n0t_r34l}")

# ---------------- Ring 4
ring("Ring 4: the photo", 5.0 * inch)
step("Step 11: Download the photo from Drive #2", need=3.4 * inch)
shot("drive2.jpg", "Figure 10. Drive #2: mayasabha.jpg, the Maya Sabha, 'floor or water?'. Download the original file; a screenshot loses the metadata.")
step("Step 12: Read its EXIF metadata")
run("a16_photo")
fake("GDG{y0u_f3ll_1n_th3_m4y4_p00l}")
P("The description points to the visitors' words. The GPS tag gives the second location.")
step("Step 13: Reverse-geocode the GPS position", need=3.4 * inch)
shot("map_purana.jpg", "Figure 11. Google Maps: 28\u00b036'34\"N 77\u00b014'39\"E is Purana Qila, New Delhi, the traditional site of Indraprastha.")

# ---------------- Ring 5 + 6
ring("Ring 5: the last board pin", 3.2 * inch)
step("Step 14: Search Purana Qila on the Waypoint board", need=3.4 * inch)
shot("board_search.jpg", "Figure 12. The board searches by place name only.", max_h=1.9 * inch)
shot("board_purana.jpg", "Figure 13. Purana Qila pin: three fakes, plus vidura's direction to the Google Maps reviews.")
P("shakuni " + mono("GDG{l04d3d_d1c3_r0ll3d_4g41n}") + ", karna_daanveer " + mono("GDG{k4rn4_g1v3s_0nly_f4k3s}") +
  " and the look-alike <b>vidur</b> " + mono("GDG{f4k3_v1dur_f4k3_fl4g}") + " are all fake. The real <b>vidura</b> says: "
  "<i>\"The last ring is not on this board. Open this place on Google Maps, sign in, and search its reviews for "
  "the name of the formation you are trapped in.\"</i>")

ring("Ring 6: the Google Maps review", 4.6 * inch)
step("Step 15: Search the reviews for the formation's name", need=3.4 * inch)
P("Open <b>Purana Qila</b> on Google Maps and sign in to Google (signed out, Maps shows only a few reviews and "
  "blocks search). Go to <b>Reviews &rarr; Search reviews</b> and type <b>Chakravyuh</b>.")
shot("google_review.png", "Figure 14. The review on Purana Qila holding the real flag.", max_h=2.6 * inch)
step("Step 16: Submit", need=3.4 * inch)
shot("portal_correct.jpg", "Figure 15. The CTF portal accepts the flag.", max_h=2.3 * inch)
good(f"<b>Flag:</b> {mono('GDG{4bh1m4nyu_f0und_th3_3x1t_v14_m0dbu5}')}")

# ---------------- Appendix
story.append(PageBreak())
P("Appendix: all fake flags in Chakravyuh", "part")
P("The portal's flag checker recognises each of these and replies \"That is one of Shakuni's loaded dice\" (it still "
  "costs an attempt).", "body")
fakes = [("GDG{dr0n4_s4ys_l00k_d33p3r}", "PNG tEXt Comment"),
         ("GDG{wr0ng_ch4nn3l_p4rth4}", "Red-channel LSB"),
         ("GDG{sh4kuni_s4ys_n1c3_try}", "Waypoint, Jyotisar (shakuni)"),
         ("GDG{duryodh4n_n3v3r_t3lls_th3_truth}", "Waypoint, Jyotisar (duryodhan, base64)"),
         ("GDG{wr0ng_w4t3r_sh4kun1_w1ns}", "Waypoint, Brahma Sarovar (shakuni)"),
         ("GDG{th3_plc_r3j3ct3d_th1s_l13}", "pcap: rejected FC16 write (strings bait)"),
         ("GDG{m4y4_s4bh4_1llus10n_n0t_r34l}", "pcap: honeypot holding register 42"),
         ("GDG{y0u_f3ll_1n_th3_m4y4_p00l}", "Photo EXIF XP Comment"),
         ("GDG{l04d3d_d1c3_r0ll3d_4g41n}", "Waypoint, Purana Qila (shakuni)"),
         ("GDG{k4rn4_g1v3s_0nly_f4k3s}", "Waypoint, Purana Qila (karna_daanveer)"),
         ("GDG{f4k3_v1dur_f4k3_fl4g}", "Waypoint, Purana Qila (vidur, look-alike user)"),
         ("GDG{t00_f4r_fr0m_1ndr4pr4sth4}", "Waypoint, National Zoological Park (shakuni)")]
table([["#", "Fake flag", "Where"]] + [[str(i + 1), escape(f), w] for i, (f, w) in enumerate(fakes)],
      [0.35 * inch, 3.1 * inch, CONTENT_W - 3.45 * inch], mono_cols=(1,))

P("Key values", "h2")
table([["What", "Value"],
       ["Ring 1 XOR key", mono("Chakravyuh") + " (the challenge name)"],
       ["First coordinates", "29&deg;57'41\"N 76&deg;46'16\"E = Jyotisar, Kurukshetra"],
       ["Vigen&egrave;re key", mono("PANCHAJANYA") + " (Krishna's conch)"],
       ["Rogue host", "10.18.0.66 (TTL 128)"],
       ["Data register", "Holding register 40 (dosing setpoint), FC6, accepted writes only"],
       ["Traps in the pcap", "3 TCP retransmissions, 1 busy exception (code 6), 1 rejected FC16 (code 2), HR42 honeypot, final restore write 125"],
       ["Second coordinates", "28&deg;36'34\"N 77&deg;14'39\"E = Purana Qila, New Delhi (photo EXIF GPS)"],
       ["Final search", "Google Maps, Purana Qila, Reviews, search " + mono("Chakravyuh")]],
      [1.6 * inch, CONTENT_W - 1.6 * inch])


# ------------------------------------------------------------------ page decoration
def on_page(c, doc):
    if doc.page == 1:
        c.setFillColor(ACC)
        c.rect(0, PAGE_H - 10 * mm, PAGE_W, 10 * mm, stroke=0, fill=1)
        c.setFillColor(GOLD)
        c.rect(0, PAGE_H - 11.2 * mm, PAGE_W, 1.2 * mm, stroke=0, fill=1)
        return
    c.setStrokeColor(CODEBR)
    c.setLineWidth(0.6)
    c.line(MARGIN, PAGE_H - 12 * mm, PAGE_W - MARGIN, PAGE_H - 12 * mm)
    c.setFont("Body", 8)
    c.setFillColor(MUTED)
    c.drawString(MARGIN, PAGE_H - 10 * mm, "GDG CTF  \u00b7  Solution Guide")
    c.drawRightString(PAGE_W - MARGIN, PAGE_H - 10 * mm, "Kestrel Point  \u00b7  Chakravyuh")
    c.drawCentredString(PAGE_W / 2, 10 * mm, str(doc.page))


doc = SimpleDocTemplate(OUT, pagesize=A4, leftMargin=MARGIN, rightMargin=MARGIN, topMargin=17 * mm,
                        bottomMargin=16 * mm, title="GDG CTF - Solution Guide",
                        author="GDGoC NFSU Cybersec", subject="Solutions: Kestrel Point and Chakravyuh")
doc.build(story, onFirstPage=on_page, onLaterPages=on_page)
print("wrote", os.path.abspath(OUT))
