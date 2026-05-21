const { app, BrowserWindow, Tray, Menu, ipcMain, nativeImage } = require('electron');
const path = require('path');
const http = require('http');

let mainWindow = null;
let tray = null;
let currentState = 'idle';
let stateServer = null;

const STATES = [
  'idle', 'thinking', 'working', 'done',
  'problem', 'study', 'tired', 'cheer',
  'rest', 'error', 'loading', 'bye'
];

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 320,
    height: 430,
    transparent: true,
    frame: false,
    alwaysOnTop: true,
    skipTaskbar: true,
    resizable: false,
    hasShadow: false,
    webPreferences: {
      nodeIntegration: true,
      contextIsolation: false
    }
  });

  mainWindow.loadFile('pet.html');
  mainWindow.setVisibleOnAllWorkspaces(true, { visibleOnFullScreen: true });

  // Prevent window from being captured in screenshots (optional)
  mainWindow.setContentProtection(true);

  mainWindow.on('close', () => {
    currentState = 'bye';
    mainWindow.webContents.send('state-change', 'bye');
    setTimeout(() => {
      if (mainWindow && !mainWindow.isDestroyed()) {
        mainWindow.destroy();
      }
    }, 800);
  });
}

function createTray() {
  // Use the idle sprite as tray icon (scaled down)
  const iconPath = path.join(__dirname, 'sprites', 'idle.png');
  const icon = nativeImage.createFromPath(iconPath).resize({ width: 16, height: 21 });
  tray = new Tray(icon);

  const contextMenu = Menu.buildFromTemplate([
    { label: '当前状态: ' + getStateLabel(currentState), enabled: false },
    { type: 'separator' },
    ...STATES.map(state => ({
      label: getStateLabel(state),
      type: 'radio',
      checked: currentState === state,
      click: () => setState(state)
    })),
    { type: 'separator' },
    {
      label: '锁定位置',
      type: 'checkbox',
      checked: false,
      click: (item) => {
        mainWindow.setMovable(!item.checked);
      }
    },
    {
      label: '退出桌宠',
      click: () => {
        clearTimeout(autoIdleTimer);
        app.quit();
      }
    }
  ]);

  tray.setToolTip('桌宠 - 陪你写代码');
  tray.setContextMenu(contextMenu);
  tray.on('double-click', () => {
    mainWindow.show();
    mainWindow.focus();
  });
}

function updateTrayMenu() {
  const contextMenu = Menu.buildFromTemplate([
    { label: '当前状态: ' + getStateLabel(currentState), enabled: false },
    { type: 'separator' },
    ...STATES.map(state => ({
      label: getStateLabel(state),
      type: 'radio',
      checked: currentState === state,
      click: () => setState(state)
    })),
    { type: 'separator' },
    {
      label: '退出桌宠',
      click: () => app.quit()
    }
  ]);
  tray.setContextMenu(contextMenu);
}

function setState(state) {
  if (!STATES.includes(state)) return;
  currentState = state;
  if (mainWindow && !mainWindow.isDestroyed()) {
    mainWindow.webContents.send('state-change', state);
  }
  updateTrayMenu();
}

function getStateLabel(state) {
  const labels = {
    idle: '空闲/待机',
    thinking: '思考中',
    working: '工作中',
    done: '完成啦',
    problem: '遇到问题',
    study: '学习中',
    tired: '有点累了',
    cheer: '加油',
    rest: '休息一下',
    error: '出错了',
    loading: '加载中',
    bye: '拜拜'
  };
  return labels[state] || state;
}

function startStateServer() {
  stateServer = http.createServer((req, res) => {
    // CORS headers
    res.setHeader('Access-Control-Allow-Origin', '*');
    res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
    res.setHeader('Access-Control-Allow-Headers', 'Content-Type');

    if (req.method === 'OPTIONS') {
      res.writeHead(200);
      res.end();
      return;
    }

    if (req.method === 'GET' && req.url === '/state') {
      res.writeHead(200, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ state: currentState, label: getStateLabel(currentState) }));
      return;
    }

    if (req.method === 'POST' && req.url === '/state') {
      let body = '';
      req.on('data', chunk => { body += chunk; });
      req.on('end', () => {
        try {
          const data = JSON.parse(body);
          if (data.state && STATES.includes(data.state)) {
            setState(data.state);
            res.writeHead(200, { 'Content-Type': 'application/json' });
            res.end(JSON.stringify({ success: true, state: currentState }));
          } else {
            res.writeHead(400, { 'Content-Type': 'application/json' });
            res.end(JSON.stringify({ success: false, error: 'Invalid state' }));
          }
        } catch (e) {
          res.writeHead(400, { 'Content-Type': 'application/json' });
          res.end(JSON.stringify({ success: false, error: 'Invalid JSON' }));
        }
      });
      return;
    }

    res.writeHead(200, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({
      pet: '桌宠',
      states: STATES,
      current: currentState,
      usage: 'POST /state { "state": "' + currentState + '" }'
    }));
  });

  stateServer.listen(9527, '127.0.0.1', () => {
    console.log('桌宠状态服务已启动: http://127.0.0.1:9527');
  });
}

// IPC handlers
ipcMain.handle('get-states', () => {
  return STATES.map(s => ({ key: s, label: getStateLabel(s) }));
});

ipcMain.handle('get-current-state', () => currentState);

// Quit handler from renderer
ipcMain.on('quit-app', () => {
  clearTimeout(autoIdleTimer);
  app.quit();
});

// Auto-idle timer: switch back to idle after period of no activity
let autoIdleTimer = null;
ipcMain.on('reset-auto-idle', () => {
  clearTimeout(autoIdleTimer);
  // Don't auto-idle from 'done' state as quickly — let user see it
  if (currentState === 'done' || currentState === 'cheer') {
    autoIdleTimer = setTimeout(() => {
      if (currentState === 'done' || currentState === 'cheer') {
        setState('idle');
      }
    }, 5000);
  }
});

app.whenReady().then(() => {
  createWindow();
  createTray();
  startStateServer();
});

app.on('window-all-closed', () => {
  // Don't quit on window close — keep running in tray
});

app.on('before-quit', () => {
  if (stateServer) stateServer.close();
});

app.on('activate', () => {
  if (mainWindow && !mainWindow.isDestroyed()) {
    mainWindow.show();
  }
});
