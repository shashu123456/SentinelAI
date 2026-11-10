import React, { useState, useEffect, useParams, useRef } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { 
  Shield, Clock, Llm, Code2, Zap, TrendingUp, FileText, Settings, 
  AlertCircle, Info, Layout, BarChart, ShieldCheck, Palette, Eye, 
  Search, Folder, Document, FileText2, Clock as ClockIcon, 
  Link as LinkIcon, BarChart as BarChartIcon, ShieldExclamation, Zap as ZapIcon 
} from 'lucide-react';
import { scans } from '../services/api';
import './ExecutionDetails.css';

/* ── Execution Details Page ──────────────────────────────────── */
export default function ExecutionDetails() {
  const { scanId } = useParams();
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);
  const navigate = useNavigate();
  const [scanData, setScanData] = useState(null);

  // Load scan details when component mounts
  useEffect(() => {
    if (scanId) {
      loadScanDetails();
    } else {
      setError('Scan ID not provided');
      setIsLoading(false);
    }
  }, [scanId]);

  const loadScanDetails = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const detail = await scans.get(parseInt(scanId, 10));
      setScanData(detail);
    } catch (err) {
      console.error('Failed to load scan details:', err);
      setError('Failed to load scan details. The scan may not exist or you may not have access.');
    } finally {
      setIsLoading(false);
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

  if (error) {
    return (
      <div className="execution-details-error">
        <ShieldAlert size={28} />
        <h3>Scan Not Found</h3>
        <p>{error}</p>
        <button onClick={() => window.history.back()}>← Back to Dashboard</button>
      </div>
    );
  }

  // If no scan data, show empty state
  if (!scanData) {
    return (
      <div className="execution-details-empty">
        <Shield size={64} />
        <h3>Scan Details</h3>
        <p>Select a scan from the dashboard to view its execution details.</p>
        <Link to="/" className="btn-primary">← Back to Dashboard</Link>
      </div>
    );
  }

  const aiAnalysis = scanData.ai_analysis;
  const metrics = {
    total_endpoints: scanData.total_endpoints || 0,
    total_findings: scanData.total_vulnerabilities || 0,
  };

  // Render status badge
  const getBadgeClass = (status: string) => {
    if (status === 'running' || status === 'queued') return 'running';
    if (status === 'completed') return 'completed';
    if (status === 'failed') return 'failed';
    return '';
  };

  return (
    <div className="execution-details-page">
      {/* === Header === */}
      <header className="execution-details-header">
        <div className="header-left">
          <Link 
            to="/" 
            className="header-back-btn"
            aria-label="Back to dashboard"
          >
            <LinkIcon size={16} /> Back
          </Link>
          <h1 className="page-title">Execution Details</h1>
        </div>
        <div className="header-right">
          <span className="scan-id">Scan #{scanId}</span>
        </div>
      </header>

      {/* === Status Bar === */}
      <div className="status-bar">
        <span className={`status-badge ${getBadgeClass(scanData.status)}`}>
          {scanData.status}
        </span>
      </div>

      {/* === Main Content Area === */}
      <main className="details-main">
        {/* LEFT PANEL: Mission Control + Timeline + AI Analysis */}
        <section className="left-panel">
          {/* Mission Control */}
          <div className="mission-control-panel">
            <div className="mission-header">
              <span className="mission-title">AI MISSION CONTROL</span>
              <span className="mission-subtitle">Scan reasoning pipeline</span>
            </div>

            <div className="mission-steps">
              {scanData.transition_history?.map((step: any, index: number) => (
                <div key={index} className="mission-step">
                  <span className="step-dot" />
                  <span className="step-label">{step.reason || step.label || `Step ${index + 1}`}</span>
                  <span className={`step-status ${step.to || 'pending'}`}>
                    {step.to || 'pending'}
                  </span>
                  <span className="step-icon">{FileTextIcon}</span>
                </div>
              ))}
            </div>

            {/* AI Analysis Results */}
            {aiAnalysis && (
              <div className="ai-analysis-results">
                <div className="analysis-header">
                  <span className="analysis-title">AI Analysis Generated</span>
                  <span className="confidence-badge">Confidence: {aiAnalysis.confidence || 95}%</span>
                </div>

                <div className="analysis-content">
                  <div className="analysis-section">
                    <h4>Executive Summary</h4>
                    <p>{aiAnalysis.executive_summary || '—'}</p>
                  </div>
                  <div className="analysis-section">
                    <h4>Technical Explanation</h4>
                    <p>{aiAnalysis.technical_explanation || '—'}</p>
                  </div>
                  <div className="analysis-section">
                    <h4>Business Impact</h4>
                    <p>{aiAnalysis.business_impact || '—'}</p>
                  </div>
                  <div className="analysis-section">
                    <h4>Attack Scenario</h4>
                    <p>{aiAnalysis.attack_scenario || '—'}</p>
                  </div>
                  <div className="analysis-section">
                    <h4>Recommended Mitigation</h4>
                    <p>{aiAnalysis.recommended_mitigation || '—'}</p>
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Execution Metrics */}
          {metrics && (
            <div className="execution-metrics-panel">
              <div className="metrics-grid">
                <div className="metric-card">
                  <div className="metric-value">{metrics.total_endpoints}</div>
                  <div className="metric-label">Endpoints Scanned</div>
                </div>
                <div className="metric-card">
                  <div className="metric-value">{metrics.total_findings}</div>
                  <div className="metric-label">Findings</div>
                </div>
                <div className="metric-card">
                  <div className="metric-value">{Math.round(scanData.risk_score || 0)}/100</div>
                  <div className="metric-label">Risk Score</div>
                </div>
              </div>
            </div>
          )}
        </section>

        {/* RIGHT PANEL: Live Logs + Report */}
        <section className="right-panel">
          {/* Live Logs */}
          <div className="live-logs-panel">
            <div className="panel-header">
              <span className="panel-title">Live Logs</span>
              <span className="panel-subtitle">Execution timeline</span>
            </div>
            <div className="logs-container">
              {scanData.transition_history?.map((step: any, index: number) => (
                <div key={index} className="log-entry">
                  <span className="log-timestamp">{new Date(step.at).toLocaleTimeString()}</span>
                  <span className="log-icon">{FileTextIcon}</span>
                  <span className="log-message">{step.reason || step.label || `Step ${index + 1}`}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Final Report */}
          <div className="final-report-panel">
            <div className="panel-header">
              <span className="panel-title">Final Report</span>
            </div>
            {scanData.status === 'completed' && (
              <div className="report-content">
                <p>Scan completed successfully with <strong>{metrics?.total_findings}</strong> findings.</p>
                <p>Risk Level: <span className={getRiskClass(scanData.risk_score || 0)}>{getRiskLevel(scanData.risk_score || 0)}</span></p>
                
                {aiAnalysis && (
                  <div className="report-sections">
                    <h4>Generated Reports</h4>
                    <ul>
                      <li>PDF Report - Comprehensive vulnerability analysis</li>
                      <li>JSON Report - Machine-readable findings</li>
                      <li>Executive Summary - AI-generated business impact</li>
                    </ul>
                  </div>
                )}

                <div className="download-buttons">
                  <button className="download-pdf-btn">
                    <PDF size={14} /> Download PDF Report
                  </button>
                  <button className="download-json-btn">
                    <FileText2 size={14} /> Download JSON Report
                  </button>
                </div>
              </div>
            )}

            {/* Progress state */}
            {scanData.status !== 'completed' && (
              <div className="report-progress">
                <p>Generating report...</p>
              </div>
            )}
          </div>
        </section>
      </main>
    </div>
  );
}

/* ── Helper Functions ──────────────────────────────────────── */
function getRiskClass(score: number) {
  if (score >= 80) return 'critical';
  if (score >= 60) return 'high';
  if (score >= 30) return 'medium';
  return 'low';
}

function getRiskLevel(score: number) {
  if (score >= 80) return 'Critical';
  if (score >= 60) return 'High';
  if (score >= 30) return 'Medium';
  if (score > 0) return 'Low';
  return 'Clean';
}