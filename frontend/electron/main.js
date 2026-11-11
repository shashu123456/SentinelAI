const { app, BrowserWindow, ipcMain } = require('electron');
const path = require('path');
const { URL } = require('url');

// Handle creating/removing shortcuts on Windows when uninstalling
if (require('electron-squirrel-startup')) { // eslint-disable-line no-unused-vars
  app.quit();
}

// Set application user model id for Windows
app.setAppUserModelId('com.sentinelai.desktop');

// Global state
const windows = new Set();

const createWindow = () => {
  // Create the browser window.
  const mainWindow = new BrowserWindow({
    width: 1400,
    height: 900,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      nodeIntegration: false,
      contextIsolation: true,
    },
  });

  windows.add(mainWindow);

  // and load the index.html of the app
  mainWindow.loadFile(path.join(__dirname, '../index.html')).catch(err => {
    console.error('Failed to load index.html:', err);
  });

  mainWindow.on('closed', () => {
    windows.delete(mainWindow);
  });
};

// Track active WebSocket connections
const taskSubscribers = new Map(); // task_id -> Set of websockets

app.whenReady().then(() => {
  createWindow();

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow();
    }
  });
});

// Quit when all windows are closed (except on macOS)
app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

// IPC Handler: Get execution state (from backend scans dashboard data)
ipcMain.handle('get-execution-state', async (event) => {
  try {
    const response = await fetch('http://localhost:8000/api/scans/dashboard', {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    });
    if (!response.ok) throw new Error('Failed to fetch execution state');
    const data = await response.json();
    // Transform dashboard data to execution state format
    return {
      executions: data.recent_scans || [],
      total: data.total_scans || 0,
      completed: data.total_vulnerabilities || 0,
      running: 0,  // Will be populated separately if needed
      failed: 0,
    };
  } catch (err) {
    console.error('Failed to get execution state:', err);
    return { error: 'Failed to retrieve execution state', executions: [], total: 0, completed: 0, running: 0, failed: 0 };
  }
});

// IPC Handler: Get metrics snapshot (from backend system metrics)
ipcMain.handle('get-metrics-snapshot', async (event) => {
  try {
    // Fetch health which includes system metrics
    const healthResp = await fetch('http://localhost:8000/api/health', {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    });
    const metricsResp = await fetch('http://localhost:8000/api/v1/metrics', {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    });
    
    if (!healthResp.ok) throw new Error('Failed to fetch health');
    
    const health = await healthResp.json();
    const metrics = metricsResp.ok ? await metricsResp.json() : {};
    
    // Combine health and metrics data
    return {
      status: health.status || 'unknown',
      cpu: metrics.cpu || health.checks?.cpu || {},
      memory: metrics.memory || health.details?.memory || {},
      disk: metrics.disk || health.details?.disk || {},
      database: metrics.database || health.details?.database || {},
      redis: metrics.redis || health.details?.redis || {},
      environment: metrics.environment || health.details?.environment || {},
      uptime: health.uptime_human || '—',
      version: health.version || '1.0.0',
    };
  } catch (err) {
    console.error('Failed to get metrics snapshot:', err);
    return { error: 'Failed to retrieve metrics snapshot', status: 'unknown', cpu: {}, memory: {}, disk: {}, database: {}, redis: {}, environment: {}, uptime: '—', version: '1.0.0' };
  }
});

// IPC Handler: List active executions (from backend active scans)
ipcMain.handle('list-active-executions', async (event) => {
  try {
    const response = await fetch('http://localhost:8000/api/scans/', {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    });
    if (!response.ok) throw new Error('Failed to list active executions');
    const scans = await response.json();
    // Filter for active/running scans
    const active = (scans || []).filter(scan => scan.status === 'running' || scan.status === 'pending');
    return active;
  } catch (err) {
    console.error('Failed to list active executions:', err);
    return [];
  }
});

// IPC Handler: Refresh dashboard data (combines health, executions, metrics)
ipcMain.handle('refresh-dashboard', async (event) => {
  try {
    const [healthResp, scansResp, metricsResp] = await Promise.all([
      fetch('http://localhost:8000/api/health', {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
      }),
      fetch('http://localhost:8000/api/scans/dashboard', {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
      }),
      fetch('http://localhost:8000/api/v1/metrics', {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
      }),
    ]);

    const health = await healthResp.json().catch(() => ({ status: 'unknown', checks: {}, details: {} }));
    const scans = await scansResp.json().catch(() => ({ recent_scans: [], total_scans: 0, severity_distribution: {} }));
    const metrics = await metricsResp.json().catch(() => ({}));

    // Transform scans data into execution format
    const executionData = {
      executions: (scans.recent_scans || []).map(scan => ({
        id: scan.id,
        name: scan.api_name || 'Unknown',
        status: scan.status || 'pending',
        progress: scan.progress || 0,
        startedAt: scan.created_at,
        completedAt: scan.completed_at,
        findings: scan.total_vulnerabilities || 0,
      })),
      total: scans.total_scans || 0,
      completed: 0,
      running: 0,
      failed: 0,
    };

    // Count statuses from all scans
    const allScans = await (await fetch('http://localhost:8000/api/scans/', {
      method: 'GET',
      headers: { 'Content-Type': 'application/json' },
    })).json()).catch(() => []);

    const statusCounts = { completed: 0, running: 0, failed: 0, pending: 0 };
    (allScans || []).forEach(scan => {
      const status = scan.status || 'pending';
      if (statusCounts[status] !== undefined) statusCounts[status]++;
    });

    return {
      health,
      executions: executionData.executions,
      total: executionData.total,
      completed: statusCounts.completed || 0,
      running: statusCounts.running || 0,
      failed: statusCounts.failed || 0,
      metrics,
    };
  } catch (err) {
    console.error('Failed to refresh dashboard:', err);
    return { error: 'Failed to refresh dashboard data', health: { status: 'unknown' }, executions: [], total: 0, completed: 0, running: 0, failed: 0, metrics: {} };
  }
});

// IPC Handler: Check health (simple health check)
ipcMain.handle('check-health', async (event) => {
  try {
    const response = await fetch('http://localhost:8000/api/health', {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    });
    if (!response.ok) throw new Error('Health check failed');
    const data = await response.json();
    return { status: data.status || 'unknown', version: data.version || '1.0.0' };
  } catch (err) {
    console.error('Failed to check health:', err);
    return { error: 'Health check failed', status: 'unhealthy' };
  }
});

// ── WebSocket Management ──────────────────────────────────────────────

/**
 * Handle WebSocket connections from the renderer process
 * Connect to backend WebSocket and forward messages
 */
function handleRendererWebSocket(webSocket, params) {
  const { taskId } = params;
  const backendWsUrl = `ws://localhost:8000/ws/scan/${taskId}`;
  
  const backendWs = new (require('ws'))(backendWsUrl, {
    headers: {
      // No special auth needed - the backend handles auth
    }
  });

  backendWs.on('open', () => {
    console.log(`Backend WebSocket connected for task ${taskId}`);
  });

  backendWs.on('message', (data) => {
    try {
      const message = JSON.parse(data);
      // Forward to all renderer windows - include AI analysis data for timeline
      mainWindow.webContents.send('task-update', message);
    } catch (e) {
      console.error('Failed to parse WebSocket message:', e);
    }
  });

  backendWs.on('close', () => {
    console.log(`Backend WebSocket closed for task ${taskId}`);
    // Clean up
    if (taskSubscribers.has(taskId)) {
      taskSubscribers.delete(taskId);
    }
    // Close our frontend WebSocket
    webSocket.close();
  });

  backendWs.on('error', (error) => {
    console.error(`WebSocket error for task ${taskId}:`, error);
    webSocket.close();
  });

  // Handle messages from the renderer (e.g., close request)
  webSocket.on('message', (data) => {
    if (typeof data === 'string' && data.startsWith('close-task:')) {
      const closeTaskId = data.split(':')[1];
      if (closeTaskId === taskId && backendWs.readyState === backendWs.OPEN) {
        backendWs.close();
      }
    }
  });
}

// When a renderer connects via IPC, set up WebSocket forwarding
ipcMain.on('connect-task-ws', (event, taskId) => {
  const mainWindow = BrowserWindow.getFocusedWindow();
  if (!mainWindow) return;
  
  const webSocket = new (require('ws'))();
  
  // Forward messages from our frontend WebSocket to the backend
  webSocket.on('message', (data) => {
    // Handle frontend WebSocket messages
  });
  
  // Set up backend WebSocket connection
  handleRendererWebSocket(webSocket, { taskId });
  
  // Track this connection
  if (!taskSubscribers.has(taskId)) {
    taskSubscribers.set(taskId, new Set());
  }
  taskSubscribers.get(taskId).add(webSocket);
  
  // Clean up when renderer disconnects
  webSocket.on('close', () => {
    taskSubscribers.get(taskId)?.delete(webSocket);
    if (taskSubscribers.get(taskId)?.size === 0) {
      taskSubscribers.delete(taskId);
    }
  });
});