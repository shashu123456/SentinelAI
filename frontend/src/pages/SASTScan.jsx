import { useState, useRef } from 'react';
import { Link } from 'react-router-dom';
import {
  ArrowLeft, Upload, FileCode, Shield, ChevronDown, ChevronUp,
  AlertTriangle, Search, Eye, Bug, Key, Terminal, Code, Database,
  Globe, Lock, Zap, CheckCircle2, XCircle, Info
} from 'lucide-react';
import { security } from '../services/api';
import './ScanResult.css';

const RULE_CATEGORIES = [
  { icon: Database, label: 'SQL Injection', desc: 'Detects dynamic SQL queries built with string formatting or concatenation', color: '#ef4444', langs: 'Python, JS, Java' },
  { icon: Terminal, label: 'Command Injection', desc: 'Finds os.system(), subprocess with shell=True, and exec() calls', color: '#f97316', langs: 'Python, JS, Java' },
  { icon: Key, label: 'Hardcoded Secrets', desc: 'Identifies passwords, API keys, tokens, and secrets in source code', color: '#ef4444', langs: 'Python, JS, Java' },
  { icon: Lock, label: 'Weak Cryptography', desc: 'Flags MD5, SHA1, DES and other deprecated algorithms', color: '#eab308', langs: 'Python, JS, Java' },
  { icon: Bug, label: 'XSS Vulnerabilities', desc: 'Catches innerHTML, dangerouslySetInnerHTML, and document.write usage', color: '#f97316', langs: 'JavaScript' },
  { icon: Eye, label: 'Path Traversal', desc: 'Detects open() with user-controlled paths and directory traversal patterns', color: '#eab308', langs: 'Python, JS, Java' },
  { icon: Globe, label: 'SSRF', desc: 'Finds requests.get() and fetch() with user-controlled URLs', color: '#8b5cf6', langs: 'Python, JS' },
  { icon: Zap, label: 'Unsafe Deserialization', desc: 'Flags pickle.loads(), yaml.load(), and eval() usage', color: '#ef4444', langs: 'Python' },
];

const LANGUAGES = [
  { ext: '.py', name: 'Python', rules: 14, examples: 'Django, Flask, FastAPI, SQLAlchemy' },
  { ext: '.js/.jsx', name: 'JavaScript', rules: 13, examples: 'Express, React, Node.js, Axios' },
  { ext: '.java', name: 'Java', rules: 13, examples: 'Spring Boot, Servlets, JDBC' },
];

const SEVERITY_COLORS = { Critical: '#ef4444', High: '#f97316', Medium: '#eab308', Low: '#10b981', Info: '#64748b' };

function DataContextPanel({ results }) {
  if (!results) return null;
  const s = results.summary;
  const riskPct = s.total_findings === 0 ? 0 : Math.min(100, Math.round(
    ((s.severity_counts.Critical || 0) * 40 + (s.severity_counts.High || 0) * 25 + (s.severity_counts.Medium || 0) * 10 + (s.severity_counts.Low || 0) * 3 + (s.severity_counts.Info || 0) * 1) / Math.max(s.files_scanned, 1) * 10
  ));
  const riskColor = riskPct >= 60 ? '#ef4444' : riskPct >= 30 ? '#f97316' : '#10b981';
  const owaspMap = {};
  results.findings.forEach(f => {
    const cat = f.owasp_category || 'Uncategorized';
    owaspMap[cat] = (owaspMap[cat] || 0) + 1;
  });
  const langMap = {};
  results.findings.forEach(f => {
    langMap[f.language] = (langMap[f.language] || 0) + 1;
  });

  return (
    <div className="copilot-data-context" style={{ marginBottom: '24px' }}>
      <div className="copilot-dc-header">
        <div className="copilot-dc-icon"><Eye size={14} /></div>
        <div className="copilot-dc-title-group">
          <span className="copilot-dc-title">Scan Analysis Complete</span>
          <span className="copilot-dc-sub">Results from static analysis of your source code</span>
        </div>
        <div className="copilot-dc-connected">
          <span className="copilot-dc-dot" />
          {s.total_findings > 0 ? `${s.total_findings} issues found` : 'Clean'}
        </div>
      </div>
      <div className="copilot-dc-body">
        <div className="copilot-dc-risk">
          <div className="copilot-dc-risk-ring" style={{ borderColor: riskColor }}>
            <span className="copilot-dc-risk-num" style={{ color: riskColor }}>{riskPct}</span>
            <span className="copilot-dc-risk-max">/100</span>
          </div>
          <div className="copilot-dc-risk-label">
            <span className="copilot-dc-risk-level" style={{ color: riskColor }}>
              {riskPct >= 60 ? 'HIGH RISK' : riskPct >= 30 ? 'MEDIUM RISK' : 'LOW RISK'}
            </span>
            <span className="copilot-dc-risk-desc">Code Security Risk Score</span>
          </div>
        </div>
        <div className="copilot-dc-stats">
          <div className="copilot-dc-stat"><span className="copilot-dc-stat-val">{s.files_scanned}</span><span className="copilot-dc-stat-lbl">Files Scanned</span></div>
          <div className="copilot-dc-stat"><span className="copilot-dc-stat-val">{s.lines_scanned.toLocaleString()}</span><span className="copilot-dc-stat-lbl">Lines Analyzed</span></div>
          <div className="copilot-dc-stat"><span className="copilot-dc-stat-val">{s.files_with_findings}</span><span className="copilot-dc-stat-lbl">Files with Issues</span></div>
        </div>
        {Object.keys(langMap).length > 0 && (
          <div className="copilot-dc-source">
            <div className="copilot-dc-source-row"><Globe size={13} /><span className="copilot-dc-source-label">Languages Detected</span></div>
            <div className="copilot-dc-source-info">
              {Object.entries(langMap).map(([lang, count]) => (
                <span key={lang} style={{ display: 'inline-flex', alignItems: 'center', gap: '6px', fontSize: '13px', color: 'var(--text-primary)', fontWeight: 600, marginRight: '16px' }}>
                  <span style={{ width: '8px', height: '8px', borderRadius: '2px', background: 'var(--accent-blue)', display: 'inline-block' }} />
                  {lang} ({count} findings)
                </span>
              ))}
            </div>
          </div>
        )}
        {Object.keys(owaspMap).length > 0 && (
          <div className="copilot-dc-source">
            <div className="copilot-dc-source-row"><Lock size={13} /><span className="copilot-dc-source-label">OWASP Categories Affected</span></div>
            <div className="copilot-dc-source-info" style={{ flexDirection: 'column', gap: '4px' }}>
              {Object.entries(owaspMap).sort((a, b) => b[1] - a[1]).map(([cat, count]) => (
                <div key={cat} style={{ display: 'flex', justifyContent: 'space-between', width: '100%', fontSize: '12px' }}>
                  <span style={{ color: 'var(--text-secondary)' }}>{cat}</span>
                  <span style={{ color: 'var(--text-primary)', fontWeight: 600 }}>{count} finding{count > 1 ? 's' : ''}</span>
                </div>
              ))}
            </div>
          </div>
        )}
        <div className="copilot-dc-why">
          <Info size={12} />
          <span>Scanned <strong>{s.files_scanned} files</strong> ({s.lines_scanned.toLocaleString()} lines) across <strong>{Object.keys(langMap).length || 0} languages</strong> using <strong>40 regex-based security rules</strong>. Each finding includes CWE mapping, OWASP category, confidence score, and line-level evidence.</span>
        </div>
      </div>
    </div>
  );
}

export default function SASTScan() {
  const [file, setFile] = useState(null);
  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [expandedFinding, setExpandedFinding] = useState(null);
  const [dragActive, setDragActive] = useState(false);
  const inputRef = useRef();

  const handleDrag = (e) => { e.preventDefault(); e.stopPropagation(); setDragActive(e.type === 'dragenter' || e.type === 'dragover'); };
  const handleDrop = (e) => { e.preventDefault(); e.stopPropagation(); setDragActive(false); if (e.dataTransfer.files?.[0]) handleFile(e.dataTransfer.files[0]); };
  const handleFile = (f) => {
    const ext = f.name.split('.').pop().toLowerCase();
    if (['py', 'js', 'jsx', 'ts', 'tsx', 'java'].includes(ext)) { setFile(f); setError(''); }
    else setError('Unsupported file type. Upload .py, .js, .jsx, .ts, .tsx, or .java');
  };
  const handleScan = async () => {
    if (!file) return;
    setLoading(true); setError('');
    try { const r = await security.sast.scanFile(file); setResults(r); }
    catch (e) { setError(e.message); } finally { setLoading(false); }
  };
  const reset = () => { setResults(null); setFile(null); setError(''); };

  return (
    <div className="page-content">
      <Link to="/dashboard" className="back-link"><ArrowLeft size={16} /> Back to Dashboard</Link>

      <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '4px' }}>
        <FileCode size={28} style={{ color: 'var(--accent-purple)' }} />
        <h1 style={{ fontSize: '22px', fontWeight: 700, letterSpacing: '-0.3px' }}>SAST Scanner</h1>
      </div>
      <p style={{ color: 'var(--text-muted)', fontSize: '13px', marginBottom: '24px' }}>
        Static Application Security Testing for Python, JavaScript, and Java source code
      </p>

      {!results && (
        <>
          {/* What is SAST */}
          <div className="info-card" style={{ marginBottom: '20px' }}>
            <div className="info-card-header">
              <Search size={16} style={{ color: 'var(--accent-purple)' }} />
              <span>What is SAST?</span>
            </div>
            <p style={{ fontSize: '13px', color: 'var(--text-secondary)', lineHeight: '1.6', margin: 0 }}>
              Static Application Security Testing analyzes your source code <strong>without executing it</strong>. It scans every line for
              known vulnerability patterns like SQL injection, hardcoded secrets, XSS, and command injection. The scanner uses
              40 regex-based security rules mapped to <strong>CWE</strong> (Common Weakness Enumeration) and <strong>OWASP</strong> categories,
              providing line-level evidence with confidence scores for each finding.
            </p>
          </div>

          {/* What We Check */}
          <div style={{ marginBottom: '20px' }}>
            <h3 style={{ fontSize: '13px', fontWeight: 700, color: 'var(--text-primary)', marginBottom: '12px', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
              What We Check
            </h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: '10px' }}>
              {RULE_CATEGORIES.map((cat, i) => (
                <div key={i} className="rule-cat-card">
                  <div className="rule-cat-icon" style={{ color: cat.color, background: `${cat.color}12` }}>
                    <cat.icon size={16} />
                  </div>
                  <div className="rule-cat-info">
                    <span className="rule-cat-label">{cat.label}</span>
                    <span className="rule-cat-desc">{cat.desc}</span>
                    <span className="rule-cat-langs">{cat.langs}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Language Coverage */}
          <div style={{ marginBottom: '20px' }}>
            <h3 style={{ fontSize: '13px', fontWeight: 700, color: 'var(--text-primary)', marginBottom: '12px', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
              Language Coverage
            </h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '10px' }}>
              {LANGUAGES.map((lang, i) => (
                <div key={i} className="lang-card">
                  <div className="lang-ext">{lang.ext}</div>
                  <div className="lang-name">{lang.name}</div>
                  <div className="lang-rules">{lang.rules} security rules</div>
                  <div className="lang-examples">{lang.examples}</div>
                </div>
              ))}
            </div>
          </div>

          {/* Upload Zone */}
          <div className="scan-page-card">
            <div
              className={`scan-dropzone ${dragActive ? 'active' : ''} ${file ? 'has-file' : ''}`}
              onDragEnter={handleDrag} onDragLeave={handleDrag} onDragOver={handleDrag} onDrop={handleDrop}
              onClick={() => inputRef.current?.click()}
            >
              <input ref={inputRef} type="file" hidden accept=".py,.js,.jsx,.ts,.tsx,.java" onChange={(e) => e.target.files?.[0] && handleFile(e.target.files[0])} />
              {file ? (
                <div className="scan-file-selected">
                  <FileCode size={40} />
                  <div className="scan-file-info">
                    <span className="scan-file-name">{file.name}</span>
                    <span className="scan-file-size">({(file.size / 1024).toFixed(1)} KB)</span>
                  </div>
                </div>
              ) : (
                <>
                  <Upload size={40} className="scan-dropzone-icon" />
                  <h3>Drop source code file here</h3>
                  <p>Supports: .py, .js, .jsx, .ts, .tsx, .java</p>
                </>
              )}
            </div>
            {error && <div className="error-banner">{error}</div>}
            <button className="btn-primary" style={{ padding: '12px 32px' }} disabled={!file || loading} onClick={handleScan}>
              {loading ? 'Scanning...' : 'Run SAST Scan'}
            </button>
          </div>
        </>
      )}

      {results && (
        <>
          <DataContextPanel results={results} />

          <div className="severity-cards" style={{ marginBottom: '24px' }}>
            {['Critical', 'High', 'Medium', 'Low', 'Info'].map(sev => (
              <div key={sev} className={`severity-card ${sev.toLowerCase()}`}>
                <span className="sev-count">{results.summary.severity_counts[sev] || 0}</span>
                <span className="sev-label">{sev}</span>
              </div>
            ))}
          </div>

          <div className="scan-stats">
            <span className="scan-stat">Files: <strong>{results.summary.files_scanned}</strong></span>
            <span className="scan-stat">Lines: <strong>{results.summary.lines_scanned.toLocaleString()}</strong></span>
            <span className="scan-stat">Languages: <strong>{results.summary.languages_detected.join(', ') || 'None'}</strong></span>
            <span className={`scan-stat ${results.summary.total_findings > 0 ? 'danger' : 'safe'}`}>
              Findings: <strong>{results.summary.total_findings}</strong>
            </span>
          </div>

          {results.findings.length > 0 ? (
            <div className="findings-list">
              {results.findings.map((f, idx) => (
                <div key={idx} className="scan-finding">
                  <div className="scan-finding-header" onClick={() => setExpandedFinding(expandedFinding === idx ? null : idx)}>
                    <span className={`sev-badge ${f.severity.toLowerCase()}`}>{f.severity}</span>
                    <span className="scan-finding-title">{f.rule_name}</span>
                    <span className="scan-finding-meta">
                      <span>{f.cwe_id}</span>
                      <span>{f.file_path.split(/[/\\]/).pop()}:{f.line_number}</span>
                      <span>{Math.round(f.confidence * 100)}%</span>
                    </span>
                    {expandedFinding === idx ? <ChevronUp size={16} className="chevron-icon" /> : <ChevronDown size={16} className="chevron-icon" />}
                  </div>
                  {expandedFinding === idx && (
                    <div className="scan-finding-detail">
                      <div>
                        <label>Description</label>
                        <p>{f.description}</p>
                      </div>
                      <div>
                        <label>Remediation</label>
                        <p>{f.remediation}</p>
                      </div>
                      <pre>{f.file_path}:{f.line_number}{'\n'}{f.line_content}</pre>
                    </div>
                  )}
                </div>
              ))}
            </div>
          ) : (
            <div className="scan-empty">
              <Shield size={48} />
              <h3>No vulnerabilities found</h3>
              <p>The scanned code passed all {results.summary.languages_detected.length > 0 ? results.summary.languages_detected.join('/') : ''} security rules</p>
            </div>
          )}

          <button className="btn-outline" style={{ marginTop: '24px' }} onClick={reset}>Scan Another File</button>
        </>
      )}
    </div>
  );
}
