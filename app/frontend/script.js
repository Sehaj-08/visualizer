// Frontend script for Hotspot Network Visualizer (Version 1)
// - Fetch /devices to build the network
// - Connect to WebSocket /ws to receive transfer_event messages
// - Animate a moving dot along the line between nodes on each event

let network = null;
let nodesDS = null;
let edgesDS = null;

window.addEventListener('DOMContentLoaded', async () => {
  const devices = await fetchDevices();
  buildNetwork(devices);
  setupWebSocket();
});

async function fetchDevices() {
  const res = await fetch('/devices');
  if (!res.ok) throw new Error('Failed to fetch /devices');
  return res.json();
}

function buildNetwork(devices) {
  const container = document.getElementById('network');

  const nodes = devices.map(d => ({
    id: d.id,
    label: `${d.name}\n${d.ip_address}`,
    title: `${d.device_type} — ${d.mac_address}`,
    color: d.device_type === 'router' ? '#ffcc00' : '#97c2fc',
    shape: d.device_type === 'router' ? 'star' : 'dot',
    size: d.device_type === 'router' ? 30 : 18
  }));

  // Star topology: connect router to each non-router
  const router = devices.find(d => d.device_type === 'router') || devices[0];
  const edges = devices
    .filter(d => d.id !== router.id)
    .map(d => ({ from: router.id, to: d.id, color: { color: '#cfcfcf' } }));

  nodesDS = new vis.DataSet(nodes);
  edgesDS = new vis.DataSet(edges);

  const data = { nodes: nodesDS, edges: edgesDS };
  const options = {
    physics: { stabilization: true },
    edges: { smooth: { type: 'cubicBezier' }, arrows: { to: false } },
    nodes: { font: { multi: 'html' } }
  };

  network = new vis.Network(container, data, options);
}

function setupWebSocket() {
  const wsUrl = (location.protocol === 'https:' ? 'wss://' : 'ws://') + location.host + '/ws';
  const ws = new WebSocket(wsUrl);

  ws.addEventListener('open', () => console.log('WebSocket connected'));
  ws.addEventListener('message', ev => {
    try {
      const msg = JSON.parse(ev.data);
      if (msg.type === 'transfer_event') {
        handleTransferEvent(msg);
      }
    } catch (err) {
      console.error('Invalid WS message', err);
    }
  });

  ws.addEventListener('close', () => console.log('WebSocket closed'));
}

function handleTransferEvent(ev) {
  // Lookup device labels for the log
  const fromNode = nodesDS.get(ev.from_id);
  const toNode = nodesDS.get(ev.to_id);
  appendLogEntry(ev, fromNode, toNode);
  animateTransfer(ev.from_id, ev.to_id);
}

function appendLogEntry(ev, fromNode, toNode) {
  const log = document.getElementById('log');
  const ts = new Date(ev.timestamp).toLocaleTimeString();
  const kb = Math.round(ev.bytes / 1024);
  const entry = document.createElement('div');
  entry.className = 'log-entry';
  entry.textContent = `[${ts}] ${kb} KB from ${fromNode.label.split('\n')[0]} (${fromNode.label.split('\n')[1]}) → ${toNode.label.split('\n')[0]} (${toNode.label.split('\n')[1]}) via ${ev.protocol}`;
  log.prepend(entry);
  // Keep recent 100 entries
  while (log.children.length > 100) log.removeChild(log.lastChild);
}

function animateTransfer(fromId, toId) {
  if (!network) return;

  const positions = network.getPositions([fromId, toId]);
  const fromPos = positions[fromId];
  const toPos = positions[toId];

  // Convert canvas coordinates to DOM coordinates (vis Network helper)
  const fromDOM = network.canvasToDOM({ x: fromPos.x, y: fromPos.y });
  const toDOM = network.canvasToDOM({ x: toPos.x, y: toPos.y });

  const container = document.getElementById('network');

  const dot = document.createElement('div');
  dot.className = 'dot';
  dot.style.left = `${fromDOM.x}px`;
  dot.style.top = `${fromDOM.y}px`;
  container.appendChild(dot);

  // Temporarily highlight the edge and nodes
  highlightNodesAndEdge(fromId, toId);

  const duration = 900; // ms
  const start = performance.now();

  function step(now) {
    const t = Math.min(1, (now - start) / duration);
    const ease = t < 0.5 ? 2 * t * t : -1 + (4 - 2 * t) * t; // easeInOut
    const curX = fromDOM.x + (toDOM.x - fromDOM.x) * ease;
    const curY = fromDOM.y + (toDOM.y - fromDOM.y) * ease;
    dot.style.left = `${curX}px`;
    dot.style.top = `${curY}px`;

    if (t < 1) {
      requestAnimationFrame(step);
    } else {
      dot.remove();
    }
  }
  requestAnimationFrame(step);
}

function highlightNodesAndEdge(fromId, toId) {
  // enlarge / recolor nodes briefly
  const fromNode = nodesDS.get(fromId);
  const toNode = nodesDS.get(toId);

  nodesDS.update([{ id: fromId, color: { background: '#ff9f43' }, size: (fromNode.size || 18) + 6 },
                  { id: toId, color: { background: '#ff6b6b' }, size: (toNode.size || 18) + 6 }]);

  // Optionally update edge appearance for the path if edge exists
  // For star topology we have edges from router to each device; we try to find an edge between these nodes
  const edges = edgesDS.get();
  const edgeToHighlight = edges.find(e => (e.from === fromId && e.to === toId) || (e.from === toId && e.to === fromId));
  let originalEdge = null;
  if (edgeToHighlight) {
    originalEdge = { id: edgeToHighlight.id, color: edgeToHighlight.color };
    edgesDS.update([{ id: edgeToHighlight.id, color: { color: '#ff7b00' }, width: 3 }]);
  }

  // Revert after a short delay
  setTimeout(() => {
    nodesDS.update([{ id: fromId, color: { background: fromNode.color ? fromNode.color.background : undefined }, size: fromNode.size },
                    { id: toId, color: { background: toNode.color ? toNode.color.background : undefined }, size: toNode.size }]);
    if (edgeToHighlight && originalEdge) {
      edgesDS.update([{ id: originalEdge.id, color: originalEdge.color || { color: '#cfcfcf' }, width: 1 }]);
    }
  }, 1000);
}
