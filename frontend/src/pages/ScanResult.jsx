import { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { scans } from '../services/api';
import {
  ArrowLeft, FileJson, FileText,
  AlertTriangle, ChevronDown, ChevronUp, Shield,
  ExternalLink, Target, Zap, Bug, Info
} from 'lucide-react';
import './ScanResult.css';

export default function ScanResult() {
  const { id } = useParams();
  const [scan, setScan] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [expandedFinding, setExpandedFinding] = useState(null);
  const [downloading, setDownloading] = useState(null);

  useEffect(() => { loadScan(); }, [id]);

  const loadScan = async () => {
    try {
      const data = await scans.get(id);
      setScan(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleDownload = async (type) => {
    try {
      setDownloading(type);
      if (type === 'pdf') await scans.downloadPdf(id);
      else await scans.downloadJson(id);
    } catch (err) {
      alert(err.message || 'Download failed');
    } finally {
      setDownloading(null);
    }
  };

  if (loading) {
    return (
      <div className="page-content">
        <div className="loading-container">
          <div className="spinner"></div>
          <p>Loading scan results...</p>
        </div>
      </div>
    );
  }

  if (error || !scan) {
    return (
      <div className="page-content">
        <div className="error-banner">{error || 'Scan not found'}</div>
        <Link to="/dashboard" className="back-link">
          <ArrowLeft size={16} /> Back to Dashboard
        </Link>
      </div>
    );
  }

  const findings = scan.findings || [];
  const severityOrder = ['Critical', 'High', 'Medium', 'Low', 'Info'];
  const sortedFindings = [...findings].sort(
    (a, b) => severityOrder.indexOf(a.severity) - severityOrder.indexOf(b.severity)
  );
  const counts = {};
  severityOrder.forEach(s => counts[s] = 0);
  findings.forEach(f => { if (counts[f.severity] !== undefined) counts[f.severity]++; });

  return (
    <div className="page-content">
      <Link to="/dashboard" className="back-link">
        <ArrowLeft size={16} /> Back to Dashboard
      </Link>

      <div className="result-header">
        <div className="result-title">
          <div className="result-shield">
            <Shield size={20} />
          </div>
          <div>
            <h1>{scan.api_name}</h1>
            {scan.api_version && <span className="version-badge">v{scan.api_version}</span>}
          </div>
        </div>
        <div className="result-actions">
          <button className="btn-outline" onClick={() => handleDownload('pdf')} disabled={downloading === 'pdf'}>
            <FileText size={16} /> {downloading === 'pdf' ? 'Generating...' : 'PDF Report'}
          </button>
          <button className="btn-outline" onClick={() => handleDownload('json')} disabled={downloading === 'json'}>
            <FileJson size={16} /> {downloading === 'json' ? 'Exporting...' : 'JSON Export'}
          </button>
        </div>
      </div>

      <div className="result-summary">
        <div className="threat-assessment">
          <div className="threat-gauge-wrap">
            <svg viewBox="0 0 200 120" className="threat-gauge-svg">
              <path d="M 20 100 A 80 80 0 0 1 180 100" fill="none" stroke="rgba(59,130,246,0.08)" strokeWidth="10" strokeLinecap="round" />
              <path d="M 20 100 A 80 80 0 0 1 180 100" fill="none" stroke="url(#scanGaugeGrad)" strokeWidth="10" strokeLinecap="round"
                strokeDasharray={`${(scan.risk_score / 100) * 251.2} 251.2`} className="threat-gauge-arc" />
              <defs>
                <linearGradient id="scanGaugeGrad" x1="0%" y1="0%" x2="100%" y2="0%">
                  <stop offset="0%" stopColor="var(--accent-blue)" />
                  <stop offset="50%" stopColor="var(--accent-purple)" />
                  <stop offset="100%" stopColor="var(--accent-red)" />
                </linearGradient>
              </defs>
              {[0, 25, 50, 75, 100].map((tick) => {
                const angle = (tick / 100) * 180 - 180;
                const rad = (angle * Math.PI) / 180;
                const x1 = 100 + 72 * Math.cos(rad);
                const y1 = 100 + 72 * Math.sin(rad);
                const x2 = 100 + 82 * Math.cos(rad);
                const y2 = 100 + 82 * Math.sin(rad);
                return <line key={tick} x1={x1} y1={y1} x2={x2} y2={y2} stroke="rgba(59,130,246,0.15)" strokeWidth="1.5" />;
              })}
            </svg>
            <div className="threat-gauge-center">
              <span className="threat-gauge-score" style={{ color: getRiskColor(scan.risk_score) }}>{scan.risk_score}</span>
              <span className="threat-gauge-sub">/100</span>
            </div>
          </div>
          <div className="threat-gauge-labels">
            <span>0</span><span>25</span><span>50</span><span>75</span><span>100</span>
          </div>
          <div className={`threat-level-badge ${getRiskClass(scan.risk_score)}`}>
            <span className="threat-level-dot" />
            {scan.risk_level} Risk
          </div>
        </div>

        <div className="severity-cards">
          {severityOrder.map(sev => (
            <div key={sev} className={`severity-card ${sev.toLowerCase()}`}>
              <span className="sev-count">{counts[sev]}</span>
              <span className="sev-label">{sev}</span>
            </div>
          ))}
        </div>

        <div className="meta-info">
          <div className="meta-item">
            <Target size={15} />
            <span>{scan.total_endpoints} endpoints</span>
          </div>
          <div className="meta-item">
            <Bug size={15} />
            <span>{scan.total_vulnerabilities} vulnerabilities</span>
          </div>
          <div className="meta-item">
            <Zap size={15} />
            <span>{scan.status}</span>
          </div>
        </div>
      </div>

      {scan.ai_analysis && (
        <div className="ai-section">
          <div className="section-header">
            <Shield size={18} />
            <h2>AI Security Analysis</h2>
          </div>
          <div className="ai-grid">
            {scan.ai_analysis.executive_summary && (
              <div className="ai-card executive">
                <h4>Executive Summary</h4>
                <p>{scan.ai_analysis.executive_summary}</p>
              </div>
            )}
            {scan.ai_analysis.technical_explanation && (
              <div className="ai-card technical">
                <h4>Technical Analysis</h4>
                <p>{scan.ai_analysis.technical_explanation}</p>
              </div>
            )}
            {scan.ai_analysis.business_impact && (
              <div className="ai-card business">
                <h4>Business Impact</h4>
                <p>{scan.ai_analysis.business_impact}</p>
              </div>
            )}
            {scan.ai_analysis.attack_scenario && (
              <div className="ai-card attack">
                <h4>Attack Scenario</h4>
                <p>{scan.ai_analysis.attack_scenario}</p>
              </div>
            )}
            {scan.ai_analysis.recommended_mitigation && (
              <div className="ai-card mitigation">
                <h4>Recommended Mitigation</h4>
                <p>{scan.ai_analysis.recommended_mitigation}</p>
              </div>
            )}
          </div>
        </div>
      )}

      <div className="findings-section">
        <div className="section-header">
          <AlertTriangle size={18} />
          <h2>Detailed Findings ({findings.length})</h2>
        </div>

        {findings.length === 0 ? (
          <div className="no-findings">
            <div className="no-findings-icon"><Shield size={40} /></div>
            <h3>No Vulnerabilities Found</h3>
            <p>The API specification passed all OWASP API Security Top 10 checks.</p>
          </div>
        ) : (
          <div className="findings-list">
            {sortedFindings.map((finding, index) => (
              <div
                key={finding.id || index}
                className={`finding-card ${finding.severity.toLowerCase()} ${expandedFinding === index ? 'expanded' : ''}`}
                onClick={() => setExpandedFinding(expandedFinding === index ? null : index)}
              >
                <div className="finding-header">
                  <div className="finding-title-row">
                    <span className={`severity-indicator ${finding.severity.toLowerCase()}`}></span>
                    <div className="finding-title-text">
                      <h3>{finding.vulnerability_name}</h3>
                      <div className="finding-subtitle">
                        {finding.affected_endpoint && (
                          <span className="endpoint-label">
                            {finding.affected_method} {finding.affected_endpoint}
                          </span>
                        )}
                      </div>
                    </div>
                  </div>
                  <div className="finding-meta">
                    <span className="owasp-badge">{finding.owasp_category}</span>
                    {finding.cwe_id && (
                      <span className="cwe-badge">{finding.cwe_id}</span>
                    )}
                    <span className={`severity-text ${finding.severity.toLowerCase()}`}>
                      {finding.severity}
                    </span>
                    {finding.confidence && (
                      <span className="confidence-badge" title="Detection confidence">
                        {finding.confidence}%
                      </span>
                    )}
                    {expandedFinding === index ? <ChevronUp size={16} className="chevron-icon" /> : <ChevronDown size={16} className="chevron-icon" />}
                  </div>
                </div>

                {expandedFinding === index && (
                  <div className="finding-details" onClick={(e) => e.stopPropagation()}>
                    <div className="detail-block">
                      <h4>Description</h4>
                      <p>{finding.description}</p>
                    </div>
                    {finding.detection_reason && (
                      <div className="detail-block detection-block">
                        <h4><Info size={13} /> Detection Reason</h4>
                        <p>{finding.detection_reason}</p>
                      </div>
                    )}
                    {finding.evidence && (
                      <div className="detail-block">
                        <h4>Evidence</h4>
                        <pre className="evidence">{finding.evidence}</pre>
                      </div>
                    )}
                    <div className="detail-block">
                      <h4>Impact</h4>
                      <p>{finding.impact}</p>
                    </div>
                    <div className="detail-block remediation-block">
                      <h4>Remediation</h4>
                      <p>{finding.remediation}</p>
                    </div>
                    {finding.false_positive_note && (
                      <div className="detail-block false-positive-note">
                        <h4>False Positive Note</h4>
                        <p><em>{finding.false_positive_note}</em></p>
                      </div>
                    )}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function getRiskColor(score) {
  if (score >= 80) return '#ef4444';
  if (score >= 60) return '#f97316';
  if (score >= 30) return '#eab308';
  return '#10b981';
}

function getRiskClass(score) {
  if (score >= 80) return 'critical';
  if (score >= 60) return 'high';
  if (score >= 30) return 'medium';
  return 'low';
}
