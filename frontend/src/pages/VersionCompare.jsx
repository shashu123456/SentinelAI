import { useState, useEffect } from 'react';
import { GitCompare, ArrowRight, TrendingUp, TrendingDown, Minus, Plus, CheckCircle, XCircle, AlertTriangle } from 'lucide-react';
import { SkeletonCard } from '../components/Skeleton';
import { enterprise } from '../services/enterprise';

export default function VersionCompare() {
  const [comparison, setComparison] = useState(null);
  const [loading, setLoading] = useState(false);
  const [scanId1, setScanId1] = useState('');
  const [scanId2, setScanId2] = useState('');
  const [error, setError] = useState('');

  const compare = async () => {
    if (!scanId1 || !scanId2) return;
    setLoading(true);
    setError('');
    try {
      const data = await enterprise.compare(scanId1, scanId2);
      setComparison(data);
    } catch (e) { setError(e.message); } finally { setLoading(false); }
  };

  return (
    <div className="page-content">
      <div className="dash-hero">
        <div>
          <h1 className="dash-hero-title">Version Comparison</h1>
          <p className="dash-hero-sub">Compare two scans side-by-side to track security improvements</p>
        </div>
      </div>

      <div className="dash-panel" style={{ marginTop: 20, padding: 24 }}>
        <div style={{ display: 'flex', gap: 16, alignItems: 'flex-end' }}>
          <div className="form-group" style={{ flex: 1 }}>
            <label>Scan 1 (Baseline)</label>
            <input type="number" value={scanId1} onChange={e => setScanId1(e.target.value)} placeholder="Scan ID" />
          </div>
          <div style={{ color: 'var(--text-muted)', paddingBottom: 10 }}><ArrowRight size={20} /></div>
          <div className="form-group" style={{ flex: 1 }}>
            <label>Scan 2 (Compare)</label>
            <input type="number" value={scanId2} onChange={e => setScanId2(e.target.value)} placeholder="Scan ID" />
          </div>
          <button className="btn-primary" onClick={compare} disabled={!scanId1 || !scanId2 || loading}>
            <GitCompare size={14} /> {loading ? 'Comparing...' : 'Compare'}
          </button>
        </div>
        {error && <div className="error-banner" style={{ marginTop: 12 }}>{error}</div>}
      </div>

      {loading && <div style={{ marginTop: 20 }}><SkeletonCard lines={4} /></div>}

      {comparison && !loading && (
        <>
          {/* Summary Row */}
          <div className="dash-core-row" style={{ marginTop: 16 }}>
            <div className="dash-core-card">
              <div className="dash-core-data">
                <span className="dash-core-num">{comparison.scan_1?.risk_score || 0}</span>
                <span className="dash-core-label">Baseline Risk</span>
              </div>
            </div>
            <div className="dash-core-card">
              <div className="dash-core-data">
                <span className="dash-core-num">{comparison.scan_2?.risk_score || 0}</span>
                <span className="dash-core-label">Compare Risk</span>
              </div>
            </div>
            <div className={`dash-core-card ${comparison.comparison?.risk_score_change < 0 ? '' : 'danger'}`}>
              <div className="dash-core-data">
                <span className="dash-core-num" style={{ color: comparison.comparison?.risk_score_change < 0 ? 'var(--accent-green)' : 'var(--accent-red)' }}>
                  {comparison.comparison?.risk_score_change > 0 ? '+' : ''}{comparison.comparison?.risk_score_change || 0}
                </span>
                <span className="dash-core-label">Risk Score Change</span>
              </div>
            </div>
            <div className="dash-core-card">
              <div className="dash-core-data">
                <span className="dash-core-num">{comparison.comparison?.findings_change > 0 ? '+' : ''}{comparison.comparison?.findings_change || 0}</span>
                <span className="dash-core-label">Findings Change</span>
              </div>
            </div>
          </div>

          {/* Changes */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16, marginTop: 16 }}>
            {/* New Findings */}
            <div className="dash-panel">
              <div className="dash-panel-header">
                <Plus size={14} style={{ color: 'var(--accent-red)' }} />
                <span className="dash-panel-title">NEW FINDINGS ({comparison.comparison?.new_findings?.length || 0})</span>
              </div>
              <div style={{ maxHeight: 200, overflow: 'auto' }}>
                {(comparison.comparison?.new_findings || []).map((f, i) => (
                  <div key={i} style={{ padding: '10px 16px', borderBottom: '1px solid var(--border)', display: 'flex', justifyContent: 'space-between' }}>
                    <span style={{ fontSize: 13, color: 'var(--text-primary)' }}>{f.name}</span>
                    <span className={`sev-badge ${f.severity.toLowerCase()}`}>{f.severity}</span>
                  </div>
                ))}
                {(!comparison.comparison?.new_findings || comparison.comparison.new_findings.length === 0) && (
                  <div style={{ padding: 20, textAlign: 'center', color: 'var(--text-muted)', fontSize: 12 }}>No new findings</div>
                )}
              </div>
            </div>

            {/* Fixed Findings */}
            <div className="dash-panel">
              <div className="dash-panel-header">
                <CheckCircle size={14} style={{ color: 'var(--accent-green)' }} />
                <span className="dash-panel-title">FIXED FINDINGS ({comparison.comparison?.fixed_findings?.length || 0})</span>
              </div>
              <div style={{ maxHeight: 200, overflow: 'auto' }}>
                {(comparison.comparison?.fixed_findings || []).map((f, i) => (
                  <div key={i} style={{ padding: '10px 16px', borderBottom: '1px solid var(--border)', display: 'flex', justifyContent: 'space-between' }}>
                    <span style={{ fontSize: 13, color: 'var(--text-primary)' }}>{f.name}</span>
                    <span className={`sev-badge ${f.severity.toLowerCase()}`}>{f.severity}</span>
                  </div>
                ))}
                {(!comparison.comparison?.fixed_findings || comparison.comparison.fixed_findings.length === 0) && (
                  <div style={{ padding: 20, textAlign: 'center', color: 'var(--text-muted)', fontSize: 12 }}>No fixed findings</div>
                )}
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
