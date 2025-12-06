// Frontend script for Hotspot Network Visualizer — Version 3
// Enhanced with: simulation controls, traffic modes, stats, alerts, and better UI

let network = null;
let nodesDS = null;
let edgesDS = null;
let deviceMap = {}; // id -> device object
let selectedDeviceId = null;
let globalStats = { transfers: 0, totalBytes: 0 };

const reconnect = { attempt: 0 };

window.addEventListener('DOMContentLoaded', async () => {
  const devices = await fetchDevices();
  buildNetwork(devices);
  setupControls();
  setupInteractions();
  connectWebSocket();
});

async function fetchDevices() {
  const res = await fetch('/devices');
  if (!res.ok) throw new Error('Failed to fetch /devices');
  const list = await res.json();
  list.forEach(d => { deviceMap[d.id] = d; });
  return list;
}

function buildNetwork(devices) {
  const container = document.getElementById('network');
  const nodes = devices.map(d => ({
    id: d.id,
    label: d.name,
    title: `${d.name} (${d.ip_address})\n${d.device_type} · ${d.mac_address}`,
    color: d.device_type === 'router' ? '#3dd4ff' : (d.device_type === 'phone' ? '#9b7bff' : (d.device_type === 'laptop' ? '#6be56b' : '#ffd166')),
    shape: d.device_type === 'router' ? 'star' : (d.device_type === 'phone' ? 'triangle' : (d.device_type === 'laptop' ? 'square' : 'dot')),
    size: d.device_type === 'router' ? 36 : 20
  }));

  const router = devices.find(d => d.device_type === 'router') || devices[0];
  const edges = devices
    .filter(d => d.id !== router.id)
    .map(d => ({ from: router.id, to: d.id, color: { color: '#2b3440' }, width: 1 }));

  nodesDS = new vis.DataSet(nodes);
  edgesDS = new vis.DataSet(edges);
  const data = { nodes: nodesDS, edges: edgesDS };
  const options = {
    physics: { stabilization: true, barnesHut: { gravitationalConstant: -4000 } },
    edges: { smooth: { type: 'cubicBezier' } },
    nodes: { font: { multi: 'html' } },
    interaction: { hover: true }
  };

  network = new vis.Network(container, data, options);
  network.on('click', params => {
    if (params.nodes && params.nodes.length === 1) {
      const id = params.nodes[0];
      selectedDeviceId = id;
      showDeviceInfo(id);
      nodesDS.update({ id, borderWidth: 3, color: { border: '#fff' } });
      setTimeout(() => nodesDS.update({ id, borderWidth: 0 }), 1400);
    }
  });
}

function setupControls() {
  // Play / Pause
  document.getElementById('play-pause-btn').addEventListener('click', () => {
    const btn = document.getElementById('play-pause-btn');
    const isPlaying = btn.textContent.includes('Play');
    const action = isPlaying ? 'play' : 'pause';
    btn.textContent = isPlaying ? '⏸ Pause' : '▶ Play';
    sendControlMessage({ type: 'control', action });
  });

  // Speed control
  document.getElementById('speed-select').addEventListener('change', (e) => {
    sendControlMessage({ type: 'control', action: 'set_speed', level: e.target.value });
  });

  // Mode control
  document.getElementById('mode-select').addEventListener('change', (e) => {
    sendControlMessage({ type: 'control', action: 'set_mode', mode: e.target.value });
  });

  // Reset stats
  document.getElementById('reset-stats-btn').addEventListener('click', () => {
    sendControlMessage({ type: 'control', action: 'reset_stats' });
  });
}

function setupInteractions() {
  // nothing extra for now
}

function sendControlMessage(msg) {
  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify(msg));
  }
}

let ws = null;

function connectWebSocket() {
  const url = (location.protocol === 'https:' ? 'wss://' : 'ws://') + location.host + '/ws';
  ws = new WebSocket(url);

  ws.addEventListener('open', () => {
    console.log('WS open');
    reconnect.attempt = 0;
    updateConnectionStatus(true);
  });

  ws.addEventListener('message', ev => {
    try {
      const msg = JSON.parse(ev.data);
      if (msg.type === 'transfer_event') {
        handleTransferEvent(msg);
      } else if (msg.type === 'alert') {
        handleAlert(msg);
      } else if (msg.type === 'stats_reset') {
        handleStatsReset();
      }
    } catch (err) {
      console.error('WS parse', err);
    }
  });

  ws.addEventListener('close', () => {
    console.log('WS closed');
    updateConnectionStatus(false);
    reconnect.attempt += 1;
    const delay = Math.min(30000, 1000 * Math.pow(1.8, reconnect.attempt));
    setTimeout(connectWebSocket, delay);
  });

  ws.addEventListener('error', () => ws.close());
}

function updateConnectionStatus(connected) {
  const dot = document.getElementById('connection-status');
  if (connected) {
    dot.className = 'status-dot status-connected';
    dot.parentElement.textContent = '🟢 Connected';
    dot.parentElement.insertBefore(dot, dot.parentElement.firstChild);
  } else {
    dot.className = 'status-dot status-disconnected';
    dot.parentElement.textContent = '🔴 Disconnected — reconnecting...';
    dot.parentElement.insertBefore(dot, dot.parentElement.firstChild);
  }
}

function handleTransferEvent(ev) {
  // Update local device stats
  if (ev.from_stats) {
    deviceMap[ev.from_id].bytes_sent = ev.from_stats.bytes_sent;
    deviceMap[ev.from_id].bytes_received = ev.from_stats.bytes_received;
    deviceMap[ev.from_id].transfer_count = ev.from_stats.transfer_count;
  }
  if (ev.to_stats) {
    deviceMap[ev.to_id].bytes_sent = ev.to_stats.bytes_sent;
    deviceMap[ev.to_id].bytes_received = ev.to_stats.bytes_received;
    deviceMap[ev.to_id].transfer_count = ev.to_stats.transfer_count;
  }

  // Update global stats
  globalStats.transfers++;
  globalStats.totalBytes += ev.bytes;
  updateGlobalStats();

  // Update selected device info if visible
  if (selectedDeviceId) updateSelectedDeviceInfo();

  appendLogEntry(ev);
  animateTransfer(ev.from_id, ev.to_id, ev.bytes);
}

function handleAlert(alert) {
  const list = document.getElementById('alerts-list');
  const div = document.createElement('div');
  div.className = 'alert-item';
  div.textContent = alert.message;
  list.prepend(div);
  // Keep recent 50 alerts
  while (list.children.length > 50) list.removeChild(list.lastChild);
}

function handleStatsReset() {
  // Clear local stats
  globalStats = { transfers: 0, totalBytes: 0 };
  Object.values(deviceMap).forEach(d => {
    d.bytes_sent = 0;
    d.bytes_received = 0;
    d.transfer_count = 0;
    d.alerted_high_traffic = false;
  });
  updateGlobalStats();
  updateSelectedDeviceInfo();
  
  // Clear log and alerts
  document.getElementById('log-entries').innerHTML = '';
  document.getElementById('alerts-list').innerHTML = '';
  
  appendLogEntry({ timestamp: new Date().toISOString(), special: 'reset' });
}

function updateGlobalStats() {
  document.getElementById('stat-transfers').textContent = globalStats.transfers;
  document.getElementById('stat-total-bytes').textContent = formatBytes(globalStats.totalBytes);

  // Find top sender and receiver
  let topSender = null, topReceiver = null;
  let maxSent = 0, maxRecv = 0;
  Object.values(deviceMap).forEach(d => {
    if (d.bytes_sent > maxSent) { maxSent = d.bytes_sent; topSender = d; }
    if (d.bytes_received > maxRecv) { maxRecv = d.bytes_received; topReceiver = d; }
  });

  document.getElementById('stat-top-sender').textContent = topSender ? topSender.name : '—';
  document.getElementById('stat-top-receiver').textContent = topReceiver ? topReceiver.name : '—';
}

function updateSelectedDeviceInfo() {
  if (!selectedDeviceId) return;
  const d = deviceMap[selectedDeviceId];
  if (!d) return;
  document.getElementById('d-sent').textContent = formatBytes(d.bytes_sent);
  document.getElementById('d-recv').textContent = formatBytes(d.bytes_received);
  document.getElementById('d-transfers').textContent = d.transfer_count || 0;
}

function appendLogEntry(ev) {
  const container = document.getElementById('log-entries');
  const div = document.createElement('div');
  div.className = 'entry';

  if (ev.special === 'reset') {
    div.innerHTML = `<div style="text-align:center; color:#9aa4b2">─── Stats Reset ───</div>`;
  } else {
    const ts = new Date(ev.timestamp).toLocaleTimeString();
    const kb = Math.round(ev.bytes / 1024);
    const from = deviceMap[ev.from_id];
    const to = deviceMap[ev.to_id];
    div.innerHTML = `<div><strong>[${ts}]</strong> <span class="muted">${ev.protocol}</span> &nbsp; <span>➡️</span> <strong>${kb} KB</strong></div>
                   <div class="muted">${from.name} → ${to.name}</div>`;
  }

  container.prepend(div);
  container.scrollTop = 0;
  while (container.children.length > 200) container.removeChild(container.lastChild);
}

function animateTransfer(fromId, toId, bytes) {
  if (!network) return;
  const positions = network.getPositions([fromId, toId]);
  const fromPos = positions[fromId];
  const toPos = positions[toId];
  if (!fromPos || !toPos) return;

  const fromDOM = network.canvasToDOM({ x: fromPos.x, y: fromPos.y });
  const toDOM = network.canvasToDOM({ x: toPos.x, y: toPos.y });

  const container = document.getElementById('network');
  const dot = document.createElement('div');
  dot.className = 'dot';
  dot.style.left = `${fromDOM.x}px`;
  dot.style.top = `${fromDOM.y}px`;
  container.appendChild(dot);

  const fromNode = nodesDS.get(fromId);
  const toNode = nodesDS.get(toId);
  nodesDS.update([{ id: fromId, color: { border: '#ffffff', background: '#ff9f43' }, size: (fromNode.size || 20) + 8 },
                  { id: toId, color: { border: '#ffffff', background: '#ff6b6b' }, size: (toNode.size || 20) + 8 }]);

  const duration = 1400;
  const start = performance.now();
  function easeInOut(t) { return t < 0.5 ? 2 * t * t : -1 + (4 - 2 * t) * t; }
  function step(now) {
    const t = Math.min(1, (now - start) / duration);
    const e = easeInOut(t);
    const curX = fromDOM.x + (toDOM.x - fromDOM.x) * e;
    const curY = fromDOM.y + (toDOM.y - fromDOM.y) * e;
    dot.style.left = `${curX}px`;
    dot.style.top = `${curY}px`;
    if (t < 1) requestAnimationFrame(step);
    else {
      dot.remove();
      nodesDS.update([{ id: fromId, color: { background: fromNode.color ? fromNode.color.background : undefined }, size: fromNode.size },
                      { id: toId, color: { background: toNode.color ? toNode.color.background : undefined }, size: toNode.size }]);
    }
  }
  requestAnimationFrame(step);
}

function showDeviceInfo(id) {
  const d = deviceMap[id];
  if (!d) return;
  const panel = document.getElementById('device-info');
  panel.querySelector('.empty').style.display = 'none';
  const details = panel.querySelector('.details');
  details.style.display = 'flex';
  document.getElementById('d-name').textContent = d.name;
  document.getElementById('d-type').textContent = d.device_type;
  document.getElementById('d-ip').textContent = `IP: ${d.ip_address}`;
  document.getElementById('d-mac').textContent = `MAC: ${d.mac_address}`;
  updateSelectedDeviceInfo();
}

function formatBytes(bytes) {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return Math.round(bytes / Math.pow(k, i) * 10) / 10 + ' ' + sizes[i];
}

window.__nv = { deviceMap, globalStats };
