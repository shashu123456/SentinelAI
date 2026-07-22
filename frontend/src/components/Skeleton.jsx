export function SkeletonCard({ lines = 3, height }) {
  return (
    <div className="skeleton-card" style={height ? { height } : {}}>
      {Array.from({ length: lines }).map((_, i) => (
        <div key={i} className={`skeleton-line ${i === lines - 1 ? 'short' : ''}`} />
      ))}
    </div>
  );
}

export function SkeletonTable({ rows = 5, cols = 4 }) {
  return (
    <div className="skeleton-table">
      <div className="skeleton-table-header">
        {Array.from({ length: cols }).map((_, i) => (
          <div key={i} className="skeleton-line" style={{ width: `${60 + Math.random() * 40}%` }} />
        ))}
      </div>
      {Array.from({ length: rows }).map((_, r) => (
        <div key={r} className="skeleton-table-row">
          {Array.from({ length: cols }).map((_, c) => (
            <div key={c} className="skeleton-line" style={{ width: `${40 + Math.random() * 50}%` }} />
          ))}
        </div>
      ))}
    </div>
  );
}

export function SkeletonMetric() {
  return (
    <div className="skeleton-metric">
      <div className="skeleton-line short" style={{ width: '60%', height: '12px' }} />
      <div className="skeleton-line" style={{ width: '40%', height: '28px', marginTop: '8px' }} />
      <div className="skeleton-line short" style={{ width: '80%', height: '6px', marginTop: '8px' }} />
    </div>
  );
}

export function DashboardSkeleton() {
  return (
    <div className="skeleton-page">
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '24px' }}>
        <div>
          <div className="skeleton-line" style={{ width: '200px', height: '22px' }} />
          <div className="skeleton-line short" style={{ width: '300px', height: '14px', marginTop: '6px' }} />
        </div>
        <div className="skeleton-line" style={{ width: '120px', height: '36px', borderRadius: '8px' }} />
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: '1.4fr 1fr 1fr 1fr', gap: '16px', marginBottom: '24px' }}>
        {[1,2,3,4].map(i => <SkeletonMetric key={i} />)}
      </div>
      <SkeletonTable rows={5} cols={5} />
    </div>
  );
}

export function ScanResultSkeleton() {
  return (
    <div className="skeleton-page">
      <div className="skeleton-line short" style={{ width: '140px', height: '14px', marginBottom: '20px' }} />
      <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '28px' }}>
        <div className="skeleton-circle" style={{ width: '40px', height: '40px' }} />
        <div>
          <div className="skeleton-line" style={{ width: '200px', height: '20px' }} />
          <div className="skeleton-line short" style={{ width: '80px', height: '14px', marginTop: '4px' }} />
        </div>
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: '200px 1fr auto', gap: '16px', marginBottom: '32px' }}>
        <div className="skeleton-card" style={{ height: '200px' }} />
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: '8px' }}>
          {[1,2,3,4,5].map(i => <div key={i} className="skeleton-card" style={{ height: '80px' }} />)}
        </div>
        <div className="skeleton-card" style={{ width: '120px' }} />
      </div>
      <SkeletonCard lines={2} />
      <div style={{ marginTop: '16px' }}>
        <SkeletonTable rows={3} cols={4} />
      </div>
    </div>
  );
}
