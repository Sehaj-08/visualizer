# Hotspot Network Visualizer — Version 2

This repository contains Version 2 of the Hotspot Network Visualizer — a demo web app that simulates a hotspot network and animates live data transfers in real time.

Version 2 Improvements
- Clean, modern dark UI with responsive two-column layout
- Smooth directional transfer animations (moving dot) and node highlights
- Device detail panel (click a node to view stats)
- Server-side accumulated stats for each device (bytes sent / received)
- Activity log with timestamped, emoji-enhanced entries
- WebSocket auto-reconnect and stable event format for future real traffic

## Tech stack
- Backend: Python + FastAPI
- Realtime: WebSockets (server pushes simulated `transfer_event` messages)
- Frontend: plain HTML/CSS/vanilla JS with Vis.js Network for graph rendering

## Installation (Windows PowerShell)
```powershell
python -m venv venv
venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## Running
From the project root run:

```powershell
uvicorn app.backend.main:app --reload
```

Open `http://localhost:8000/` in your browser.

## Endpoints
- `GET /devices` — returns the list of simulated devices (including `bytes_sent` and `bytes_received`).
- `WS /ws` — WebSocket that emits `transfer_event` messages periodically. Each message includes updated `from_stats` and `to_stats` so the frontend can update device totals.

Example `transfer_event` message:
```json
{
	"type": "transfer_event",
	"from_id": 2,
	"to_id": 4,
	"bytes": 2048,
	"protocol": "TCP",
	"timestamp": "2025-01-01T12:34:56Z",
	"from_stats": { "bytes_sent": 12345, "bytes_received": 9876 },
	"to_stats": { "bytes_sent": 4321, "bytes_received": 5555 }
}
```

## How it works (quick)
- The frontend fetches `/devices` and initializes a Vis.js network (router visually distinct). 
- The frontend opens a WebSocket to `/ws` and listens for `transfer_event` messages.
- On each event: the frontend animates a moving dot from source → destination (~1.4s), briefly highlights nodes, and appends a log entry. The device detail panel updates with the latest stats.

## Files of interest
- `app/backend/main.py` — FastAPI app, simulated devices, WebSocket event generator (now accumulates stats)
- `app/frontend/index.html` — Frontend UI (layout + containers)
- `app/frontend/script.js` — Visualization, animation, WebSocket handling, UI interactions
- `app/frontend/styles.css` — Styling for dark theme

## Extending to real traffic
To plug in real events, replace the simulated generator logic inside `app/backend/main.py` while keeping the same `transfer_event` message format. The frontend expects the `from_stats` and `to_stats` fields and will update accordingly.

## Notes
- The UI is designed to be presentation-ready for demos and project submissions. The code is commented to help beginners understand how events are generated and visualized.

