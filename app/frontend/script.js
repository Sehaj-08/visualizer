// Frontend script for Hotspot Network Visualizer — Version 2
// Responsibilities:
// - Fetch /devices and render Vis.js network
// - Maintain a local map of device stats
// - Connect to /ws and handle transfer_event messages
// - Animate transfers with smooth moving dot and node highlights
// - Show detailed device info when a node is clicked

let network = null;
let nodesDS = null;
let edgesDS = null;
let deviceMap = {}; // id -> device object (includes stats)

const reconnect = { attempt: 0 };

window.addEventListener('DOMContentLoaded', async () => {
  const devices = await fetchDevices();
  buildNetwork(devices);
  setupInteractions();
  connectWebSocket();
});

async function fetchDevices() {
  const res = await fetch('/devices');
  if (!res.ok) throw new Error('Failed to fetch /devices');
  const list = await res.json();
  // populate deviceMap
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

  // Star topology: router at center
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
      showDeviceInfo(id);
      // visually highlight
      nodesDS.update({ id, borderWidth: 3, color: { border: '#fff' } });
      setTimeout(() => nodesDS.update({ id, borderWidth: 0 }), 1400);
    }
  });

}

function setupInteractions(){
  // nothing fancy for now - click handled in buildNetwork
}

function connectWebSocket(){
  const url = (location.protocol === 'https:' ? 'wss://' : 'ws://') + location.host + '/ws';
  const ws = new WebSocket(url);

  ws.addEventListener('open', () => {
    console.log('WS open');
    reconnect.attempt = 0;
    showStatus('Connected');
  });

  ws.addEventListener('message', ev => {
    try{
      const msg = JSON.parse(ev.data);
      if (msg.type === 'transfer_event') handleTransferEvent(msg);
    }catch(err){
      console.error('WS parse', err);
    }
  });

  ws.addEventListener('close', () => {
    console.log('WS closed');
    showStatus('Disconnected — reconnecting...');
    // exponential backoff
    reconnect.attempt += 1;
    const delay = Math.min(30000, 1000 * Math.pow(1.8, reconnect.attempt));
    setTimeout(connectWebSocket, delay);
  });

  ws.addEventListener('error', () => ws.close());
}

function showStatus(text){
  // optionally show status in UI (not implemented UI element for brevity)
  console.log(text);
}

function handleTransferEvent(ev){
  // update local deviceMap stats with authoritative backend numbers
  if (ev.from_stats) {
    deviceMap[ev.from_id].bytes_sent = ev.from_stats.bytes_sent;
    deviceMap[ev.from_id].bytes_received = ev.from_stats.bytes_received;
  }
  if (ev.to_stats) {
    deviceMap[ev.to_id].bytes_sent = ev.to_stats.bytes_sent;
    deviceMap[ev.to_id].bytes_received = ev.to_stats.bytes_received;
  }

  // update details panel if showing either device
  const selected = document.querySelector('.device-info .details');
  if (selected && selected.style.display !== 'none'){
    const dname = document.getElementById('d-name').textContent;
    // find id by name (simple) — better: track selected id globally (omitted for brevity)
  }

  appendLogEntry(ev);
  animateTransfer(ev.from_id, ev.to_id, ev.bytes);
}

function appendLogEntry(ev){
  const container = document.getElementById('log-entries');
  const ts = new Date(ev.timestamp).toLocaleTimeString();
  const kb = Math.round(ev.bytes / 1024);
  const from = deviceMap[ev.from_id];
  const to = deviceMap[ev.to_id];

  const div = document.createElement('div');
  div.className = 'entry';
  div.innerHTML = `<div><strong>[${ts}]</strong> <span class="muted">${ev.protocol}</span> &nbsp; <span>➡️</span> <strong>${kb} KB</strong></div>
                   <div class="muted">${from.name} → ${to.name}</div>`;
  container.prepend(div);
  // auto-scroll: keep newest visible at top by ensuring container scrollTop = 0
  container.scrollTop = 0;
  // cap entries
  while (container.children.length > 200) container.removeChild(container.lastChild);
}

function animateTransfer(fromId, toId, bytes){
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

  // highlight nodes
  const fromNode = nodesDS.get(fromId);
  const toNode = nodesDS.get(toId);
  nodesDS.update([{ id: fromId, color: { border: '#ffffff', background: '#ff9f43' }, size: (fromNode.size || 20) + 8 },
                  { id: toId, color: { border: '#ffffff', background: '#ff6b6b' }, size: (toNode.size || 20) + 8 }]);

  const duration = 1400; // ms — slightly longer so movement is visible
  const start = performance.now();

  function easeInOut(t){ return t<0.5 ? 2*t*t : -1+(4-2*t)*t }

  function step(now){
    const t = Math.min(1, (now - start) / duration);
    const e = easeInOut(t);
    const curX = fromDOM.x + (toDOM.x - fromDOM.x) * e;
    const curY = fromDOM.y + (toDOM.y - fromDOM.y) * e;
    dot.style.left = `${curX}px`;
    dot.style.top = `${curY}px`;
    if (t < 1) requestAnimationFrame(step);
    else {
      dot.remove();
      // revert node styles
      nodesDS.update([{ id: fromId, color: { background: fromNode.color ? fromNode.color.background : undefined }, size: fromNode.size },
                      { id: toId, color: { background: toNode.color ? toNode.color.background : undefined }, size: toNode.size }]);
    }
  }
  requestAnimationFrame(step);
}

function showDeviceInfo(id){
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
  document.getElementById('d-sent').textContent = d.bytes_sent || 0;
  document.getElementById('d-recv').textContent = d.bytes_received || 0;
}

// Expose for debugging
window.__nv = { deviceMap };
