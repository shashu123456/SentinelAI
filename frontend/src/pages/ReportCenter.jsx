import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import {
  FileText, Download, FileJson, File, Calendar, Clock,
  CheckCircle2, AlertCircle, ExternalLink,
} from 'lucide-react';
import { scans } from '../services/api';
import './ReportCenter.css';

export default function ReportCenter() {
  const [scanList, setScanList] = useState([]);
  const [loading, setLoading] = useState(true);
  const [downloading, setDownloading] = useState(null);

  useEffect(() => {
    scans.list()
      .then(data => setScanList(data || []))
      .catch(() => setScanList([]))
      .finally(() => setLoading(false));
  }, []);

  const handleDownload = async (scanId, format) => {
    setDownloading(`${scanId}-${format}`);
    try {
      if (format === 'pdf') {
        await scans.downloadPdf(scanId);
      } else {
        await scans.downloadJson(scanId);
      }
    } catch (err) {
      console.error('Download failed:', err);
    } finally {
      setDownloading(null);
    }
  };

  if (loading) {
    return (
      <div className="report-loading">
        <div className="page-loader-spinner" />
        <p>Loading reports...</p>
      </div>
    );
  }

  return (
    <div className="report-page">
      <div className="report-header">
        <div className="report-header-badge"><FileText size={12} /> REPORT CENTER</div>
        <h1 className="report-header-title">Reports</h1>
        <p className="report-header-sub">Generate executive, technical, and compliance reports</p>
      </div>

      {scanList.length === 0 ? (
        <div className="report-empty">
          <FileText size={40} />
          <h3>No scans yet</h3>
          <p>Run a scan first to generate reports.</p>
          <Link to="/new-scan" className="report-empty-btn">Start a Scan</Link>
        </div>
      ) : (
        <div className="report-list">
          {scanList.map(scan => (
            <div key={scan.id} className="report-card">
              <div className="report-card-header">
                <div className="report-card-icon">
                  <FileText size={18} />
                </div>
                <div className="report-card-info">
                  <h3 className="report-card-title">{scan.api_name}</h3>
                  <div className="report-card-meta">
                    <span className="report-card-date">
                      <Calendar size={11} />
                      {new Date(scan.created_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}
                    </span>
                    <span className="report-card-findings">
                      {scan.total_vulnerabilities || 0} findings
                    </span>
                    {scan.risk_score > 0 && (
                      <span className={`report-card-risk ${scan.risk_score >= 70 ? 'danger' : scan.risk_score >= 40 ? 'warning' : 'safe'}`}>
                        Risk: {scan.risk_score}
                      </span>
                    )}
                  </div>
                </div>
                <Link to={`/scan/${scan.id}`} className="report-card-view">
                  View Scan <ExternalLink size={12} />
                </Link>
              </div>

              <div className="report-card-actions">
                <button
                  className="report-download-btn pdf"
                  onClick={() => handleDownload(scan.id, 'pdf')}
                  disabled={downloading === `${scan.id}-pdf`}
                >
                  <File size={14} />
                  {downloading === `${scan.id}-pdf` ? 'Generating...' : 'PDF Report'}
                </button>
                <button
                  className="report-download-btn json"
                  onClick={() => handleDownload(scan.id, 'json')}
                  disabled={downloading === `${scan.id}-json`}
                >
                  <FileJson size={14} />
                  {downloading === `${scan.id}-json` ? 'Generating...' : 'JSON Export'}
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
