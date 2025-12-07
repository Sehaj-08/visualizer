# Hotspot Network Visualizer — Version 4 (Real Devices, Simulated Traffic)

This repository contains Version 4 of the Hotspot Network Visualizer — an interactive, analytics-focused web app that discovers **real devices on your local network** and animates simulated data transfers between them.

## 🆕 Version 4 Changes
**Major improvement**: Devices are now **discovered from your actual network** using ARP scan + ping sweep, not hard-coded.

- Real device discovery via ARP table parsing
- Automatic detection of local hotspot/router as central node
- Simulated traffic patterns now operate on real discovered devices
- All Version 3 features (controls, modes, stats, alerts) work unchanged with real devices
- Scan results cached for 15 seconds to avoid excessive network traffic
- Graceful fallback if fewer than 2 devices discovered

## Tech Stack
- Backend: Python + FastAPI + WebSocket (stdlib only: subprocess, socket, ipaddress)
- Frontend: HTML + CSS + Vanilla JS + Vis.js Network
- Dark modern UI with responsive design

## Installation (Windows PowerShell)
```powershell
python -m venv venv
venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## Before Running – Configure Your Network

Edit `app/backend/main.py` line 18 to match your network:

```python
NETWORK_CIDR = "192.168.137.0/24"  # ← Change this to your subnet
```

### Finding Your Subnet

**Windows (PowerShell):**
```powershell
ipconfig
```
Look for "IPv4 Address" (e.g., `192.168.137.5`) and "Subnet Mask" (e.g., `255.255.255.0`).

The subnet is typically the first 3 octets + `.0/24`. Examples:
- `192.168.1.0/24`
- `192.168.137.0/24`
- `10.0.0.0/24`

**macOS/Linux:**
```bash
ifconfig
```

## Running

```powershell
uvicorn app.backend.main:app --reload
```

Open `http://localhost:8000/` in your browser.

**First-time startup**: The app will scan your network and discover devices. This may take 5–10 seconds. Subsequent `/devices` calls are cached for 15 seconds.

## How to Use
1. **Wait for device discovery** — the graph will populate with real devices from your network
2. **Start the simulation** — devices begin exchanging simulated traffic
3. **Change simulation mode** — Random, Hotspot-Centric (most traffic through router), or Heavy-Talker
4. **Adjust speed** — Slow, Normal, or Fast
5. **Monitor stats** — watch transfer counts and byte totals update
6. **Click a device** — view its detailed stats
7. **Check alerts** — high-traffic warnings appear automatically
8. **Reset** — clears all stats and logs

## Device Discovery Details

### How It Works
1. **Ping sweep**: Sends ICMP ping to a sample of IPs in the subnet to populate ARP cache
2. **ARP table parsing**: Runs `arp -a` command and parses output
3. **Local IP detection**: Identifies this machine as the "Hotspot/Router" central node
4. **Caching**: Results cached for 15 seconds to avoid repeated scanning

### Supported Platforms
- **Windows**: Uses `arp -a` command (built-in)
- **macOS/Linux**: Uses `arp -a` command (built-in)

### Requirements
- ARP must be available on your system (standard on all major OS)
- All devices should be on the same subnet
- Admin/root privileges usually NOT required (but may be on some corporate networks)

### Configuration
In `app/backend/main.py`:

```python
NETWORK_CIDR = "192.168.137.0/24"          # Change to your subnet
ARP_SCAN_ENABLED = True                    # Set to False to disable ping sweep
SCAN_CACHE_TTL_SECONDS = 15                # Cache results for 15 seconds
```

## Device Naming

Devices are automatically named based on their IP address:
- Local machine: "Hotspot (This Device)" — marked as `device_type: "router"`
- Other devices: "Device-{last_octet}" — marked as `device_type: "host"`

For example:
- 192.168.137.1 → "Hotspot (This Device)"
- 192.168.137.10 → "Device-10"
- 192.168.137.45 → "Device-45"

If a device is not in ARP table, it will not appear in the graph.

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
  "timestamp": "2025-01-07T12:34:56Z",
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
  "message": "⚠️ High traffic: Device-10 has sent 500.5 MB."
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

All modes operate on **real discovered devices** instead of simulated ones.

### Random (Default)
Random source and destination for each transfer.

### Hotspot-Centric
85% of transfers flow through the router ("Hotspot (This Device)").
Reflects realistic WiFi usage where all traffic goes through the AP.

### Heavy-Talker
One device dominates for ~30 seconds, then rotates.
Simulates file downloads or video streaming scenarios.

## Stats & Analytics

### Global Stats
- **Transfers**: Total transfer events since start/reset
- **Total Bytes**: Sum of all bytes transferred (real-time)
- **Top Sender**: Device with highest `bytes_sent`
- **Top Receiver**: Device with highest `bytes_received`

### Per-Device Stats (click a device)
- **Bytes Sent**: Total outbound traffic
- **Bytes Received**: Total inbound traffic
- **Transfers**: Number of transfers participated in

### Alerts
- Triggered when a device's `bytes_sent` exceeds ~500 KB
- Each device alerted once; clears on stats reset
- Appears with timestamp and device name

## Files
- `app/backend/main.py` — FastAPI backend with ARP discovery, simulation, controls
- `app/frontend/index.html` — Markup for control panel, stats, alerts, graph, log
- `app/frontend/styles.css` — Dark modern theme, responsive layout
- `app/frontend/script.js` — WebSocket handling, UI updates, animations
- `requirements.txt` — Python dependencies (FastAPI, Uvicorn only)
- `README.md` / `README_V4.md` — This file

## Troubleshooting

### No devices discovered
1. Check `NETWORK_CIDR` in `app/backend/main.py` matches your network
2. Ensure connected devices are online
3. Try pinging other devices manually to verify network connectivity
4. Check that `arp -a` command works on your system

### Only one device (Hotspot) discovered
Devices may not be in ARP cache yet. They appear after they communicate on the network.
Try enabling ping sweep: `ARP_SCAN_ENABLED = True` (default).

### Performance issues (slow device discovery)
Increase cache TTL: `SCAN_CACHE_TTL_SECONDS = 30` (fewer scans).
Or disable ping sweep: `ARP_SCAN_ENABLED = False` (faster but less thorough).

## Security & Privacy Notes
- This app is designed for **local networks you control** (e.g., your hotspot).
- ARP scanning and visualization is only visible locally at `http://localhost:8000/`.
- Do **not** expose this app to untrusted networks.
- For security-conscious environments, review the code before running.

## Extending Version 4
To replace simulated traffic with real packet monitoring:
1. Replace the `random.randint(256, 65536)` with actual network traffic statistics
2. Modify traffic simulation to match real packet patterns
3. Keep the same WebSocket message format so frontend works unchanged

## Comparison: Versions 1–4

| Feature | V1 | V2 | V3 | V4 |
|---------|----|----|----|----|
| Simulated Devices | ✅ | ✅ | ✅ | ❌ |
| Real Device Discovery | ❌ | ❌ | ❌ | ✅ |
| Simulated Traffic | ✅ | ✅ | ✅ | ✅ |
| UI Styling | Basic | Dark | Dark + Stats | Dark + Stats |
| Controls (Mode/Speed) | ❌ | ❌ | ✅ | ✅ |
| Alerts | ❌ | ❌ | ✅ | ✅ |
| ARP Caching | N/A | N/A | N/A | ✅ |

---

**Version 4 Release Notes**: Version 4 transitions from a demo app with fake devices to a real network monitoring simulation. All existing features are preserved; devices are now discovered from your actual network.
