window.electron = {
  // Execution state
  getExecutionState: () => window.ipcRenderer.invoke('get-execution-state'),
  getMetricsSnapshot: () => window.ipcRenderer.invoke('get-metrics-snapshot'),
  listActiveExecutions: () => window.ipcRenderer.invoke('list-active-executions'),
  refreshDashboard: () => window.ipcRenderer.invoke('refresh-dashboard'),
  checkHealth: () => window.ipcRenderer.invoke('check-health'),
  
  // WebSocket task tracking
  connectTaskWS: (taskId) => {
    window.ipcRenderer.send('connect-task-ws', taskId);
  },onTaskUpdate: (callback) => {
    window.ipcRenderer.on('task-update', (event, data) => callback(data));
  },
  disconnectTaskWS: (taskId) => {
    window.ipcRenderer.send('disconnect-task-ws', taskId);
  },

  // Lifecycle events
  onExecutionUpdate: (callback) => {
    window.ipcRenderer.on('execution-update', (event, data) => callback(data));
  },
  onMetricsUpdate: (callback) => {
    window.ipcRenderer.on('metrics-update', (event, data) => callback(data));
  },
  onAiAnalysisUpdate: (callback) => {
    window.ipcRenderer.on('ai-analysis-update', (event, data) => callback(data));
  }
};