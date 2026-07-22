import { useState, useEffect, useRef, useCallback } from 'react';
import {
  Bot, User, Send, Shield, Zap, FileText,
  AlertTriangle, Target, Lock, ArrowRight,
  BarChart3, Database, GitBranch, Clock, ChevronRight,
  Activity, Trash2, RefreshCw, Eye
} from 'lucide-react';
import { security } from '../services/api';
import './Copilot.css';

function parseMarkdown(text) {
  if (!text) return null;
  const lines = text.split('\n');
  const elements = [];
  let inCodeBlock = false;
  let codeLines = [];

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    if (line.startsWith('```')) {
      if (inCodeBlock) {
        elements.push(<pre key={`code-${i}`} className="copilot-code-block"><code>{codeLines.join('\n')}</code></pre>);
        codeLines = [];
        inCodeBlock = false;
      } else {
        inCodeBlock = true;
      }
      continue;
    }
    if (inCodeBlock) { codeLines.push(line); continue; }
    if (line.startsWith('### ')) elements.push(<h4 key={i} className="copilot-h4">{line.slice(4)}</h4>);
    else if (line.startsWith('## ')) elements.push(<h3 key={i} className="copilot-h3">{line.slice(3)}</h3>);
    else if (line.startsWith('# ')) elements.push(<h2 key={i} className="copilot-h2">{line.slice(2)}</h2>);
    else if (line.startsWith('- ') || line.startsWith('* ')) {
      elements.push(<div key={i} className="copilot-list-item"><span className="copilot-bullet" /><span>{renderInline(line.slice(2))}</span></div>);
    } else if (/^\d+\.\s/.test(line)) {
      const num = line.match(/^(\d+)\./)[1];
      elements.push(<div key={i} className="copilot-list-item"><span className="copilot-number">{num}.</span><span>{renderInline(line.replace(/^\d+\.\s/, ''))}</span></div>);
    } else if (line.trim() === '') elements.push(<div key={i} className="copilot-spacer" />);
    else elements.push(<p key={i} className="copilot-paragraph">{renderInline(line)}</p>);
  }
  if (inCodeBlock && codeLines.length > 0) {
    elements.push(<pre key="code-end" className="copilot-code-block"><code>{codeLines.join('\n')}</code></pre>);
  }
  return elements;
}

function renderInline(text) {
  const parts = [];
  let remaining = text;
  let key = 0;
  while (remaining.length > 0) {
    const boldMatch = remaining.match(/\*\*(.+?)\*\*/);
    const codeMatch = remaining.match(/`(.+?)`/);
    let nextMatch = null, matchType = '';
    if (boldMatch && (!codeMatch || boldMatch.index <= codeMatch.index)) { nextMatch = boldMatch; matchType = 'bold'; }
    else if (codeMatch) { nextMatch = codeMatch; matchType = 'code'; }
    if (!nextMatch) { parts.push(<span key={key++}>{remaining}</span>); break; }
    if (nextMatch.index > 0) parts.push(<span key={key++}>{remaining.slice(0, nextMatch.index)}</span>);
    if (matchType === 'bold') parts.push(<strong key={key++} className="copilot-bold">{nextMatch[1]}</strong>);
    else parts.push(<code key={key++} className="copilot-inline-code">{nextMatch[1]}</code>);
    remaining = remaining.slice(nextMatch.index + nextMatch[0].length);
  }
  return parts;
}

function MessageBubble({ msg }) {
  const isUser = msg.role === 'user';
  const text = msg.content || 'No response received.';
  return (
    <div className={`copilot-msg ${isUser ? 'user' : 'assistant'}`}>
      <div className={`copilot-msg-avatar ${isUser ? 'user' : 'assistant'}`}>
        {isUser ? <User size={16} /> : <Shield size={16} />}
      </div>
      <div className={`copilot-msg-content ${isUser ? 'user' : 'assistant'}`}>
        {!isUser && (
          <div className="copilot-msg-header">
            <span className="copilot-msg-name">SentinelAI</span>
            {msg.tool_used && (
              <span className="copilot-tool-badge"><Zap size={10} /> {msg.tool_used.replace(/_/g, ' ')}</span>
            )}
          </div>
        )}
        <div className="copilot-msg-body">
          {isUser ? <p>{text}</p> : parseMarkdown(text)}
        </div>
      </div>
    </div>
  );
}

const SEVERITY_COLORS = { Critical: '#ef4444', High: '#f97316', Medium: '#eab308', Low: '#10b981', Info: '#64748b' };

function DataContextPanel({ ctx }) {
  if (!ctx || ctx.error || !ctx.total_scans) return null;
  const riskColor = ctx.risk_score >= 80 ? '#ef4444' : ctx.risk_score >= 60 ? '#f97316' : ctx.risk_score >= 30 ? '#eab308' : '#10b981';
  const latest = ctx.latest_scan;
  const sevEntries = ctx.severity_counts ? Object.entries(ctx.severity_counts).filter(([,v]) => v > 0) : [];

  return (
    <div className="copilot-data-context">
      <div className="copilot-dc-header">
        <div className="copilot-dc-icon"><Database size={14} /></div>
        <div className="copilot-dc-title-group">
          <span className="copilot-dc-title">Security Assessment Data Loaded</span>
          <span className="copilot-dc-sub">SentinelAI is using this data to answer your questions</span>
        </div>
        <div className="copilot-dc-connected">
          <span className="copilot-dc-dot" />
          Active
        </div>
      </div>

      <div className="copilot-dc-body">
        {/* Risk score */}
        <div className="copilot-dc-risk">
          <div className="copilot-dc-risk-ring" style={{ borderColor: riskColor }}>
            <span className="copilot-dc-risk-num" style={{ color: riskColor }}>{ctx.risk_score}</span>
            <span className="copilot-dc-risk-max">/100</span>
          </div>
          <div className="copilot-dc-risk-label">
            <span className="copilot-dc-risk-level" style={{ color: riskColor }}>
              {ctx.risk_score >= 80 ? 'CRITICAL' : ctx.risk_score >= 60 ? 'HIGH' : ctx.risk_score >= 30 ? 'MEDIUM' : 'LOW'}
            </span>
            <span className="copilot-dc-risk-desc">Overall Risk Classification</span>
          </div>
        </div>

        {/* Stats row */}
        <div className="copilot-dc-stats">
          <div className="copilot-dc-stat">
            <span className="copilot-dc-stat-val">{ctx.total_scans}</span>
            <span className="copilot-dc-stat-lbl">Scans Run</span>
          </div>
          <div className="copilot-dc-stat">
            <span className="copilot-dc-stat-val">{ctx.total_findings}</span>
            <span className="copilot-dc-stat-lbl">Total Findings</span>
          </div>
          <div className="copilot-dc-stat critical">
            <span className="copilot-dc-stat-val">{ctx.critical_count}</span>
            <span className="copilot-dc-stat-lbl">Critical</span>
          </div>
        </div>

        {/* Severity bar */}
        {sevEntries.length > 0 && (
          <div className="copilot-dc-sev">
            <span className="copilot-dc-sev-label">Severity Distribution</span>
            <div className="copilot-dc-sev-bar">
              {sevEntries.map(([sev, count]) => {
                const total = sevEntries.reduce((a, [,v]) => a + v, 0);
                const pct = total > 0 ? (count / total) * 100 : 0;
                return (
                  <div key={sev} className="copilot-dc-sev-seg" style={{ width: `${pct}%`, background: SEVERITY_COLORS[sev] }} title={`${sev}: ${count}`} />
                );
              })}
            </div>
            <div className="copilot-dc-sev-legend">
              {sevEntries.map(([sev, count]) => (
                <span key={sev} className="copilot-dc-sev-item">
                  <span className="copilot-dc-sev-dot" style={{ background: SEVERITY_COLORS[sev] }} />
                  {sev} {count}
                </span>
              ))}
            </div>
          </div>
        )}

        {/* Latest scan source */}
        {latest && (
          <div className="copilot-dc-source">
            <div className="copilot-dc-source-row">
              <GitBranch size={13} />
              <span className="copilot-dc-source-label">Data Source</span>
            </div>
            <div className="copilot-dc-source-info">
              <span className="copilot-dc-source-name">{latest.api_name}</span>
              <span className="copilot-dc-source-meta">
                Score {latest.risk_score}/100 &middot; {latest.total_vulnerabilities} findings
              </span>
            </div>
          </div>
        )}

        {/* Recent findings */}
        {ctx.recent_findings?.length > 0 && (
          <div className="copilot-dc-findings">
            <span className="copilot-dc-findings-label">Top Findings in Context</span>
            {ctx.recent_findings.slice(0, 4).map((f, i) => (
              <div key={i} className="copilot-dc-finding">
                <span className="copilot-dc-finding-dot" style={{ background: SEVERITY_COLORS[f.severity] }} />
                <span className="copilot-dc-finding-name">{f.vulnerability_name}</span>
                <span className="copilot-dc-finding-sev" style={{ color: SEVERITY_COLORS[f.severity] }}>{f.severity}</span>
              </div>
            ))}
          </div>
        )}

        {/* Why */}
        <div className="copilot-dc-why">
          <Eye size={12} />
          <span>This data is pulled from your SQLite database via the <strong>SecurityContext</strong> engine. Every question you ask is answered against these real findings, CVEs, and risk scores.</span>
        </div>
      </div>
    </div>
  );
}

const SUGGESTIONS = [
  { icon: BarChart3, title: 'Security Status', desc: 'What is my current security posture?', msg: 'What is my security status?', color: '#3b82f6' },
  { icon: AlertTriangle, title: 'Highest Risk', desc: 'Show me the most critical findings', msg: 'What is my highest risk issue?', color: '#ef4444' },
  { icon: Zap, title: 'Remediation Plan', desc: 'Generate a prioritized fix plan', msg: 'Generate remediation plan', color: '#f97316' },
  { icon: FileText, title: 'Executive Summary', desc: 'Write a leadership-ready report', msg: 'Write executive summary', color: '#8b5cf6' },
  { icon: Target, title: 'Attack Analysis', desc: 'How would an attacker exploit this?', msg: 'How would an attacker exploit this?', color: '#ec4899' },
  { icon: Lock, title: 'OWASP Mapping', desc: 'Map findings to OWASP Top 10', msg: 'Map findings to OWASP Top 10', color: '#10b981' },
];

const FOLLOW_UPS = [
  { label: 'How do I fix this?', msg: 'How do I fix this?' },
  { label: 'Why is this critical?', msg: 'Why is this critical?' },
  { label: 'Compare my scans', msg: 'Compare my scans' },
  { label: 'Scan history', msg: 'Show my scan history' },
];

export default function Copilot() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [context, setContext] = useState(null);
  const [showWelcome, setShowWelcome] = useState(true);
  const messagesEnd = useRef();
  const inputRef = useRef();

  const scrollDown = useCallback(() => {
    messagesEnd.current?.scrollIntoView({ behavior: 'smooth' });
  }, []);

  useEffect(() => { scrollDown(); }, [messages, scrollDown]);
  useEffect(() => { loadContext(); inputRef.current?.focus(); }, []);

  const loadContext = async () => {
    try { const data = await security.copilot.sidebar(); setContext(data); }
    catch { setContext({ error: true }); }
  };

  const send = async (text) => {
    const msg = text || input.trim();
    if (!msg || loading) return;
    setShowWelcome(false);
    setMessages(prev => [...prev, { role: 'user', content: msg }]);
    setInput('');
    setLoading(true);
    try {
      const result = await security.copilot.chat(msg);
      setMessages(prev => [...prev, { role: 'assistant', content: result.response, tool_used: result.tool_used }]);
      loadContext();
    } catch (e) {
      setMessages(prev => [...prev, { role: 'assistant', content: `I encountered an error: ${e.message}. Please try again.` }]);
    } finally { setLoading(false); }
  };

  const clearChat = async () => {
    try { await security.copilot.clear(); } catch {}
    setMessages([]);
    setShowWelcome(true);
  };

  const handleKey = (e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send(); } };

  const riskColor = context?.risk_score >= 80 ? '#ef4444' : context?.risk_score >= 60 ? '#f97316' : context?.risk_score >= 30 ? '#eab308' : '#10b981';

  return (
    <div className="copilot-layout">
      {/* Top bar */}
      <div className="copilot-topbar">
        <div className="copilot-topbar-left">
          <div className="copilot-logo"><Shield size={18} /></div>
          <div className="copilot-topbar-info">
            <span className="copilot-topbar-title">SentinelAI Analyst</span>
            <span className="copilot-topbar-status">
              <span className="copilot-status-dot" />
              {context && !context.error && context.total_scans > 0 ? 'Connected to scan data' : 'No scan data loaded'}
            </span>
          </div>
        </div>
        <div className="copilot-topbar-right">
          {context && context.total_scans > 0 && (
            <div className="copilot-context-pills">
              <span className="copilot-pill"><span className="copilot-pill-dot" style={{ background: riskColor }} />Risk {context.risk_score}/100</span>
              <span className="copilot-pill">{context.total_findings} findings</span>
              {context.critical_count > 0 && <span className="copilot-pill danger">{context.critical_count} critical</span>}
            </div>
          )}
          <button className="copilot-refresh-btn" onClick={loadContext} title="Refresh context"><RefreshCw size={13} /></button>
          {messages.length > 0 && (
            <button className="copilot-clear-btn" onClick={clearChat} title="New conversation"><Trash2 size={14} /></button>
          )}
        </div>
      </div>

      {/* Messages area */}
      <div className="copilot-messages">
        {showWelcome ? (
          <div className="copilot-welcome">
            <div className="copilot-welcome-icon"><Shield size={40} /></div>
            <h1 className="copilot-welcome-title">SentinelAI Analyst</h1>
            <p className="copilot-welcome-sub">
              Your AI-powered security analyst. I have access to your scan data, findings, and risk assessments.
              Ask me anything about your security posture.
            </p>

            {/* Data context panel on welcome screen */}
            <DataContextPanel ctx={context} />

            <div className="copilot-suggestions">
              {SUGGESTIONS.map((s, i) => (
                <button key={i} className="copilot-suggestion" onClick={() => send(s.msg)}>
                  <div className="copilot-suggestion-icon" style={{ color: s.color, background: `${s.color}15` }}>
                    <s.icon size={18} />
                  </div>
                  <div className="copilot-suggestion-text">
                    <span className="copilot-suggestion-title">{s.title}</span>
                    <span className="copilot-suggestion-desc">{s.desc}</span>
                  </div>
                  <ArrowRight size={14} className="copilot-suggestion-arrow" />
                </button>
              ))}
            </div>
          </div>
        ) : (
          <div className="copilot-msg-list">
            {/* Data context panel at top of conversation */}
            <DataContextPanel ctx={context} />
            {messages.map((msg, i) => <MessageBubble key={i} msg={msg} />)}
            {loading && (
              <div className="copilot-msg assistant">
                <div className="copilot-msg-avatar assistant"><Shield size={16} /></div>
                <div className="copilot-msg-content assistant">
                  <div className="copilot-msg-header"><span className="copilot-msg-name">SentinelAI</span></div>
                  <div className="copilot-typing"><span /><span /><span /></div>
                </div>
              </div>
            )}
            <div ref={messagesEnd} />
          </div>
        )}
      </div>

      {/* Follow-up chips */}
      {!showWelcome && !loading && messages.length > 0 && messages.length % 2 === 0 && (
        <div className="copilot-followups">
          {FOLLOW_UPS.map((f, i) => (
            <button key={i} className="copilot-followup-btn" onClick={() => send(f.msg)}>{f.label}</button>
          ))}
        </div>
      )}

      {/* Input area */}
      <div className="copilot-input-wrap">
        <div className="copilot-input-container">
          <textarea ref={inputRef} value={input} onChange={e => setInput(e.target.value)} onKeyDown={handleKey}
            placeholder="Ask about your security findings..." rows={1} className="copilot-textarea" />
          <button className="copilot-send-btn" onClick={() => send()} disabled={!input.trim() || loading}>
            <Send size={18} />
          </button>
        </div>
        <p className="copilot-input-hint">SentinelAI analyzes your scan findings to provide grounded security guidance.</p>
      </div>
    </div>
  );
}
