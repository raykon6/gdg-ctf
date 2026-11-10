# Chakravyuh

| | |
|---|---|
| Level | Advanced (experienced players) |
| Category | Steganography + OSINT + OT/ICS forensics |
| Points | 500 |
| Attempts | 10 (there are 12 fake flags, and each one says it's fake once you read it) |
| File | [`dist/chakravyuh.png`](dist/chakravyuh.png) |
| Online part | Waypoint board at `https://<your-ctf-host>/waypoint/` |
| Flag format | `GDG{...}` |

## Story

Dronacharya has laid the **Chakravyuh**. Abhimanyu learned how to break in while still
in his mother's womb, but never heard how to break out. Seven rings of illusion stand
between you and the exit.

Somewhere in the **Mayasabha Jal Kendra**, a water works that exists only in this CTF,
a rogue machine has been whispering to a PLC. Follow the charioteer, and trust only
those he tells you to trust.

Shakuni has scattered loaded dice everywhere. This challenge contains many fake
flags, and you have 10 attempts.

*The first ring opens with the name of this challenge.*

## Hint ladder

1. **Stego:** The image carries more than one message. Check each colour plane's
   lowest bit (zsteg, StegOnline, or CyberChef *Extract LSB*). Not everything shaped like
   a flag is one. The XOR key is the challenge name, exactly as written.
2. **OSINT:** The first coordinates give you a place name. Search that name on the
   Waypoint board, which only searches by name. The charioteer's conch has a name, and that name is a
   Vigenère key.
3. **OT:** In the capture only the stranger on the OT network matters, and only
   the writes the PLC accepted to the dosing setpoint. Drop TCP retransmissions and
   anything answered with an exception, then read each 16-bit register as two ASCII
   characters. The photo you find next remembers where it was taken (EXIF GPS), and the
   last word belongs to the visitors on Google Maps.

## You will need

A Google account, for the last step.

## Tools that help (all free)

zsteg / StegOnline / CyberChef · Google Maps or OpenStreetMap (reverse geocoding) ·
Wireshark or tshark · exiftool (photo GPS) ·
searching the web for Mahabharata lore and the Modbus function codes
