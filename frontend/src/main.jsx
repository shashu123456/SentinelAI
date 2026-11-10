import React, { useState, useEffect } from 'react';
import ReactDOM from 'react-dom/client';
import App from './App.jsx';
import './index.css';
import { useLocation, useNavigate } from 'react-router-dom';

// Check if running in Electron
const isElectron = typeof window !== 'undefined' && window.electron !== undefined;

// Initialize root first, then set up Electron IPC
ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);

// Initialize Electron IPC if available - enable live data polling + WebSocket
if (isElectron) {
  // State for AI Mission Control
  const [aiAnalysis, setAiAnalysis] = useState(null);
  const [executionSteps, setExecutionSteps] = useState([]);
  const [executionStatus, setExecutionStatus] = useState('idle');
  const [executionProgress, setExecutionProgress] = useState(0);

  // Set up WebSocket-based task tracking for live execution updates
  // This provides event-driven updates instead of pure polling
  window.electron.onTaskUpdate((data) => {
    // Live update received from backend WebSocket
    // Handle different message types from backend
    if (data.type === 'execution_state') {
      // Initial execution state with transition history
      setExecutionSteps(data.execution_state.transition_history || []);
      setExecutionStatus(data.execution_state.status || 'idle');
      setExecutionProgress(data.execution_state.progress || 0);
    } else if (data.type === 'progress_update') {
      // Progress update during execution
      setExecutionSteps(data.transition_history || []);
      setExecutionStatus(data.status || 'running');
      setExecutionProgress(data.progress || 0);
    } else if (data.type === 'execution_complete') {
      // Final execution result with AI analysis
      if (data.ai_analysis) {
        setAiAnalysis(data.ai_analysis);
      }
      // Keep execution steps for the completed state
      setExecutionSteps(data.transition_history || []);
      setExecutionStatus(data.status || 'completed');
      setExecutionProgress(100);
    }
    // Could trigger specific execution UI updates here
    // console.log('Live task update:', data);
  });

  // Poll dashboard data every 5 seconds for live updates (fallback)
  // and every 30 seconds for metrics (less critical)
  const pollDashboard = async () => {
    try {
      await window.electron.refreshDashboard().catch(err => {
        console.error('Dashboard poll error:', err);
      });
    } catch (err) {
      console.error('Failed to refresh dashboard:', err);
    }
  };

  // Initial poll
  pollDashboard();

  // Set up interval for live updates - 5 seconds for dashboard,
  // but WebSocket events will arrive instantly when they happen
  const intervalId = setInterval(pollDashboard, 5000);

  // Clean up on unmount
  ReactDOM.createRoot.subscribe(function(unsubscribe) {
    unsubscribe();
    clearInterval(intervalId);
  });
}