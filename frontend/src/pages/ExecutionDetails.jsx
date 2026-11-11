import { useState, useEffect, useCallback } from 'react';
import { Link, useParams } from 'react-router-dom';
import {
  Shield, ShieldAlert, Clock, FileText, Download, ArrowLeft,
  AlertTriangle, CheckCircle2,
} from 'lucide-react';
import { scans } from '../services/api';
import './ExecutionDetails.css';

function getRiskClass(score) {
  if (score >= 80) return 'critical';
  if (score >= 60) return 'high';
  if (score >= 30) return 'medium';
  return 'low';
}

function getRiskLevel(score) {
  if (score >= 80) return 'Critical';
  if (score >= 60) return 'High';
  if (score >= 30) return 'Medium';
  if (score > 0) return 'Low';
  return 'Clean';
}

function getBadgeClass(status) {
  if (status === 'running' || status === 'queued') return 'running';
  if (status === 'completed') return 'completed';
  if (status === 'failed') return 'failed';
  return '';
}

export default function ExecutionDetails() {
  const { id } = useParams();
  const scanId = Number(id);
  const [scanData, setScanData] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);
  const [downloading, setDownloading] = useState(null);

  const loadScanDetails = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      setScanData(await scans.get(scanId));
    } catch (err) {
      setError(err.message || 'Failed to load scan details.');
    } finally {
      setIsLoading(false);
    }
  }, [scanId]);

  useEffect(() => {
    if (!Number.isFinite(scanId)) {
      setError('Invalid scan ID.');
      setIsLoading(false);
      return;
    }
    loadScanDetails();
  }, [scanId, loadScanDetails]);

  const handleDownload = async (format) => {
    setDownloading(format);
    try {
      if (format === 'pdf') await scans.downloadPdf(scanId);
      else await scans.downloadJson(scanId);
    } catch (err) {
      setError(err.message || 'Download failed.');
    } finally {
      setDownloading(null);
    }
  };

  if (isLoading) {
    return (
      <div className="execution-details-skeleton">
        <div className="skeleton-header" />
        <div className="skeleton-content" />
      </div>
    );
  }

  if (error || !scanData) {
    return (
      <div className="execution-details-error">
        <ShieldAlert size={28} />
        <h3>Scan Unavailable</h3>
        <p>{error || 'No data for this scan.'}</p>
        <Link to="/dashboard">← Back to Dashboard</Link>
      </div>
    );
  }

  const ai = scanData.ai_analysis;
  const findings = scanData.findings || [];
  const timeline = Array.isArray(scanData.transition_history) ? scanData.transition_history : [];

  return (
    <div className="execution-details-page">
      <header className="execution-details-header">
        <div className="header-left">
          <Link to="/dashboard" className="header-back-btn" aria-label="Back to dashboard">
            <ArrowLeft size={16} /> Back
          </Link>
          <h1 className="page-title">{scanData.api_title || scanData.api_name || 'Execution Details'}</h1>
        </div>
        <div className="header-right">
          <span className="scan-id">Scan #{scanData.id}</span>
        </div>
      </header>

      <div className="status-bar">
        <span className={`status-badge ${getBadgeClass(scanData.status)}`}>{scanData.status}</span>
        {scanData.created_at && (
          <span className="scan-id">
            <Clock size={12} /> {new Date(scanData.created_at).toLocaleString()}
          </span>
        )}
      </div>

      <main className="details-main">
        <section className="left-panel">
          <div className="mission-control-panel">
            <div className="mission-header">
              <span className="mission-title">AI MISSION CONTROL</span>
              <span className="mission-subtitle">Scan reasoning pipeline</span>
            </div>

            <div className="mission-steps">
              {timeline.length === 0 ? (
                <div className="mission-step">
                  <span className="step-dot" />
                  <span className="step-label">No transition history recorded</span>
                </div>
              ) : (
                timeline.map((step, index) => (
                  <div key={index} className="mission-step">
                    <span className="step-dot" />
                    <span className="step-label">
                      {step.reason || step.label || `Step ${index + 1}`}
                    </span>
                    <span className={`step-status ${step.to || 'pending'}`}>
                      {step.to || 'pending'}
                    </span>
                    <span className="step-icon"><FileText size={12} /></span>
                  </div>
                ))
              )}
            </div>

            {ai && (
              <div className="ai-analysis-results">
                <div className="analysis-header">
                  <span className="analysis-title">AI Analysis Generated</span>
                </div>
                <div className="analysis-content">
                  {[
                    ['Executive Summary', ai.executive_summary],
                    ['Technical Explanation', ai.technical_explanation],
                    ['Business Impact', ai.business_impact],
                    ['Attack Scenario', ai.attack_scenario],
                    ['Recommended Mitigation', ai.recommended_mitigation],
                  ].map(([label, text]) => (
                    <div key={label} className="analysis-section">
                      <h4>{label}</h4>
                      <p>{text || '—'}</p>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>

          <div className="execution-metrics-panel">
            <div className="metrics-grid">
              <div className="metric-card">
                <div className="metric-value">{scanData.total_endpoints ?? 0}</div>
                <div className="metric-label">Endpoints Scanned</div>
              </div>
              <div className="metric-card">
                <div className="metric-value">{scanData.total_vulnerabilities ?? 0}</div>
                <div className="metric-label">Findings</div>
              </div>
              <div className="metric-card">
                <div className="metric-value">{Math.round(scanData.risk_score ?? 0)}/100</div>
                <div className="metric-label">Risk Score</div>
              </div>
            </div>
          </div>
        </section>

        <section className="right-panel">
          <div className="live-logs-panel">
            <div className="panel-header">
              <span className="panel-title">Findings</span>
              <span className="panel-subtitle">{findings.length} recorded</span>
            </div>
            <div className="logs-container">
              {findings.length === 0 ? (
                <div className="log-entry">
                  <CheckCircle2 size={14} />
                  <span className="log-message">No vulnerabilities were detected.</span>
                </div>
              ) : (
                findings.map((f) => (
                  <div key={f.id} className="log-entry">
                    <AlertTriangle size={14} />
                    <span className="log-message">
                      <strong>{f.vulnerability_name}</strong> — {f.severity} · {f.owasp_category}
                      {f.affected_endpoint ? ` · ${f.affected_endpoint}` : ''}
                    </span>
                  </div>
                ))
              )}
            </div>
          </div>

          <div className="final-report-panel">
            <div className="panel-header">
              <span className="panel-title">Final Report</span>
            </div>
            {scanData.status === 'completed' ? (
              <div className="report-content">
                <p>
                  Scan completed with <strong>{scanData.total_vulnerabilities ?? 0}</strong> findings
                  across <strong>{scanData.total_endpoints ?? 0}</strong> endpoints.
                </p>
                <p>
                  Risk Level:{' '}
                  <span className={getRiskClass(scanData.risk_score || 0)}>
                    {getRiskLevel(scanData.risk_score || 0)}
                  </span>
                </p>

                <div className="download-buttons">
                  <button
                    className="download-pdf-btn"
                    onClick={() => handleDownload('pdf')}
                    disabled={downloading === 'pdf'}
                  >
                    <Download size={14} />
                    {downloading === 'pdf' ? 'Generating...' : 'Download PDF Report'}
                  </button>
                  <button
                    className="download-json-btn"
                    onClick={() => handleDownload('json')}
                    disabled={downloading === 'json'}
                  >
                    <FileText size={14} />
                    {downloading === 'json' ? 'Generating...' : 'Download JSON Report'}
                  </button>
                </div>
              </div>
            ) : (
              <div className="report-progress">
                <Shield size={16} />
                <p>Report becomes available once the scan completes.</p>
              </div>
            )}
          </div>
        </section>
      </main>
    </div>
  );
}
