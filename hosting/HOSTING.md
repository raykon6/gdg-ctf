# Hosting the GDG CTF

Everything ships with one small Python server (`server.py`, standard library only).
It serves three things:

| path | what | needed by |
|---|---|---|
| `/` | CTF portal: both challenges, downloads, hints, flag checker (with decoy detection, 10-attempt limit on Chakravyuh, rate limit) | optional if you use CTFd |
| `/waypoint/` | "Waypoint" traveller pin-board: the OSINT comment pages | **Chakravyuh** |
| `/drive/<token>/` | stand-in shared drive holding `ps7_capture.pcap` | Chakravyuh, unless you use Google Drive |
| `/healthz` | liveness probe | Docker |

Kestrel Point is file-only, so any platform that hosts a download works for it.

---

## 0. Build the files (once, or when you change the drive link)

```bash
pip install numpy pillow
cd beginner-kestrel-point/src && python build.py && cd ../..
cd advanced-chakravyuh/src   && python build.py --drive-url "<DRIVE-LINK>" && cd ../..
```

`<DRIVE-LINK>` is where players will download the pcap. Pick one:

- **Bundled drive page (simplest):** `https://<your-host>/drive/1Mz7vYhAbhimanyu-PS7rk/`
  If you change the token part, set the same value in `DRIVE_TOKEN` when you run the server.
- **Real Google Drive (fits the story better):**
  1. Make a folder (for example `PS7-shift-logs`) and upload `advanced-chakravyuh/drive/ps7_capture.pcap`.
  2. Share > General access > **Anyone with the link: Viewer**.
  3. Copy the folder link and pass it as `--drive-url`.
  4. Test the link in a private window while signed out.

Only `hosting/data/waypoint.json` changes with the drive link. The image and pcap are
deterministic, so players' files stay valid across rebuilds.

Check the build before going live:

```bash
cd advanced-chakravyuh/src && python solve.py --pcap ../drive/ps7_capture.pcap
cd ../../beginner-kestrel-point/src && python solve.py ../dist/postcard.png LAMP
```

---

## Live deployment: Render (free), the permanent link

**https://gdg-ctf.onrender.com** (deployed from the private repo `raykon6/gdg-ctf`, branch `main`).

How it was set up:
1. Push this folder to a **private** GitHub repo.
2. Go to render.com, sign in with GitHub, then **Blueprints → New Blueprint Instance**, pick the repo, name it `gdg-ctf`, and click **Deploy Blueprint**.
   Render reads `render.yaml`: Docker, free plan, Singapore, health check `/healthz`.
3. Every `git push` to `main` redeploys automatically (about 1 minute).

What to know about it:
- **Free plan sleep:** after about 15 minutes with no visitors the service spins down, and the next visit waits up to about 50 s. Open the link yourself before sharing it or starting the event.
- **Attempt counters** live in memory, so they reset whenever the service restarts or sleeps.
- **Not deployed:** `.dockerignore` keeps solutions, `src/`, the solution PDF and CTFd configs out of the image. On 2026-11-10 I checked that solution, flag-file and `.git` paths all return 404 and that the real flag appears nowhere on the portal or board.
- **Player IPs:** behind Render's proxy the server uses the **last** `X-Forwarded-For` entry (the one the proxy adds), so a forged header can't reset the attempt limit.

## Option A: everything in one container (recommended for a club event)

```bash
# from the gdg-ctf folder
docker compose -f hosting/docker-compose.yml up -d --build
curl http://localhost:8080/healthz        # -> ok
```

Open `http://<server-ip>:8080/`. The container runs as a non-root user with a read-only
filesystem and copies in only the player files, the pcap and `hosting/data`. Solution
files and build scripts are not in the image.

**Without Docker:**

```bash
python hosting/server.py                  # Python 3.9+, no packages needed
PORT=9000 python hosting/server.py        # another port
```

### Quick public link from a laptop (Cloudflare quick tunnel), the setup used for the demo

No account, no Docker, no open ports. The link lives only while the laptop, the server
and the tunnel are running, and it changes every time the tunnel restarts.

1. Get `cloudflared` from Cloudflare's GitHub releases
   (`cloudflared-windows-amd64.exe`, saved here as `C:\Users\raykon\bin\cloudflared.exe`).
2. Terminal 1, the server on localhost only, so only the tunnel can reach it:
   ```powershell
   $env:HOST = '127.0.0.1'; python gdg-ctf\hosting\server.py
   ```
3. Terminal 2, the tunnel. Use `--protocol http2`: on our mobile/Jio connection the default
   QUIC (UDP) dropped about a third of requests with Cloudflare 522 errors, and HTTP/2
   delivered 40/40.
   ```powershell
   C:\Users\raykon\bin\cloudflared.exe tunnel --no-autoupdate --protocol http2 --url http://127.0.0.1:8080
   ```
4. Copy the `https://<random-words>.trycloudflare.com` URL it prints. That is the CTF link.

Behind the tunnel the server identifies players by Cloudflare's `CF-Connecting-IP` header.
Players can't fake it, so a forged `X-Forwarded-For` doesn't reset the 10-attempt limit
(tested). Players on the same Wi-Fi/NAT share one public IP and so share the counter.
That's another reason to use CTFd (Option B) for a large in-person event.

Account-less quick tunnels have no uptime guarantee. For a fixed URL, use a named tunnel
on a Cloudflare account, or a VPS.

### HTTPS and a domain

Put a reverse proxy in front of it. With Caddy, a two-line `Caddyfile` gets automatic TLS:

```
ctf.your-club.example {
    reverse_proxy 127.0.0.1:8080
}
```

The server reads `X-Forwarded-For` for its per-player attempt counter, so keep the proxy
on the same machine and don't expose port 8080 publicly.

### Sizing

A single process is plenty for a club CTF (pages are a few KB; the largest download is
the 786 KB postcard). Any 1 vCPU / 512 MB VM works.

---

## Option B: CTFd for scoring, this server for the OSINT pages

Use this if your chapter already runs CTFd (accounts, teams, scoreboard).

1. Run CTFd (official image):
   ```bash
   git clone https://github.com/CTFd/CTFd && cd CTFd && docker compose up -d
   ```
2. Install the challenges with ctfcli:
   ```bash
   pip install ctfcli
   cd gdg-ctf/hosting/ctfd && ctf init        # point it at your CTFd URL + admin token
   mkdir -p kestrel-point/dist chakravyuh/dist
   cp ../../beginner-kestrel-point/dist/postcard.png kestrel-point/dist/
   cp ../../advanced-chakravyuh/dist/chakravyuh.png  chakravyuh/dist/
   ctf challenge install kestrel-point
   ctf challenge install chakravyuh
   ```
   Then edit the Chakravyuh description in CTFd and replace `https://YOUR-HOST/waypoint/`
   with your real board URL.
3. Run the board and drive with the portal turned off:
   ```bash
   docker compose -f hosting/docker-compose.yml up -d --build   # with ENABLE_PORTAL: "0"
   ```
   With the portal off, `/`, `/files/` and `/submit` return 404, so flags are only
   checked in CTFd.

CTFd only knows the real flag, so a decoy just shows as "incorrect". The `attempts: 10`
in `challenge.yml` is what stops players guessing through all 11 decoys.

---

## Option C: Google My Maps instead of Waypoint

Only do this if you specifically want a Google-branded map. You'd create your own
My Maps map with your own pins and descriptions, not reviews on real business listings.
Be aware that a shared My Maps map shows every pin at once, which removes the
"reverse-geocode, then search by name" step and the decoy pins lose their purpose. The
bundled Waypoint board is the intended design.

---

## Pre-event checklist

- [ ] `build.py` run with the final `--drive-url` and `--drive2-url`
- [ ] Drive #1 holds the **latest** `ps7_capture.pcap`, Drive #2 holds `mayasabha.jpg`, both links open signed out, sharing set to **Viewer**
- [ ] The Purana Qila Google Maps review is found by searching `Chakravyuh` from a Google account **other than the one that posted it** ([GOOGLE_REVIEW.md](../advanced-chakravyuh/GOOGLE_REVIEW.md))
- [ ] Both `solve.py` runs print the flags
- [ ] `/waypoint/search?q=Jyotisar` and `?q=Purana` return the pins on the public URL
- [ ] Submitting a decoy shows the decoy message, and the real flag shows "Correct"
- [ ] `SOLUTION.md` files and `src/` folders are **not** published
- [ ] Restarting the server resets attempt counters (they are in memory). Restart before the event, not during it.

## Troubleshooting

| symptom | fix |
|---|---|
| `missing .../ps7_capture.pcap: run the build scripts first` | run both `build.py` scripts |
| drive page is 404 | `DRIVE_TOKEN` doesn't match the token inside `--drive-url` |
| board still shows the old drive link | rebuild with the new `--drive-url`, then restart or rebuild the container |
| every player shares one attempt counter | the proxy isn't sending `X-Forwarded-For` |
