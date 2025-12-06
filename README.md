# Hotspot Network Visualizer — Version 3

This repository contains Version 3 of the Hotspot Network Visualizer — an interactive, analytics-focused web app that simulates a hotspot network with real-time traffic visualization and smart controls.

## Version 3 Enhancements
- **Simulation Controls**: Play/Pause, Speed adjustment (Slow/Normal/Fast), Reset Stats
- **Traffic Modes**: Random, Hotspot-Centric (85% router traffic), Heavy-Talker (one device dominates)
- **Global & Per-Device Stats**: Live transfer count, total bytes, top sender/receiver, per-device transfer participation
- **Alerts System**: Automatic high-traffic warnings for devices exceeding threshold (~500 KB)
- **Improved UI**: Control panel, global stats card, responsive layout, connection status indicator
- **Better event format**: WebSocket messages now include transfer count and per-device stats

## Tech Stack
- Backend: Python + FastAPI + WebSocket (simulated traffic)
- Frontend: HTML + CSS + Vanilla JS + Vis.js Network
- Dark modern UI with responsive design

## Installation (Windows PowerShell)
```powershell
python -m venv venv
venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## Running
```powershell
uvicorn app.backend.main:app --reload
```

Open `http://localhost:8000/` in your browser.

## How to Use
1. **Start the app** — the simulator begins in "Play" mode with "Normal" speed
2. **Change simulation mode** — select from Random, Hotspot-Centric, or Heavy-Talker
3. **Adjust speed** — Slow (4–5s between events), Normal (1–3s), or Fast (0.3–1s)
4. **Pause/Resume** — click the button to pause or resume transfer events
5. **Monitor stats** — watch Global Stats update in real time (transfers, bytes, top devices)
6. **Click a device** — view its detailed stats (sent, received, participation count)
7. **Check alerts** — high-traffic warnings appear automatically
8. **Reset** — clears all stats and logs, resetting the simulation

## WebSocket Messages

### Outgoing (Backend → Frontend)

**Transfer Event:**
```json
{
  "type": "transfer_event",
  "from_id": 2,
  "to_id": 4,
  "bytes": 2048,
  "protocol": "TCP",
  "timestamp": "2025-01-01T12:34:56Z",
  "from_stats": { "bytes_sent": 12345, "bytes_received": 9876, "transfer_count": 45 },
  "to_stats": { "bytes_sent": 4321, "bytes_received": 5555, "transfer_count": 32 }
}
```

**Alert:**
```json
{
  "type": "alert",
  "level": "warning",
  "device_id": 3,
  "message": "⚠️ High traffic: Bob's Laptop has sent 500.5 MB."
}
```

**Stats Reset Confirmation:**
```json
{
  "type": "stats_reset"
}
```

### Incoming (Frontend → Backend)

**Control Messages:**
```json
{ "type": "control", "action": "play" }
{ "type": "control", "action": "pause" }
{ "type": "control", "action": "set_speed", "level": "fast" }
{ "type": "control", "action": "set_mode", "mode": "hotspot" }
{ "type": "control", "action": "reset_stats" }
```

## Traffic Simulation Modes

### Random (Default)
- Completely random source and destination for each transfer.
- Represents general network chatter.

### Hotspot-Centric
- 85% of traffic flows through the router/hotspot.
- Reflects realistic WiFi usage where most devices communicate via the AP.
- Remaining 15% is random peer-to-peer or direct device communication.

### Heavy-Talker
- One randomly selected device becomes the "heavy talker" for ~30 seconds.
- That device sends 70% of its transfers out, receives 30%.
- After 30s, a new heavy talker is chosen.
- Simulates scenarios like file downloads, video streaming, or backup operations.

## Stats & Analytics

### Global Stats (shown at top of right panel)
- **Transfers**: Total number of transfer events since start/reset
- **Total Bytes**: Sum of all bytes transferred
- **Top Sender**: Device currently with the highest `bytes_sent`
- **Top Receiver**: Device currently with the highest `bytes_received`

### Per-Device Stats (click a device in the graph)
- **Bytes Sent**: Total outbound traffic
- **Bytes Received**: Total inbound traffic
- **Transfers**: Number of transfers the device participated in

### Alerts
- Automatically triggered when a device's `bytes_sent` exceeds ~500 KB
- Each device is alerted once; alert clears on stats reset
- Appears in the Alerts panel with a timestamp and device name

## Files
- `app/backend/main.py` — FastAPI backend with modes, controls, and stats accumulation
- `app/frontend/index.html` — Markup for control panel, stats, alerts, graph, and log
- `app/frontend/styles.css` — Dark modern theme, responsive layout
- `app/frontend/script.js` — WebSocket handling, controls, animations, stats UI updates
- `requirements.txt` — Python dependencies (FastAPI, Uvicorn)
- `README.md` — This file

## Extending Version 3
To replace simulated traffic with real network monitoring:
1. Replace the `pick_transfer_pair()` function in `app/backend/main.py` with real packet capture logic.
2. Keep the same WebSocket message format so the frontend works unchanged.
3. Update `HIGH_TRAFFIC_THRESHOLD` if needed for your network.

## Notes
- The UI is designed to be clean, beginner-friendly, and suitable for presentations or project submissions.
- Backend is stateful during a session; restart to clear all stats and reset simulation state.
- Alerts and high-traffic tracking is per-session (not persisted).
