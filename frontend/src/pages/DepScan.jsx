import { useState, useRef } from 'react';
import { Link } from 'react-router-dom';
import {
  ArrowLeft, Upload, Package, ShieldAlert, ExternalLink,
  Search, AlertTriangle, CheckCircle2, Info, Eye, Shield,
  Bug, Lock, Globe, Zap, Server, FileCode, RefreshCw
} from 'lucide-react';
import { security } from '../services/api';
import './ScanResult.css';

const VULN_CATEGORIES = [
  { icon: Bug, label: 'Known CVEs', desc: 'Cross-references your packages against 38+ curated CVE entries from NVD', color: '#ef4444' },
  { icon: Lock, label: 'CWE Mapping', desc: 'Each vulnerability mapped to Common Weakness Enumeration IDs', color: '#f97316' },
  { icon: Zap, label: 'CVSS Scoring', desc: 'Common Vulnerability Scoring System severity ratings (0.0-10.0)', color: '#eab308' },
  { icon: RefreshCw, label: 'Fix Versions', desc: 'Identifies the minimum safe version to upgrade each vulnerable package', color: '#10b981' },
];

const ECOSYSTEMS = [
  { name: 'Python', icon: FileCode, ext: 'requirements.txt', pkgs: 'Django, Flask, requests, urllib3, PyYAML, cryptography', color: '#3b82f6', vulnCount: 15 },
  { name: 'JavaScript', icon: Globe, ext: 'package.json', pkgs: 'lodash, axios, express, react, webpack, node-fetch', color: '#eab308', vulnCount: 13 },
  { name: 'Java', icon: Server, ext: 'pom.xml', pkgs: 'Spring Framework, Log4j, Jackson, Apache Tomcat', color: '#ef4444', vulnCount: 10 },
];

const SEVERITY_COLORS = { Critical: '#ef4444', High: '#f97316', Medium: '#eab308', Low: '#10b981', Info: '#64748b' };

function DataContextPanel({ results }) {
  if (!results) return null;
  const s = results.summary;
  const vulnPct = s.total_dependencies > 0 ? Math.round((s.total_vulnerabilities / s.total_dependencies) * 100) : 0;
  const riskColor = vulnPct >= 30 ? '#ef4444' : vulnPct >= 10 ? '#f97316' : '#10b981';
  const ecoBreakdown = {};
  results.dependencies.forEach(d => {
    ecoBreakdown[d.ecosystem] = (ecoBreakdown[d.ecosystem] || 0) + 1;
  });
  const ecoVulnBreakdown = {};
  results.findings.forEach(f => {
    ecoVulnBreakdown[f.ecosystem] = (ecoVulnBreakdown[f.ecosystem] || 0) + 1;
  });

  return (
    <div className="copilot-data-context" style={{ marginBottom: '24px' }}>
      <div className="copilot-dc-header">
        <div className="copilot-dc-icon"><Eye size={14} /></div>
        <div className="copilot-dc-title-group">
          <span className="copilot-dc-title">Dependency Analysis Complete</span>
          <span className="copilot-dc-sub">Cross-referenced {s.total_dependencies} packages against known CVE database</span>
        </div>
        <div className="copilot-dc-connected">
          <span className="copilot-dc-dot" />
          {s.total_vulnerabilities > 0 ? `${s.total_vulnerabilities} vulnerabilities` : 'All clear'}
        </div>
      </div>
      <div className="copilot-dc-body">
        <div className="copilot-dc-risk">
          <div className="copilot-dc-risk-ring" style={{ borderColor: riskColor }}>
            <span className="copilot-dc-risk-num" style={{ color: riskColor }}>{vulnPct}</span>
            <span className="copilot-dc-risk-max">%</span>
          </div>
          <div className="copilot-dc-risk-label">
            <span className="copilot-dc-risk-level" style={{ color: riskColor }}>
              {vulnPct >= 30 ? 'HIGH EXPOSURE' : vulnPct >= 10 ? 'MODERATE EXPOSURE' : 'LOW EXPOSURE'}
            </span>
            <span className="copilot-dc-risk-desc">Vulnerable Packages Ratio ({s.total_vulnerabilities}/{s.total_dependencies})</span>
          </div>
        </div>
        <div className="copilot-dc-stats">
          <div className="copilot-dc-stat"><span className="copilot-dc-stat-val">{s.total_dependencies}</span><span className="copilot-dc-stat-lbl">Total Packages</span></div>
          <div className="copilot-dc-stat"><span className="copilot-dc-stat-val">{s.total_vulnerabilities}</span><span className="copilot-dc-stat-lbl">Vulnerabilities</span></div>
          <div className="copilot-dc-stat critical"><span className="copilot-dc-stat-val">{s.severity_counts?.Critical || 0}</span><span className="copilot-dc-stat-lbl">Critical CVEs</span></div>
        </div>
        {s.total_vulnerabilities > 0 && (
          <div className="copilot-dc-sev">
            <span className="copilot-dc-sev-label">Severity Distribution</span>
            <div className="copilot-dc-sev-bar">
              {Object.entries(s.severity_counts).filter(([,v]) => v > 0).map(([sev, count]) => {
                const total = Object.values(s.severity_counts).reduce((a, b) => a + b, 0);
                return <div key={sev} className="copilot-dc-sev-seg" style={{ width: `${(count / total) * 100}%`, background: SEVERITY_COLORS[sev] }} title={`${sev}: ${count}`} />;
              })}
            </div>
            <div className="copilot-dc-sev-legend">
              {Object.entries(s.severity_counts).filter(([,v]) => v > 0).map(([sev, count]) => (
                <span key={sev} className="copilot-dc-sev-item">
                  <span className="copilot-dc-sev-dot" style={{ background: SEVERITY_COLORS[sev] }} />
                  {sev} {count}
                </span>
              ))}
            </div>
          </div>
        )}
        <div className="copilot-dc-source">
          <div className="copilot-dc-source-row"><Globe size={13} /><span className="copilot-dc-source-label">Ecosystem Breakdown</span></div>
          <div className="copilot-dc-source-info" style={{ flexDirection: 'column', gap: '6px' }}>
            {Object.entries(ecoBreakdown).map(([eco, count]) => (
              <div key={eco} style={{ display: 'flex', justifyContent: 'space-between', width: '100%', fontSize: '12px' }}>
                <span style={{ color: 'var(--text-secondary)', textTransform: 'capitalize' }}>{eco}</span>
                <span style={{ color: 'var(--text-primary)', fontWeight: 600 }}>
                  {count} packages{ecoVulnBreakdown[eco] ? ` (${ecoVulnBreakdown[eco]} vulnerable)` : ' (clean)'}
                </span>
              </div>
            ))}
          </div>
        </div>
        <div className="copilot-dc-why">
          <Info size={12} />
          <span>Parsed <strong>{s.total_dependencies} dependencies</strong> from your manifest file, cross-referenced against a curated database of <strong>38+ known CVEs</strong> across Python, JavaScript, and Java ecosystems. Each finding includes CVSS score, CWE mapping, and the minimum safe version to upgrade.</span>
        </div>
      </div>
    </div>
  );
}

export default function DepScan() {
  const [file, setFile] = useState(null);
  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [dragActive, setDragActive] = useState(false);
  const inputRef = useRef();

  const handleDrag = (e) => { e.preventDefault(); e.stopPropagation(); setDragActive(e.type === 'dragenter' || e.type === 'dragover'); };
  const handleDrop = (e) => { e.preventDefault(); e.stopPropagation(); setDragActive(false); if (e.dataTransfer.files?.[0]) handleFile(e.dataTransfer.files[0]); };
  const handleFile = (f) => {
    const allowed = ['requirements.txt', 'package.json', 'pom.xml', 'requirements.in', 'Pipfile'];
    if (allowed.some(name => f.name === name)) { setFile(f); setError(''); }
    else setError('Upload requirements.txt, package.json, requirements.in, Pipfile, or pom.xml');
  };
  const handleScan = async () => {
    if (!file) return;
    setLoading(true); setError('');
    try { const r = await security.deps.scanFile(file); setResults(r); }
    catch (e) { setError(e.message); } finally { setLoading(false); }
  };
  const reset = () => { setResults(null); setFile(null); setError(''); };

  return (
    <div className="page-content">
      <Link to="/dashboard" className="back-link"><ArrowLeft size={16} /> Back to Dashboard</Link>

      <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '4px' }}>
        <Package size={28} style={{ color: 'var(--accent-blue)' }} />
        <h1 style={{ fontSize: '22px', fontWeight: 700, letterSpacing: '-0.3px' }}>Dependency Scanner</h1>
      </div>
      <p style={{ color: 'var(--text-muted)', fontSize: '13px', marginBottom: '24px' }}>
        Detect known CVEs in Python, JavaScript, and Java dependencies
      </p>

      {!results && (
        <>
          {/* What is Dependency Scanning */}
          <div className="info-card" style={{ marginBottom: '20px' }}>
            <div className="info-card-header">
              <Search size={16} style={{ color: 'var(--accent-blue)' }} />
              <span>What is Dependency Scanning?</span>
            </div>
            <p style={{ fontSize: '13px', color: 'var(--text-secondary)', lineHeight: '1.6', margin: 0 }}>
              Your application inherits the security of every package it uses. Dependency scanning parses your manifest file
              (<strong>requirements.txt</strong>, <strong>package.json</strong>, or <strong>pom.xml</strong>) and cross-references each package
              against a curated database of <strong>38+ known CVEs</strong>. It identifies which packages have known vulnerabilities,
              what severity they are, and the minimum safe version to upgrade to. Outdated dependencies are the #1 attack vector
              for supply chain attacks.
            </p>
          </div>

          {/* What We Check */}
          <div style={{ marginBottom: '20px' }}>
            <h3 style={{ fontSize: '13px', fontWeight: 700, color: 'var(--text-primary)', marginBottom: '12px', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
              What We Check
            </h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: '10px' }}>
              {VULN_CATEGORIES.map((cat, i) => (
                <div key={i} className="rule-cat-card">
                  <div className="rule-cat-icon" style={{ color: cat.color, background: `${cat.color}12` }}>
                    <cat.icon size={16} />
                  </div>
                  <div className="rule-cat-info">
                    <span className="rule-cat-label">{cat.label}</span>
                    <span className="rule-cat-desc">{cat.desc}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Ecosystem Coverage */}
          <div style={{ marginBottom: '20px' }}>
            <h3 style={{ fontSize: '13px', fontWeight: 700, color: 'var(--text-primary)', marginBottom: '12px', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
              Ecosystem Coverage
            </h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '10px' }}>
              {ECOSYSTEMS.map((eco, i) => (
                <div key={i} className="lang-card">
                  <div className="lang-ext" style={{ color: eco.color }}>{eco.ext}</div>
                  <div className="lang-name">{eco.name}</div>
                  <div className="lang-rules">{eco.vulnCount} CVEs tracked</div>
                  <div className="lang-examples">{eco.pkgs}</div>
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
              <input ref={inputRef} type="file" hidden accept=".txt,.json,.xml" onChange={(e) => e.target.files?.[0] && handleFile(e.target.files[0])} />
              {file ? (
                <div className="scan-file-selected">
                  <Package size={40} />
                  <div className="scan-file-info">
                    <span className="scan-file-name">{file.name}</span>
                  </div>
                </div>
              ) : (
                <>
                  <Upload size={40} className="scan-dropzone-icon" />
                  <h3>Drop dependency manifest here</h3>
                  <p>requirements.txt, package.json, or pom.xml</p>
                </>
              )}
            </div>
            {error && <div className="error-banner">{error}</div>}
            <button className="btn-primary" style={{ padding: '12px 32px' }} disabled={!file || loading} onClick={handleScan}>
              {loading ? 'Scanning...' : 'Scan Dependencies'}
            </button>
          </div>
        </>
      )}

      {results && (
        <>
          <DataContextPanel results={results} />

          <div className="scan-stats" style={{ marginBottom: '20px' }}>
            <span className="scan-stat">Packages: <strong>{results.summary.total_dependencies}</strong></span>
            <span className={`scan-stat ${results.summary.total_vulnerabilities > 0 ? 'danger' : 'safe'}`}>
              Vulnerabilities: <strong>{results.summary.total_vulnerabilities}</strong>
            </span>
            <span className="scan-stat">Critical: <strong style={{ color: 'var(--severity-critical)' }}>{results.summary.severity_counts?.Critical || 0}</strong></span>
            <span className="scan-stat">High: <strong style={{ color: 'var(--severity-high)' }}>{results.summary.severity_counts?.High || 0}</strong></span>
            <span className="scan-stat">Medium: <strong style={{ color: 'var(--severity-medium)' }}>{results.summary.severity_counts?.Medium || 0}</strong></span>
            <span className="scan-stat" style={{ marginLeft: 'auto' }}>
              Ecosystems: <strong>{results.summary.ecosystems_detected.join(', ')}</strong>
            </span>
          </div>

          {results.findings.length > 0 ? (
            <div className="findings-list">
              {results.findings.map((f, idx) => (
                <div key={idx} className="scan-finding" style={{ borderLeft: 'none' }}>
                  <div className="scan-finding-header" style={{ borderLeft: `4px solid var(--severity-${f.severity.toLowerCase()})` }}>
                    <span className={`sev-badge ${f.severity.toLowerCase()}`}>{f.severity}</span>
                    <span className="scan-finding-title">{f.package}</span>
                    <span className="scan-finding-meta">
                      <span>{f.installed_version}</span>
                      <span style={{ padding: '2px 8px', borderRadius: '4px', background: 'var(--severity-critical-bg)', color: 'var(--severity-critical)', fontSize: '11px', fontWeight: 600 }}>
                        CVE: {f.cve_id}
                      </span>
                      <span>{f.cwe_id}</span>
                      <span>CVSS: {f.cvss_score}</span>
                      {f.url && (
                        <a href={f.url} target="_blank" rel="noopener noreferrer" style={{ color: 'var(--accent-blue)', display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
                          <ExternalLink size={12} /> Details
                        </a>
                      )}
                    </span>
                  </div>
                  <div style={{ padding: '0 20px 16px', marginTop: '4px' }}>
                    <p style={{ color: 'var(--text-secondary)', fontSize: '13px', marginBottom: '10px' }}>{f.description}</p>
                    <div className="scan-fix-box">
                      <strong>Fix: </strong>
                      <span>Update to {f.fixed_in} or later</span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="scan-empty">
              <ShieldAlert size={48} />
              <h3>No known vulnerabilities</h3>
              <p>All {results.summary.total_dependencies} dependencies are clean</p>
            </div>
          )}

          {results.dependencies.length > 0 && (
            <div className="scan-page-card" style={{ marginTop: '24px' }}>
              <h3 style={{ fontSize: '14px', fontWeight: 600, color: 'var(--text-primary)', marginBottom: '12px' }}>
                All Dependencies ({results.dependencies.length})
              </h3>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: '8px' }}>
                {results.dependencies.map((dep, idx) => {
                  const isVulnerable = results.findings.some(f => f.package === dep.name);
                  return (
                    <div key={idx} style={{
                      padding: '8px 12px', borderRadius: '6px',
                      background: isVulnerable ? 'var(--severity-critical-bg)' : 'var(--bg-page)',
                      border: `1px solid ${isVulnerable ? '#fecaca' : 'var(--border)'}`,
                      fontSize: '12px', display: 'flex', justifyContent: 'space-between',
                    }}>
                      <span style={{ color: isVulnerable ? 'var(--severity-critical)' : 'var(--text-primary)', fontWeight: isVulnerable ? 600 : 400 }}>{dep.name}</span>
                      <span style={{ color: 'var(--text-muted)' }}>{dep.version}</span>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          <button className="btn-outline" style={{ marginTop: '24px' }} onClick={reset}>Scan Another File</button>
        </>
      )}
    </div>
  );
}
