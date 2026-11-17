import { useState, useEffect, useCallback, useMemo } from 'react';
import { Link, useParams } from 'react-router-dom';
import {
  Shield, ShieldAlert, Clock, FileText, Download, ArrowLeft,
  AlertTriangle, CheckCircle2,
} from 'lucide-react';
import { scans } from '../services/api';
import './ExecutionDetails.css';

const SEVERITY_ORDER = ['critical', 'high', 'medium', 'low', 'info'];
const SEVERITY_LABELS = {
  critical: 'Critical', high: 'High', medium: 'Medium', low: 'Low', info: 'Info',
};

function severityOf(finding) {
  const value = String(finding.severity || '').toLowerCase();
  return SEVERITY_ORDER.includes(value) ? value : 'info';
}

function getRiskLevel(score) {
  if (score >= 80) return 'Critical';
  if (score >= 60) return 'High';
  if (score >= 30) return 'Medium';
  if (score > 0) return 'Low';
  return 'Clean';
}

function getRiskClass(score) {
  return getRiskLevel(score).toLowerCase();
}

const KIND_LABELS = {
  spec: 'API spec',
  deps: 'Dependencies',
  code: 'SAST',
};

function getBadgeClass(status) {
  if (status === 'running' || status === 'queued') return 'running';
  if (status === 'completed') return 'completed';
  if (status === 'failed') return 'failed';
  return '';
}

/** One finding: severity, identity, the fix instruction, then collapsible detail. */
function FindingRow({ finding }) {
  const severity = severityOf(finding);
  const technical = [
    ['Description', finding.description],
    ['Evidence', finding.evidence],
    ['Impact', finding.impact],
    ['Technical impact', finding.technical_impact],
    ['Detection reason', finding.detection_reason],
  ].filter(([, text]) => text);

  return (
    <article className={`finding-row finding-${severity}`}>
      <div className="finding-head">
        <span className={`finding-severity severity-${severity}`}>
          {SEVERITY_LABELS[severity]}
        </span>
        <h3 className="finding-name">{finding.vulnerability_name}</h3>
        <div className="finding-tags">
          {finding.cwe_id && <span className="finding-tag">{finding.cwe_id}</span>}
          {finding.owasp_category && <span className="finding-tag">{finding.owasp_category}</span>}
          {typeof finding.cvss_score === 'number' && (
            <span className="finding-tag">CVSS {finding.cvss_score.toFixed(1)}</span>
          )}
        </div>
      </div>

      {finding.affected_endpoint && (
        <p className="finding-endpoint">
          <span className="finding-method">{finding.affected_method || 'ENDPOINT'}</span>
          <code>{finding.affected_endpoint}</code>
        </p>
      )}

      <div className="finding-fix">
        <span className="finding-fix-label">Fix</span>
        <p>{finding.remediation || finding.fix_recommendation || 'No fix instruction was recorded for this finding.'}</p>
      </div>

      {technical.length > 0 && (
        <details className="finding-details">
          <summary>Technical detail</summary>
          <dl className="finding-dl">
            {technical.map(([label, text]) => (
              <div key={label}>
                <dt>{label}</dt>
                <dd>{text}</dd>
              </div>
            ))}
          </dl>
        </details>
      )}
    </article>
  );
}

export default function ExecutionDetails() {
  const { id } = useParams();
  const scanId = Number(id);
  const [scanData, setScanData] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);
  const [downloading, setDownloading] = useState(null);
  const [severityFilter, setSeverityFilter] = useState('all');

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

  const findings = scanData?.findings || [];

  const severityCounts = useMemo(() => {
    const counts = { critical: 0, high: 0, medium: 0, low: 0, info: 0 };
    findings.forEach((f) => { counts[severityOf(f)] += 1; });
    return counts;
  }, [findings]);

  const visibleFindings = useMemo(
    () => (severityFilter === 'all'
      ? findings
      : findings.filter((f) => severityOf(f) === severityFilter)),
    [findings, severityFilter],
  );

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
        <Link to="/reports">← Back to Reports</Link>
      </div>
    );
  }

  const analysis = scanData.ai_analysis;
  const timeline = Array.isArray(scanData.transition_history) ? scanData.transition_history : [];
  const riskScore = Math.round(scanData.risk_score ?? 0);
  const riskLevel = getRiskLevel(riskScore);

  const analysisSections = analysis
    ? [
        ['Executive summary', analysis.executive_summary],
        ['Technical explanation', analysis.technical_explanation],
        ['Business impact', analysis.business_impact],
        ['Attack scenario', analysis.attack_scenario],
        ['Recommended mitigation', analysis.recommended_mitigation],
      ].filter(([, text]) => text)
    : [];

  return (
    <div className="execution-details-page">
      <header className="execution-details-header">
        <div className="header-left">
          <Link to="/reports" className="header-back-btn" aria-label="Back to reports">
            <ArrowLeft size={16} /> Reports
          </Link>
          <h1 className="page-title">{scanData.api_title || scanData.api_name || 'Scan details'}</h1>
        </div>
        <div className="header-right">
          <span className="scan-id">Scan #{scanData.id}</span>
        </div>
      </header>

      <div className="status-bar">
        <span className={`status-badge ${getBadgeClass(scanData.status)}`}>{scanData.status}</span>
        {scanData.kind && <span className="scan-id">{KIND_LABELS[scanData.kind] || scanData.kind}</span>}
        {scanData.created_at && (
          <span className="scan-id">
            <Clock size={12} /> {new Date(scanData.created_at).toLocaleString()}
          </span>
        )}
      </div>

      <section className="summary-section" aria-label="Scan summary">
        <div className="summary-kpis">
          <div className="metric-card">
            <div className="metric-value">{scanData.total_endpoints ?? 0}</div>
            <div className="metric-label">Endpoints scanned</div>
          </div>
          <div className="metric-card">
            <div className="metric-value">{scanData.total_vulnerabilities ?? findings.length}</div>
            <div className="metric-label">Findings</div>
          </div>
          <div className="metric-card">
            <div className="metric-value">{riskScore}<span className="metric-suffix">/100</span></div>
            <div className="metric-label">Risk score</div>
          </div>
          <div className="metric-card metric-card-level">
            <div className={`metric-value risk-${getRiskClass(riskScore)}`}>{riskLevel}</div>
            <div className="metric-label">Risk level</div>
          </div>
        </div>

        <div className="severity-breakdown" aria-label="Findings by severity">
          {SEVERITY_ORDER.map((severity) => (
            <div key={severity} className={`severity-cell severity-${severity}`}>
              <span className="severity-cell-dot" aria-hidden="true" />
              <span className="severity-cell-count">{severityCounts[severity]}</span>
              <span className="severity-cell-label">{SEVERITY_LABELS[severity]}</span>
            </div>
          ))}
        </div>
      </section>

      <section className="findings-section" aria-label="Findings">
        <div className="panel-header">
          <span className="panel-title">Findings</span>
          <span className="panel-subtitle">{findings.length} recorded</span>
        </div>

        {findings.length > 0 && (
          <div className="severity-filter" role="group" aria-label="Filter findings by severity">
            <button
              type="button"
              className={`severity-filter-btn${severityFilter === 'all' ? ' active' : ''}`}
              aria-pressed={severityFilter === 'all'}
              onClick={() => setSeverityFilter('all')}
            >
              All <span className="severity-filter-count">{findings.length}</span>
            </button>
            {SEVERITY_ORDER.filter((s) => severityCounts[s] > 0).map((severity) => (
              <button
                key={severity}
                type="button"
                className={`severity-filter-btn severity-filter-${severity}${severityFilter === severity ? ' active' : ''}`}
                aria-pressed={severityFilter === severity}
                onClick={() => setSeverityFilter(severity)}
              >
                {SEVERITY_LABELS[severity]} <span className="severity-filter-count">{severityCounts[severity]}</span>
              </button>
            ))}
          </div>
        )}

        <div className="findings-list">
          {findings.length === 0 ? (
            <div className="findings-empty">
              <CheckCircle2 size={18} />
              <span>No vulnerabilities were detected.</span>
            </div>
          ) : visibleFindings.length === 0 ? (
            <div className="findings-empty">
              <AlertTriangle size={18} />
              <span>No {SEVERITY_LABELS[severityFilter]} findings in this scan.</span>
            </div>
          ) : (
            visibleFindings.map((finding) => <FindingRow key={finding.id} finding={finding} />)
          )}
        </div>
      </section>

      <div className="details-columns">
        <section className="analysis-panel" aria-label="Scan analysis">
          <div className="panel-header">
            <span className="panel-title">Scan analysis</span>
            {scanData.completed_at && (
              <span className="panel-subtitle">
                Completed {new Date(scanData.completed_at).toLocaleDateString()}
              </span>
            )}
          </div>

          {timeline.length > 0 && (
            <ul className="mission-steps">
              {timeline.map((step, index) => (
                <li key={index} className="mission-step">
                  <span className="step-dot" aria-hidden="true" />
                  <span className="step-label">
                    {step.reason || step.label || `Step ${index + 1}`}
                  </span>
                  <span className={`step-status ${step.to || 'pending'}`}>
                    {step.to || 'pending'}
                  </span>
                </li>
              ))}
            </ul>
          )}

          {analysisSections.length > 0 && (
            <div className="analysis-results">
              <h3 className="analysis-title">Analysis summary</h3>
              <dl className="analysis-content">
                {analysisSections.map(([label, text]) => (
                  <div key={label} className="analysis-section">
                    <dt>{label}</dt>
                    <dd>{text}</dd>
                  </div>
                ))}
              </dl>
            </div>
          )}
        </section>

        <section className="final-report-panel" aria-label="Export">
          <div className="panel-header">
            <span className="panel-title">Export</span>
          </div>
          {scanData.status === 'completed' ? (
            <div className="report-content">
              <p>
                <strong>{scanData.total_vulnerabilities ?? 0}</strong> findings across{' '}
                <strong>{scanData.total_endpoints ?? 0}</strong> endpoints.
                Risk level: <strong>{riskLevel}</strong>.
              </p>
              <div className="download-buttons">
                <button
                  className="download-pdf-btn"
                  onClick={() => handleDownload('pdf')}
                  disabled={downloading === 'pdf'}
                >
                  <Download size={14} />
                  {downloading === 'pdf' ? 'Generating…' : 'PDF report'}
                </button>
                <button
                  className="download-json-btn"
                  onClick={() => handleDownload('json')}
                  disabled={downloading === 'json'}
                >
                  <FileText size={14} />
                  {downloading === 'json' ? 'Generating…' : 'JSON export'}
                </button>
              </div>
            </div>
          ) : (
            <div className="report-progress">
              <Shield size={16} />
              <p>The report becomes available once the scan completes.</p>
            </div>
          )}
        </section>
      </div>
    </div>
  );
}
