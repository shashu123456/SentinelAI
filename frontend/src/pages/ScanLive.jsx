import { useState, useEffect, useRef } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { scans } from '../services/api';
import { ArrowLeft, Terminal, CheckCircle2, XCircle, Loader2 } from 'lucide-react';
import './ScanLive.css';

const API_HOST = 'sentinelai-backend-3lru.onrender.com';
const WS_BASE = 'wss:';
const WS_HOST = API_HOST;

export default function ScanLive() {
  const { taskId } = useParams();
  const navigate = useNavigate();
  const [logs, setLogs] = useState([]);
  const [progress, setProgress] = useState(0);
  const [status, setStatus] = useState('connecting');
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const terminalRef = useRef(null);
  const wsRef = useRef(null);
  const statusRef = useRef('connecting');

  useEffect(() => {
    if (!taskId) return;

    const wsUrl = `${WS_BASE}//${WS_HOST}/ws/scan/${taskId}`;
    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => {
      addLog('system', 'Connected to scan engine');
      setStatus('running');
      statusRef.current = 'running';
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        setProgress(data.progress || 0);
        setStatus(data.status);
        statusRef.current = data.status;

        if (data.message) {
          const msg = data.message;
          if (msg.includes('[CRITICAL]')) addLog('critical', msg);
          else if (msg.includes('[HIGH]')) addLog('high', msg);
          else if (msg.includes('[MEDIUM]')) addLog('medium', msg);
          else if (msg.includes('[LOW]')) addLog('low', msg);
          else if (msg.includes('[INFO]')) addLog('info', msg);
          else if (msg.includes('Risk Score:')) addLog('risk', msg);
          else if (msg.includes('Scan complete:')) addLog('success', msg);
          else if (msg.startsWith('  [API') || msg.includes('Security schemes:')) addLog('check', msg);
          else if (msg.startsWith('  [GET]') || msg.startsWith('  [POST]') || msg.startsWith('  [PUT]') || msg.startsWith('  [DELETE]') || msg.startsWith('  [PATCH]')) addLog('endpoint', msg);
          else addLog('scan', msg);
        }

        if (data.status === 'completed' && data.scan_id) {
          addLog('success', `Scan completed. Scan ID: #${data.scan_id}`);
          setResult(data);
        }

        if (data.status === 'failed') {
          addLog('error', `Scan failed: ${data.error || 'Unknown error'}`);
          setError(data.error);
        }
      } catch (e) {
        addLog('error', 'Failed to parse server message');
      }
    };

    ws.onerror = () => {
      addLog('error', 'WebSocket connection error');
      setStatus('error');
      statusRef.current = 'error';
    };

    ws.onclose = () => {
      if (statusRef.current === 'running' || statusRef.current === 'connecting') {
        addLog('system', 'Connection closed');
      }
    };

    return () => {
      ws.close();
    };
  }, [taskId]);

  useEffect(() => {
    if (terminalRef.current) {
      terminalRef.current.scrollTop = terminalRef.current.scrollHeight;
    }
  }, [logs]);

  const addLog = (type, message) => {
    const timestamp = new Date().toLocaleTimeString('en-US', { hour12: false });
    setLogs(prev => [...prev, { type, message, timestamp, id: Date.now() + Math.random() }]);
  };

  const handleViewResults = () => {
    if (result?.scan_id) {
      navigate(`/scan/${result.scan_id}`);
    }
  };

  return (
    <div className="scanlive-page">
      <div className="scanlive-header">
        <Link to="/dashboard" className="back-link">
          <ArrowLeft size={16} /> Dashboard
        </Link>
        <div className="scanlive-title">
          <Terminal size={20} />
          <h1>Live Scan</h1>
          <span className={`status-badge ${status}`}>
            {status === 'connecting' && <><Loader2 size={12} className="spin" /> Connecting</>}
            {status === 'queued' && <><Loader2 size={12} className="spin" /> Queued</>}
            {status === 'running' && <><Loader2 size={12} className="spin" /> Running</>}
            {status === 'completed' && <><CheckCircle2 size={12} /> Complete</>}
            {status === 'failed' && <><XCircle size={12} /> Failed</>}
          </span>
        </div>
      </div>

      <div className="scanlive-content">
        <div className="progress-section">
          <div className="progress-bar-container">
            <div className="progress-bar" style={{ width: `${progress}%` }}></div>
          </div>
          <span className="progress-text">{progress}%</span>
        </div>

        <div className="terminal" ref={terminalRef}>
          <div className="terminal-header">
            <div className="terminal-dots">
              <span className="dot red"></span>
              <span className="dot yellow"></span>
              <span className="dot green"></span>
            </div>
            <span className="terminal-title">sentinelai@scanner ~ #{taskId?.slice(0, 8)}</span>
          </div>
          <div className="terminal-body">
            <div className="terminal-line system">
              <span className="line-prefix"> </span>
              ┌──────────────────────────────────────────────────────┐
            </div>
            <div className="terminal-line system">
              <span className="line-prefix"> </span>
              │   ███████╗███████╗██╗███╗   ██╗███████╗            │
            </div>
            <div className="terminal-line system">
              <span className="line-prefix"> </span>
              │   ██╔════╝██╔════╝██║████╗  ██║██╔════╝            │
            </div>
            <div className="terminal-line system">
              <span className="line-prefix"> </span>
              │   ███████╗█████╗  ██║██╔██╗ ██║███████╗            │
            </div>
            <div className="terminal-line system">
              <span className="line-prefix"> </span>
              │   ╚════██║██╔══╝  ██║██║╚██╗██║╚════██║            │
            </div>
            <div className="terminal-line system">
              <span className="line-prefix"> </span>
              │   ███████║███████╗██║██║ ╚████║███████║            │
            </div>
            <div className="terminal-line system">
              <span className="line-prefix"> </span>
              │   ╚══════╝╚══════╝╚═╝╚═╝  ╚═══╝╚══════╝            │
            </div>
            <div className="terminal-line system">
              <span className="line-prefix"> </span>
              │         API Security Scanner v1.0                    │
            </div>
            <div className="terminal-line system">
              <span className="line-prefix"> </span>
              └──────────────────────────────────────────────────────┘
            </div>
            <div className="terminal-line system">{'─'.repeat(62)}</div>
            <div className="terminal-line system">
              <span className="line-prefix">$</span>
              sentinelai scan --realtime --task {taskId?.slice(0, 8)}
            </div>
            <div className="terminal-line system">
              <span className="line-prefix">*</span>
              OWASP API Security Top 10 Engine v2.0
            </div>
            <div className="terminal-line system">{'─'.repeat(62)}</div>

            {logs.map((log) => (
              <div key={log.id} className={`terminal-line ${log.type}`}>
                <span className="line-time">{log.timestamp}</span>
                <span className="line-prefix">
                  {log.type === 'scan' && '▸'}
                  {log.type === 'success' && '✓'}
                  {log.type === 'error' && '✗'}
                  {log.type === 'system' && '*'}
                  {log.type === 'endpoint' && '→'}
                  {log.type === 'check' && '▸'}
                  {log.type === 'critical' && '✗'}
                  {log.type === 'high' && '▲'}
                  {log.type === 'medium' && '●'}
                  {log.type === 'low' && '○'}
                  {log.type === 'info' && '·'}
                  {log.type === 'risk' && '='}
                </span>
                <span className="line-message">{log.message}</span>
              </div>
            ))}

            {status === 'running' && (
              <div className="terminal-line cursor">
                <span className="line-prefix">&gt;</span>
                <span className="cursor-blink">_</span>
              </div>
            )}
          </div>
        </div>

        {status === 'completed' && result && (
          <div className="scanlive-result">
            <div className="result-summary-bar">
              <span className="result-item">
                Scan ID: <strong>#{result.scan_id}</strong>
              </span>
              <span className="result-item">
                Endpoints: <strong>{result.total_endpoints || 'N/A'}</strong>
              </span>
              <span className="result-item">
                Vulnerabilities: <strong className={result.total_vulnerabilities > 0 ? 'has-vulns' : ''}>{result.total_vulnerabilities}</strong>
              </span>
              <span className="result-item">
                Risk Score: <strong className={`risk-text ${getRiskClass(result.risk_score)}`}>{result.risk_score}/100</strong>
              </span>
              <span className="result-item">
                Level: <strong className={`risk-text ${getRiskClass(result.risk_score)}`}>{result.risk_level}</strong>
              </span>
            </div>
            <button className="btn-view-results" onClick={handleViewResults}>
              View Full Results
            </button>
          </div>
        )}

        {status === 'failed' && (
          <div className="scanlive-error">
            <XCircle size={20} />
            <span>Scan failed: {error || 'Unknown error'}</span>
            <Link to="/new-scan" className="btn-retry">Try Again</Link>
          </div>
        )}
      </div>
    </div>
  );
}

function getRiskClass(score) {
  if (score >= 80) return 'critical';
  if (score >= 60) return 'high';
  if (score >= 30) return 'medium';
  return 'low';
}
