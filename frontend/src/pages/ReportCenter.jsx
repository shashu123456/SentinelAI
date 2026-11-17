import { useState, useEffect, useMemo } from 'react';
import { Link } from 'react-router-dom';
import {
  FileText, FileJson, File, Calendar, Search,
  Trash2, ExternalLink,
} from 'lucide-react';
import { scans, account } from '../services/api';
import './ReportCenter.css';

const KIND_LABELS = { spec: 'API Spec', deps: 'Dependencies', code: 'SAST' };

const KIND_FILTERS = [
  { value: 'all', label: 'All' },
  { value: 'spec', label: 'API' },
  { value: 'deps', label: 'Dependencies' },
  { value: 'code', label: 'SAST' },
];

export default function ReportCenter() {
  const [scanList, setScanList] = useState([]);
  const [loading, setLoading] = useState(true);
  const [downloading, setDownloading] = useState(null);
  const [isDemo, setIsDemo] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [query, setQuery] = useState('');
  const [kindFilter, setKindFilter] = useState('all');

  const load = () => {
    setLoading(true);
    scans.list()
      .then(data => setScanList(data || []))
      .catch(() => setScanList([]))
      .finally(() => setLoading(false));
  };

  const handleDeleteData = async () => {
    if (!window.confirm('Delete every scan and report on this account? The account itself is kept.')) return;
    setDeleting(true);
    try {
      await account.deleteData();
      setScanList([]);
    } catch (err) {
      console.error('Delete failed:', err);
    } finally {
      setDeleting(false);
    }
  };

  useEffect(() => {
    load();
    setIsDemo(localStorage.getItem('sentinelai_demo') === 'true');
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

  const kpis = useMemo(() => {
    const totalFindings = scanList.reduce((sum, s) => sum + (s.total_vulnerabilities || 0), 0);
    const highRisk = scanList.filter(s => (s.risk_score || 0) >= 60).length;
    const avgRisk = scanList.length
      ? Math.round(scanList.reduce((sum, s) => sum + (s.risk_score || 0), 0) / scanList.length)
      : 0;
    return { scans: scanList.length, totalFindings, highRisk, avgRisk };
  }, [scanList]);

  const visibleScans = useMemo(() => {
    const needle = query.trim().toLowerCase();
    return scanList.filter(scan => {
      const matchesKind = kindFilter === 'all' || scan.kind === kindFilter;
      const matchesQuery = !needle || (scan.api_name || '').toLowerCase().includes(needle);
      return matchesKind && matchesQuery;
    });
  }, [scanList, query, kindFilter]);

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
        <p className="report-header-sub">Export each scan as PDF or JSON.</p>
        {isDemo && (
          <div className="demo-banner" role="note">Demo data — read-only. Sign up to scan your own material.</div>
        )}
      </div>

      {scanList.length === 0 ? (
        <div className="report-empty">
          <FileText size={40} />
          <h3>No scans yet</h3>
          <p>Run a scan first to generate reports.</p>
          <Link to="/scans/new" className="report-empty-btn">Start a Scan</Link>
        </div>
      ) : (
        <>
          <div className="report-kpis">
            <div className="report-kpi">
              <span className="report-kpi-value">{kpis.scans}</span>
              <span className="report-kpi-label">Scans</span>
            </div>
            <div className="report-kpi">
              <span className="report-kpi-value">{kpis.totalFindings}</span>
              <span className="report-kpi-label">Findings</span>
            </div>
            <div className="report-kpi">
              <span className="report-kpi-value">{kpis.highRisk}</span>
              <span className="report-kpi-label">High-risk scans (60+)</span>
            </div>
            <div className="report-kpi">
              <span className="report-kpi-value">{kpis.avgRisk}</span>
              <span className="report-kpi-label">Average risk</span>
            </div>
          </div>

          <div className="report-toolbar">
            <div className="report-search">
              <Search size={15} aria-hidden="true" />
              <input
                type="search"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Search scans by name"
                aria-label="Search scans by name"
              />
            </div>
            <div className="report-filter" role="group" aria-label="Filter by scanner">
              {KIND_FILTERS.map(filter => (
                <button
                  key={filter.value}
                  type="button"
                  className={`report-filter-btn${kindFilter === filter.value ? ' active' : ''}`}
                  aria-pressed={kindFilter === filter.value}
                  onClick={() => setKindFilter(filter.value)}
                >
                  {filter.label}
                </button>
              ))}
            </div>
          </div>

          {visibleScans.length === 0 ? (
            <div className="report-empty report-empty-inline">
              <h3>No scans match this filter</h3>
              <p>Clear the search or choose another scanner.</p>
            </div>
          ) : (
            <div className="report-list">
              {visibleScans.map(scan => (
                <div key={scan.id} className="report-card">
                  <div className="report-card-header">
                    <div className="report-card-icon">
                      <FileText size={18} />
                    </div>
                    <div className="report-card-info">
                      <h3 className="report-card-title">{scan.api_name}</h3>
                      <div className="report-card-meta">
                        {scan.kind && (
                          <span className="report-card-kind">{KIND_LABELS[scan.kind] || scan.kind}</span>
                        )}
                        <span className="report-card-date">
                          <Calendar size={11} />
                          {new Date(scan.created_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}
                        </span>
                        <span className="report-card-findings">
                          {scan.total_vulnerabilities || 0} findings
                        </span>
                        <span className={`report-card-risk ${scan.risk_score >= 60 ? 'danger' : scan.risk_score >= 30 ? 'warning' : 'safe'}`}>
                          Risk {scan.risk_score}
                        </span>
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

          {!isDemo && (
            <div className="report-danger-zone">
              <div>
                <h3 className="report-danger-title">Danger zone</h3>
                <p className="report-danger-desc">
                  Removes every scan and report on this account. The account itself is kept.
                </p>
              </div>
              <button className="report-delete-data" onClick={handleDeleteData} disabled={deleting}>
                <Trash2 size={14} />
                {deleting ? 'Deleting…' : 'Delete my scan data'}
              </button>
            </div>
          )}
        </>
      )}
    </div>
  );
}
