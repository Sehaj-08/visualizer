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

# Simulation state management
class SimulationState:
    """Manages simulation control state, modes, and device stats."""
    def __init__(self):
        self.is_running = True
        self.mode = "random"  # "random", "hotspot", "heavy_talker"
        self.speed = "normal"  # "slow", "normal", "fast"
        self.heavy_talker_id = None
        self.heavy_talker_change_time = 0
        self.transfer_count = 0

sim_state = SimulationState()

# In-memory simulated devices with runtime stats (Version 3: enhanced)
# Each device now tracks bytes_sent, bytes_received, transfer count, and alert status
devices = [
    {"id": 1, "name": "Hotspot", "ip_address": "192.168.1.1", "mac_address": "AA:BB:CC:DD:EE:01", "device_type": "router", "bytes_sent": 0, "bytes_received": 0, "transfer_count": 0, "alerted_high_traffic": False},
    {"id": 2, "name": "Alice's Phone", "ip_address": "192.168.1.10", "mac_address": "00:11:22:33:44:55", "device_type": "phone", "bytes_sent": 0, "bytes_received": 0, "transfer_count": 0, "alerted_high_traffic": False},
    {"id": 3, "name": "Bob's Laptop", "ip_address": "192.168.1.11", "mac_address": "66:77:88:99:AA:BB", "device_type": "laptop", "bytes_sent": 0, "bytes_received": 0, "transfer_count": 0, "alerted_high_traffic": False},
    {"id": 4, "name": "Carol's Tablet", "ip_address": "192.168.1.12", "mac_address": "CC:DD:EE:FF:00:11", "device_type": "tablet", "bytes_sent": 0, "bytes_received": 0, "transfer_count": 0, "alerted_high_traffic": False},
    {"id": 5, "name": "Guest Phone", "ip_address": "192.168.1.13", "mac_address": "22:33:44:55:66:77", "device_type": "phone", "bytes_sent": 0, "bytes_received": 0, "transfer_count": 0, "alerted_high_traffic": False}
]

HIGH_TRAFFIC_THRESHOLD = 500000  # bytes (500 KB)


# Serve frontend static files under /static
app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")


@app.get("/")
async def index():
    """Return the frontend index page."""
    index_file = FRONTEND_DIR / "index.html"
    return FileResponse(str(index_file))


@app.get("/devices")
async def get_devices():
    """Return the list of simulated devices including their runtime stats."""
    return devices


def get_delay():
    """Return the delay (in seconds) between transfer events based on current speed."""
    if sim_state.speed == "slow":
        return random.uniform(4.0, 5.5)
    elif sim_state.speed == "fast":
        return random.uniform(0.3, 1.0)
    else:  # "normal"
        return random.uniform(1.5, 3.0)


def pick_transfer_pair():
    """
    Pick a source and destination device based on the current traffic mode.
    
    Modes:
    - "random": completely random pairs
    - "hotspot": 85% traffic involves router, 15% random
    - "heavy_talker": one device is the heavy talker
    """
    now = datetime.datetime.now().timestamp()
    
    if sim_state.mode == "hotspot":
        # 85% of traffic goes through router
        if random.random() < 0.85:
            router = devices[0]  # assume id=1 is router
            other = random.choice([d for d in devices if d["id"] != router["id"]])
            # 50/50 direction
            if random.random() < 0.5:
                return router, other
            else:
                return other, router
        else:
            return random.sample(devices, 2)
    
    elif sim_state.mode == "heavy_talker":
        # Periodically change the heavy talker (every 30 seconds)
        if sim_state.heavy_talker_id is None or (now - sim_state.heavy_talker_change_time > 30):
            # Pick a non-router device
            candidates = [d for d in devices if d["device_type"] != "router"]
            sim_state.heavy_talker_id = random.choice(candidates)["id"]
            sim_state.heavy_talker_change_time = now
        
        heavy = None
        for d in devices:
            if d["id"] == sim_state.heavy_talker_id:
                heavy = d
                break
        
        if heavy:
            other = random.choice([d for d in devices if d["id"] != heavy["id"]])
            # 70% heavy talker sends, 30% heavy talker receives
            if random.random() < 0.7:
                return heavy, other
            else:
                return other, heavy
        else:
            return random.sample(devices, 2)
    
    else:  # "random"
        return random.sample(devices, 2)


def check_high_traffic_alerts():
    """
    Check if any device exceeds HIGH_TRAFFIC_THRESHOLD and return alert messages.
    Only alerts once per device unless stats are reset.
    """
    alerts = []
    for device in devices:
        if device["bytes_sent"] > HIGH_TRAFFIC_THRESHOLD and not device["alerted_high_traffic"]:
            device["alerted_high_traffic"] = True
            alerts.append({
                "type": "alert",
                "level": "warning",
                "device_id": device["id"],
                "message": f"⚠️ High traffic: {device['name']} has sent {device['bytes_sent'] / 1024 / 1024:.1f} MB."
            })
    return alerts


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for real-time transfer events and control messages.
    
    Incoming message types:
    - { "type": "control", "action": "play" | "pause" | "reset_stats", ... }
    - { "type": "control", "action": "set_speed", "level": "slow" | "normal" | "fast" }
    - { "type": "control", "action": "set_mode", "mode": "random" | "hotspot" | "heavy_talker" }
    
    Outgoing message types:
    - { "type": "transfer_event", ... }
    - { "type": "alert", ... }
    - { "type": "stats_snapshot", ... }
    """
    await websocket.accept()
    try:
        while True:
            # Non-blocking check for incoming control messages
            try:
                data = await asyncio.wait_for(websocket.receive_json(), timeout=0.1)
                if data.get("type") == "control":
                    action = data.get("action")
                    
                    if action == "play":
                        sim_state.is_running = True
                    elif action == "pause":
                        sim_state.is_running = False
                    elif action == "set_speed":
                        level = data.get("level", "normal")
                        if level in ["slow", "normal", "fast"]:
                            sim_state.speed = level
                    elif action == "set_mode":
                        mode = data.get("mode", "random")
                        if mode in ["random", "hotspot", "heavy_talker"]:
                            sim_state.mode = mode
                    elif action == "reset_stats":
                        # Reset all device stats
                        for device in devices:
                            device["bytes_sent"] = 0
                            device["bytes_received"] = 0
                            device["transfer_count"] = 0
                            device["alerted_high_traffic"] = False
                        sim_state.transfer_count = 0
                        await websocket.send_json({
                            "type": "stats_reset"
                        })
            except asyncio.TimeoutError:
                pass
            
            # Generate and send transfer events if running
            if sim_state.is_running:
                await asyncio.sleep(get_delay())
                
                src, dst = pick_transfer_pair()
                size = random.randint(256, 65536)
                
                # Update stats
                src["bytes_sent"] += size
                dst["bytes_received"] += size
                src["transfer_count"] += 1
                dst["transfer_count"] += 1
                sim_state.transfer_count += 1
                
                event = {
                    "type": "transfer_event",
                    "from_id": src["id"],
                    "to_id": dst["id"],
                    "bytes": size,
                    "protocol": random.choice(["TCP", "UDP"]),
                    "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
                    "from_stats": {"bytes_sent": src["bytes_sent"], "bytes_received": src["bytes_received"], "transfer_count": src["transfer_count"]},
                    "to_stats": {"bytes_sent": dst["bytes_sent"], "bytes_received": dst["bytes_received"], "transfer_count": dst["transfer_count"]}
                }
                
                await websocket.send_json(event)
                
                # Check and send alerts if needed
                alerts = check_high_traffic_alerts()
                for alert in alerts:
                    await websocket.send_json(alert)
            else:
                # Pause: just wait a bit without generating events
                await asyncio.sleep(0.5)
    
    except WebSocketDisconnect:
        return
