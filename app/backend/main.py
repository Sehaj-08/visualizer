from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path
import asyncio
import random
import datetime
import subprocess
import socket
import re
from typing import List, Dict, Optional
from ipaddress import ip_network,ip_address

app = FastAPI()

# Resolve paths so static serving works regardless of cwd
BASE_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = BASE_DIR / "frontend"

# ========== VERSION 4: REAL DEVICE DISCOVERY CONFIG ==========
NETWORK_CIDR = "192.168.137.0/24"  # Change this to match your hotspot/LAN subnet
ARP_SCAN_ENABLED = True
SCAN_CACHE_TTL_SECONDS = 15  # Re-scan every N seconds
# ============================================================

# Device discovery cache
last_scan_time = None
last_scan_devices: List[Dict] = []
local_router_ip = None


def get_local_ip_in_subnet():
    """
    Attempt to detect the local machine's IP address.
    Returns the IP of the interface that would route to NETWORK_CIDR.
    """
    try:
        # Try to connect to a socket to find the local IP
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        return local_ip
    except Exception as e:
        print(f"Warning: Could not detect local IP: {e}")
        return None

def parse_arp_table():
    """
    Parse the ARP table using 'arp -a' command (Windows-compatible).
    Returns a list of (ip_address, mac_address) tuples for devices in NETWORK_CIDR.
    """
    try:
        result = subprocess.run(
            ["arp", "-a"],
            capture_output=True,
            text=True,
            timeout=5
        )
        lines = result.stdout.split("\n")

        devices = []
        subnet = ip_network(NETWORK_CIDR, strict=False)

        for line in lines:
            # Skip interface headers + empty lines
            if "Interface:" in line or not line.strip():
                continue

            parts = line.split()
            if len(parts) < 3:
                continue

            ip_str = parts[0].strip()
            mac_str = parts[1].strip()
            type_str = parts[2].strip().lower()

            try:
                # Validate and parse IP as a single address
                ip_obj = ip_address(ip_str)
            except ValueError:
                # Not an IP (maybe junk or header) → skip
                continue

            # Only keep entries in our hotspot subnet
            if ip_obj not in subnet:
                continue

            # Normalise MAC
            mac = mac_str.replace("-", ":").lower()

            # Ignore broadcast ff:ff:ff:ff:ff:ff
            if mac == "ff:ff:ff:ff:ff:ff":
                continue

            # IMPORTANT: do NOT filter on type_str.
            # We accept both 'dynamic' and 'static', since your hotspot marks them as static.
            devices.append((ip_str, mac))

        return devices

    except Exception as e:
        print(f"Warning: ARP scan failed: {e}")
        return []

def ping_subnet_and_scan():
    """
    Ping sweep the subnet to populate ARP cache, then parse ARP table.
    (This helps discover devices that might not be in ARP cache yet.)
    """
    try:
        subnet = ip_network(NETWORK_CIDR, strict=False)
        # Only ping a subset of the subnet to avoid excessive network traffic
        # Ping the gateway, broadcast, and a sample of hosts
        ips_to_ping = [
            str(subnet.network_address + 1),  # gateway
            str(subnet.broadcast_address - 1),  # broadcast
        ]
        
        for i in [10, 100, 200]:
            try:
                ip = str(subnet.network_address + i)
                if ip in subnet:
                    ips_to_ping.append(ip)
            except:
                pass
        
        # Ping with short timeout
        for ip in ips_to_ping:
            try:
                if hasattr(subprocess, "DEVNULL"):
                    subprocess.run(
                        ["ping", "-n" if subprocess.os.name == "nt" else "-c", "1", "-w", "100" if subprocess.os.name == "nt" else "-W", "100", ip],
                        capture_output=True,
                        timeout=1
                    )
            except:
                pass
    except Exception as e:
        print(f"Warning: Ping sweep failed: {e}")


def discover_devices() -> List[Dict]:
    """
    Discover real devices on the local network using ARP scan and ping sweep.
    Returns a list of device dictionaries with id, name, ip_address, mac_address, device_type.
    """
    global last_scan_time, last_scan_devices, local_router_ip
    
    now = datetime.datetime.now()
    
    # Check cache
    if last_scan_time and (now - last_scan_time).total_seconds() < SCAN_CACHE_TTL_SECONDS:
        return last_scan_devices
    
    print("[DISCOVERY] Scanning network...")
    devices = []
    
    # Step 1: Detect local router IP (this machine)
    local_ip = get_local_ip_in_subnet()
    if local_ip:
        local_router_ip = local_ip
    
    # Step 2: Ping sweep to populate ARP cache
    if ARP_SCAN_ENABLED:
        ping_subnet_and_scan()
    
    # Step 3: Parse ARP table
    arp_devices = parse_arp_table()
    
    # Step 4: Build device list
    device_id_counter = 1
    seen_ips = set()
    
    # Add local router first
    if local_ip:
        devices.append({
            "id": device_id_counter,
            "name": "Hotspot (This Device)",
            "ip_address": local_ip,
            "mac_address": "00:00:00:00:00:00",  # We'll update this below if possible
            "device_type": "router",
            "bytes_sent": 0,
            "bytes_received": 0,
            "transfer_count": 0,
            "alerted_high_traffic": False
        })
        seen_ips.add(local_ip)
        device_id_counter += 1
    
    # Add discovered devices from ARP
    for ip, mac in arp_devices:
        if ip not in seen_ips:
            # Generate a friendly name based on IP last octet
            last_octet = ip.split(".")[-1]
            name = f"Device-{last_octet}"
            
            devices.append({
                "id": device_id_counter,
                "name": name,
                "ip_address": ip,
                "mac_address": mac,
                "device_type": "host",
                "bytes_sent": 0,
                "bytes_received": 0,
                "transfer_count": 0,
                "alerted_high_traffic": False
            })
            seen_ips.add(ip)
            device_id_counter += 1
    
    # If we found fewer than 2 devices, add a fallback
    if len(devices) < 2:
        print("[DISCOVERY] Warning: Found fewer than 2 devices. Adding fallback device.")
        devices.append({
            "id": device_id_counter,
            "name": "Device-Fallback",
            "ip_address": "192.168.137.254",
            "mac_address": "ff:ff:ff:ff:ff:ff",
            "device_type": "host",
            "bytes_sent": 0,
            "bytes_received": 0,
            "transfer_count": 0,
            "alerted_high_traffic": False
        })
    
    # Cache the results
    last_scan_time = now
    last_scan_devices = devices
    
    print(f"[DISCOVERY] Found {len(devices)} device(s)")
    return devices


# Simulation state management
class SimulationState:
    """Manages simulation control state, modes, and device stats."""
    def __init__(self):
        self.is_running = True
        self.mode = "random"
        self.speed = "normal"
        self.heavy_talker_id = None
        self.heavy_talker_change_time = 0
        self.transfer_count = 0

sim_state = SimulationState()

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
    """
    Return the list of discovered devices (real devices from ARP scan).
    This endpoint uses caching to avoid scanning too frequently.
    """
    return discover_devices()


def get_delay():
    """Return the delay (in seconds) between transfer events based on current speed."""
    if sim_state.speed == "slow":
        return random.uniform(4.0, 5.5)
    elif sim_state.speed == "fast":
        return random.uniform(0.3, 1.0)
    else:  # "normal"
        return random.uniform(1.5, 3.0)


def pick_transfer_pair(devices):
    """
    Pick a source and destination device based on the current traffic mode.
    Now uses the real discovered devices instead of a static list.
    """
    if len(devices) < 2:
        return None
    
    now = datetime.datetime.now().timestamp()
    
    if sim_state.mode == "hotspot":
        # 85% of traffic goes through router
        router = next((d for d in devices if d["device_type"] == "router"), devices[0])
        other = random.choice([d for d in devices if d["id"] != router["id"]])
        if random.random() < 0.5:
            return router, other
        else:
            return other, router
    
    elif sim_state.mode == "heavy_talker":
        # Periodically change the heavy talker (every 30 seconds)
        if sim_state.heavy_talker_id is None or (now - sim_state.heavy_talker_change_time > 30):
            candidates = [d for d in devices if d["device_type"] != "router"]
            if candidates:
                sim_state.heavy_talker_id = random.choice(candidates)["id"]
                sim_state.heavy_talker_change_time = now
        
        heavy = next((d for d in devices if d["id"] == sim_state.heavy_talker_id), None)
        if heavy:
            other = random.choice([d for d in devices if d["id"] != heavy["id"]])
            if random.random() < 0.7:
                return heavy, other
            else:
                return other, heavy
        else:
            return random.sample(devices, 2)
    
    else:  # "random"
        return random.sample(devices, 2)


def check_high_traffic_alerts(devices):
    """
    Check if any device exceeds HIGH_TRAFFIC_THRESHOLD and return alert messages.
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
    Now uses discovered real devices for the transfer simulation.
    """
    await websocket.accept()
    try:
        while True:
            # Refresh device list periodically (inherits cache logic)
            current_devices = discover_devices()
            
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
                        for device in current_devices:
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
            if sim_state.is_running and len(current_devices) >= 2:
                await asyncio.sleep(get_delay())
                
                pair = pick_transfer_pair(current_devices)
                if pair is None:
                    await asyncio.sleep(0.5)
                    continue
                
                src, dst = pair
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
                alerts = check_high_traffic_alerts(current_devices)
                for alert in alerts:
                    await websocket.send_json(alert)
            else:
                # Pause or insufficient devices: just wait a bit without generating events
                await asyncio.sleep(0.5)
    
    except WebSocketDisconnect:
        return
