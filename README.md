# LS4 Operator GUI

Web dashboard for LS4 observing at La Silla. Operators log in from a browser to run pre-flight checks, control the dome and PDU, manage telescope services, preview mosaics, and follow the nightly workflow — without relying on VNC for every step.

Runs on the **mountain machine** as the `observer` user. Not intended for public internet access.


## Quick start (mountain)

```bash
cd ~/ls4_gui
git pull
cp .env.example .env          # first time only — then edit SECRET_KEY and PASSWORD
~/observer_venv/bin/pip install -r requirements.txt
./run.sh
```

Open in a browser (see [Access](#access-from-a-browser) below).

**Stop:** `Ctrl+C` in the terminal where Flask is running.


## Simulate vs live

| `LS4_GUI_SIMULATE` | Behavior |
|--------------------|----------|
| `true` (default)   | Safe testing — no real hardware commands |
| `false`            | Live — runs `start_questctl`, `opendome_raw`, PDU, `mos`, etc. |

Keep `true` until paths are verified and you are ready for real operations.


## Access from a browser

Flask listens on port **8080** on the mountain network.

### On the mountain (RealVNC)

Chrome inside VNC:

```
http://192.168.1.73:8080
```

(or `http://127.0.0.1:8080` on the same machine)

### From your personal laptop

1. Connect **Cisco Secure Client** (La Silla VPN).
2. Start Flask on the mountain (see Quick start).
3. On your laptop, open a terminal:

   ```bash
   ssh -L 8080:192.168.1.73:8080 -p 5900 ls4@134.171.80.150
   ```

   Use the **`ls4` SSH password** (not the Flask GUI password). Leave this window open.

4. Chrome on your laptop:

   ```
   http://127.0.0.1:8080
   ```

5. Log in with the **GUI password** from your `.env`.

**Why `127.0.0.1`?** Your laptop cannot reach the internal address `192.168.1.73` directly. The SSH tunnel forwards your laptop’s port 8080 to Flask on the mountain.

If the tunnel fails, try:

```bash
ssh -L 8080:127.0.0.1:8080 -p 5900 ls4@134.171.80.150
```


## Configuration

Copy `.env.example` to `.env`. Minimum required changes:

```bash
LS4_GUI_SECRET_KEY=<long random string>
LS4_GUI_PASSWORD=<strong password>
```

All other variables have **mountain defaults** in `config.py`. Override in `.env` only if your paths differ.

Run `bash scripts/discover_mountain_paths.sh` (read-only) to inspect paths and get suggested `.env` lines.

### Important variables

| Variable | Purpose |
|----------|---------|
| `LS4_GUI_SIMULATE` | `true` = mock hardware; `false` = live |
| `LS4_OBSERVER_HOME` | Observer account home (`/home/observer`) |
| `LS4_KENNETH_DIR` | ls4 tools (`/home/ls4/kenneth`) |
| `LS4_DATA_DIR` | Exposure data (`/data/observer`) |
| `LS4_FLUX_METER_SNAPSHOT_DIR` | Flux cam images (`*_cam3.jpg`) |
| `LS4_GUI_PYTHON` | Python with Flask installed |

See `.env.example` for the full list.


## How to run

### Development / testing

```bash
./run.sh
```

Uses Flask’s built-in server. Fine for short tests. You may see a “development server” warning — that is expected.

Optional debug mode (auto-reload, tracebacks in browser):

```bash
LS4_GUI_DEBUG=true ./run.sh
```

### Longer sessions / observing nights

```bash
./run_production.sh
```

Uses **gunicorn** (no development-server warning, more stable). For always-on use, wrap this in **systemd** (not included yet).


## Mosaic prefixes

Exposures live under `/data/observer/` in dated folders (e.g. `20260625/`).

Find a prefix:

```bash
ls -lt /data/observer/20260625 | head
```

If you see `20260625010625sC001.fits`, enter **`20260625010625sC`** in the GUI.

- **Simulate mode:** generates a placeholder SVG preview.
- **Live mode:** runs `mos <prefix>` or reuses an existing `mos_*.fits` in that night’s folder.


## Project layout

```
ls4_gui/
├── app.py                 # Flask routes, login, API endpoints
├── config.py              # Loads .env; all paths and settings
├── run.sh                 # Start dev server
├── run_production.sh      # Start gunicorn
├── requirements.txt       # Python dependencies
├── .env.example           # Config template (copy to .env)
│
├── templates/             # HTML pages (Jinja2)
│   ├── base.html          # Shared layout, nav, flash messages
│   ├── login.html         # Login form
│   └── dashboard.html     # Main operator dashboard
│
├── static/
│   ├── css/style.css      # Dashboard styling
│   └── js/dashboard.js    # Button clicks, API calls, auto-refresh
│
├── services/
│   ├── control.py         # Control layer: simulate vs live, all actions
│   ├── mountain.py        # Runs real observer commands (tcsh, PDU, mosaics)
│   └── mosaic_preview.py  # Converts FITS mosaics to PNG for the browser
│
├── sim/                   # Used when LS4_GUI_SIMULATE=true (or as fallback)
│   ├── state.py           # In-memory / file sim state (dome, PDU, scheduler)
│   ├── webcam_capture.py  # Generates placeholder webcam SVGs
│   ├── generate_mosaic.py # Generates placeholder mosaic SVG
│   └── pdu_api.py         # Fake PDU for VM testing
│
└── scripts/
    └── discover_mountain_paths.sh   # Read-only path discovery for .env
```


## What each part does

### `app.py`

Flask application entry point.

- `/login` — session-based authentication
- `/` — dashboard (requires login)
- `/api/*` — JSON API for dome, telescope, PDU, scheduler, webcams, mosaics

Returns HTTP 400 when an action fails; the dashboard shows the error message in a toast.

### `config.py`

Single source of truth for settings. Reads `.env` and provides defaults for the La Silla layout (`/home/observer`, `/home/ls4/kenneth`, `/data/observer`, etc.).

### `services/control.py`

Decides whether each action is **simulated** or **live** (`LS4_GUI_SIMULATE` + observer environment check).

Handles: dome, questctl, stow, PDU, scheduler, webcams, mosaic generation. Keeps sim state in sync for the dashboard badges.

### `services/mountain.py`

Invokes real mountain software:

| GUI action | Mountain command / source |
|------------|---------------------------|
| Start questctl | `start_questctl` |
| Stop questctl | `stop_questctl` |
| Open dome | `opendome_raw` |
| Close dome | `closedome.csh` |
| Scheduler start/stop | `obs_control_script start/stop` |
| Stow | `stow_telescope` |
| PDU outlet | `pdu_api.py -p/-o <outlet>` |
| Mosaic | `mos <prefix>` in exposure directory |
| Webcams | Latest images from kenneth / snapshots dirs |

Commands run in a `tcsh` shell with the observer `.tcshrc` sourced.

### `sim/`

Mock hardware for safe testing. Writes cache files under `LS4_SIM_DIR` (default `/home/observer/sim/`).

### Frontend (`templates/` + `static/`)

Server-rendered HTML with JavaScript calling the `/api/*` endpoints. Webcams auto-refresh on an interval. No WebSocket — multiple users do not see each other’s clicks unless they refresh.


## Security

- Login required for all pages and APIs.
- Shared username/password in `.env` (one operator account today).
- Binds to `0.0.0.0:8080` on the **private observatory network** — not exposed to the public internet.
- From home: VPN + SSH tunnel + GUI password.


## Troubleshooting

| Problem | Fix |
|---------|-----|
| Page still works after `Ctrl+C` | Hard refresh (`Ctrl+Shift+R`) — old cached page |
| Webcam POST returns 400 | Hardware/source down, or sim path issue; GET may still show placeholder |
| Mosaic 400 | Empty prefix — enter a valid exposure prefix |
| `mos: not in PATH` | Run from observer shell; live mosaics need full observer environment |
| Cannot open from laptop | Use SSH tunnel; direct `192.168.1.x` often fails even on VPN |
| Development server warning | Use `./run_production.sh` for gunicorn |


## Network addresses (reference)

| Address | Role |
|---------|------|
| `134.171.80.150:5900` | Public SSH entry (from home) |
| `192.168.1.73:8080` | Internal Flask URL (on mountain LAN / VNC) |
| `127.0.0.1:8080` | Your laptop, via SSH tunnel |
