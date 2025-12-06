from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path
import asyncio
import random
import datetime

app = FastAPI()

# Resolve paths so static serving works regardless of cwd
BASE_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = BASE_DIR / "frontend"

# In-memory simulated devices
# - id: integer
# - name: human-friendly name
# - ip_address: fake but realistic
# - mac_address: fake MAC address
# - device_type: router/phone/laptop/tablet
devices = [
    {"id": 1, "name": "Hotspot", "ip_address": "192.168.1.1", "mac_address": "AA:BB:CC:DD:EE:01", "device_type": "router"},
    {"id": 2, "name": "Alice's Phone", "ip_address": "192.168.1.10", "mac_address": "00:11:22:33:44:55", "device_type": "phone"},
    {"id": 3, "name": "Bob's Laptop", "ip_address": "192.168.1.11", "mac_address": "66:77:88:99:AA:BB", "device_type": "laptop"},
    {"id": 4, "name": "Carol's Tablet", "ip_address": "192.168.1.12", "mac_address": "CC:DD:EE:FF:00:11", "device_type": "tablet"},
    {"id": 5, "name": "Guest Phone", "ip_address": "192.168.1.13", "mac_address": "22:33:44:55:66:77", "device_type": "phone"}
]

# Serve frontend static files under /static
app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")

# Root serves index.html
@app.get("/")
async def index():
    index_file = FRONTEND_DIR / "index.html"
    return FileResponse(str(index_file))

# Devices REST endpoint
@app.get("/devices")
async def get_devices():
    """Return the list of simulated devices."""
    return devices

# WebSocket that pushes simulated transfer events to client
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    When a client connects, start sending simulated transfer_event messages
    periodically. The loop stops cleanly when the socket disconnects.

    Message format (JSON):
    {
      "type": "transfer_event",
      "from_id": 2,
      "to_id": 4,
      "bytes": 10240,
      "protocol": "TCP",
      "timestamp": "2025-01-01T12:34:56Z"
    }
    """
    await websocket.accept()
    try:
        while True:
            # Wait a random interval between 2 and 5 seconds
            await asyncio.sleep(random.uniform(2.0, 5.0))

            # Pick two distinct devices
            src, dst = random.sample(devices, 2)

            event = {
                "type": "transfer_event",
                "from_id": src["id"],
                "to_id": dst["id"],
                "bytes": random.randint(200, 20000),
                "protocol": random.choice(["TCP", "UDP"]),
                "timestamp": datetime.datetime.utcnow().isoformat() + "Z"
            }

            # Send the JSON event to the connected client
            await websocket.send_json(event)

    except WebSocketDisconnect:
        # Client disconnected; the loop ends and we exit cleanly
        return
