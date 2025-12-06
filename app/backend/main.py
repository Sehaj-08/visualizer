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

# In-memory simulated devices with runtime stats
# Each device includes bytes_sent and bytes_received to track simple stats.
devices = [
    {"id": 1, "name": "Hotspot", "ip_address": "192.168.1.1", "mac_address": "AA:BB:CC:DD:EE:01", "device_type": "router", "bytes_sent": 0, "bytes_received": 0},
    {"id": 2, "name": "Alice's Phone", "ip_address": "192.168.1.10", "mac_address": "00:11:22:33:44:55", "device_type": "phone", "bytes_sent": 0, "bytes_received": 0},
    {"id": 3, "name": "Bob's Laptop", "ip_address": "192.168.1.11", "mac_address": "66:77:88:99:AA:BB", "device_type": "laptop", "bytes_sent": 0, "bytes_received": 0},
    {"id": 4, "name": "Carol's Tablet", "ip_address": "192.168.1.12", "mac_address": "CC:DD:EE:FF:00:11", "device_type": "tablet", "bytes_sent": 0, "bytes_received": 0},
    {"id": 5, "name": "Guest Phone", "ip_address": "192.168.1.13", "mac_address": "22:33:44:55:66:77", "device_type": "phone", "bytes_sent": 0, "bytes_received": 0}
]

# Serve frontend static files under /static
app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")


@app.get("/")
async def index():
    """Return the frontend index page."""
    index_file = FRONTEND_DIR / "index.html"
    return FileResponse(str(index_file))


@app.get("/devices")
async def get_devices():
    """Return the list of simulated devices including their runtime stats.

    This endpoint is used by the frontend to build the initial network and
    to display device information.
    """
    return devices


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint that periodically emits simulated `transfer_event`
    messages. Each message includes updated stats for the source and
    destination device so the frontend can display live totals.

    The message format includes `from_stats` and `to_stats` objects with
    the `bytes_sent` / `bytes_received` totals after applying the event.
    """
    await websocket.accept()
    try:
        while True:
            # Wait a random interval between 1.5 and 4.0 seconds for snappier events
            await asyncio.sleep(random.uniform(1.5, 4.0))

            # Choose two distinct devices
            src, dst = random.sample(devices, 2)

            # Simulate transfer size in bytes
            size = random.randint(256, 65536)

            # Update backend stats (simple accumulation)
            src["bytes_sent"] += size
            dst["bytes_received"] += size

            event = {
                "type": "transfer_event",
                "from_id": src["id"],
                "to_id": dst["id"],
                "bytes": size,
                "protocol": random.choice(["TCP", "UDP"]),
                "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
                "from_stats": {"bytes_sent": src["bytes_sent"], "bytes_received": src["bytes_received"]},
                "to_stats": {"bytes_sent": dst["bytes_sent"], "bytes_received": dst["bytes_received"]}
            }

            # Send the JSON event to the connected client
            await websocket.send_json(event)

    except WebSocketDisconnect:
        # Client disconnected; exit cleanly
        return
