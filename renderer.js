const { ipcRenderer } = require('electron');

const container = document.getElementById('pet-container');
const sprite = document.getElementById('pet-sprite');
const contextMenu = document.getElementById('context-menu');

let currentState = 'idle';
let autoIdleTimer = null;

// States that auto-transition back to idle after a delay
const AUTO_IDLE_STATES = {
  done: 5000,
  cheer: 4000,
  problem: 8000,
  error: 6000,
  bye: 1500
};

function setState(state) {
  if (state === currentState) return;

  // Remove old state class
  container.classList.remove('state-' + currentState);

  // Update sprite
  sprite.src = 'sprites/' + state + '.png';

  // Add transition animation for non-idle states
  if (state !== currentState) {
    sprite.classList.remove('state-transition');
    void sprite.offsetWidth; // Force reflow
    sprite.classList.add('state-transition');
  }

  // Add new state class
  container.classList.add('state-' + state);
  currentState = state;

  // Auto-idle timer
  clearTimeout(autoIdleTimer);
  if (AUTO_IDLE_STATES[state]) {
    autoIdleTimer = setTimeout(() => {
      setState('idle');
      ipcRenderer.send('reset-auto-idle');
    }, AUTO_IDLE_STATES[state]);
  }

  // Notify main process
  ipcRenderer.send('reset-auto-idle');
}

// Listen for state changes from main process (HTTP API)
ipcRenderer.on('state-change', (event, state) => {
  setState(state);
});

// Context menu
document.addEventListener('contextmenu', (e) => {
  e.preventDefault();
  showContextMenu(e.clientX, e.clientY);
});

document.addEventListener('click', () => {
  contextMenu.style.display = 'none';
});

function showContextMenu(x, y) {
  // Highlight current state
  document.querySelectorAll('.menu-state').forEach(item => {
    if (item.dataset.state === currentState) {
      item.classList.add('current');
    } else {
      item.classList.remove('current');
    }
  });

  contextMenu.style.display = 'block';
  contextMenu.style.left = x + 'px';
  contextMenu.style.top = y + 'px';

  // Ensure menu stays within window bounds
  const rect = contextMenu.getBoundingClientRect();
  if (rect.right > window.screen.width) {
    contextMenu.style.left = (x - rect.width) + 'px';
  }
  if (rect.bottom > window.screen.height) {
    contextMenu.style.top = (y - rect.height) + 'px';
  }
}

// Menu click handlers
contextMenu.addEventListener('click', (e) => {
  const item = e.target;
  if (item.classList.contains('menu-state')) {
    const state = item.dataset.state;
    // Send state change via HTTP to self
    fetch('http://127.0.0.1:9527/state', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ state })
    }).catch(() => {});
  }
  if (item.id === 'menu-quit') {
    ipcRenderer.send('quit-app');
  }
});

// Initial state: loading, then idle
setState('loading');
setTimeout(() => setState('idle'), 1500);
