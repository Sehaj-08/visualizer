# Hotspot Network Visualizer — Version 1

A small demo app that simulates a hotspot network and animates data transfers in real time.

## Overview
- Backend: Python + FastAPI
- Realtime: WebSockets (server pushes simulated `transfer_event` messages)
- Frontend: plain HTML/CSS/vanilla JS with Vis.js Network for graph rendering

## Installation
1. Create a virtual environment and activate it

Windows (PowerShell):
```
python -m venv venv
venv\Scripts\activate
```

2. Install dependencies

```
pip install -r requirements.txt
```

## Running
From the project root (where `requirements.txt` lives) run:

```
uvicorn app.backend.main:app --reload
```

Open `http://localhost:8000/` in your browser.

## How it works
- The backend exposes `GET /devices` which returns a list of simulated devices.
- The backend also opens a WebSocket at `/ws` and periodically sends `transfer_event` JSON messages.
- The frontend fetches `/devices`, draws a network using Vis.js, and listens on `/ws`.
- When a `transfer_event` arrives, the frontend animates a moving dot between the two nodes and briefly highlights nodes/edges.

## Files of interest
- `app/backend/main.py` — FastAPI app, simulated devices, WebSocket event generator
- `app/frontend/index.html` — Frontend UI
- `app/frontend/script.js` — Visualization and animation logic
- `app/frontend/styles.css` — Simple styling

## Extending to real traffic
Replace the simulated generator inside `app/backend/main.py` with actual monitoring code. Keep the WebSocket message format (`transfer_event`) unchanged so the frontend continues to work.
