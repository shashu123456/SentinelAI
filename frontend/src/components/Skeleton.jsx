export function SkeletonLine({ width, height = 14, style, className = '' }) {
  return (
    <div
      className={`skeleton-line ${className}`}
      style={{ width: width || '100%', height, ...style }}
    />
  );
}

export function SkeletonCard({ lines = 3, height, delay = 0 }) {
  return (
    <div className="skeleton-card" style={{ animationDelay: `${delay}ms`, ...(height ? { height } : {}) }}>
      {Array.from({ length: lines }).map((_, i) => (
        <div
          key={i}
          className={`skeleton-line ${i === lines - 1 ? 'short' : ''}`}
          style={{ animationDelay: `${delay + i * 40}ms` }}
        />
      ))}
    </div>
  );
}

export function SkeletonTable({ rows = 5, cols = 4 }) {
  return (
    <div className="skeleton-table">
      <div className="skeleton-table-header">
        {Array.from({ length: cols }).map((_, i) => (
          <div
            key={i}
            className="skeleton-line"
            style={{ width: `${50 + Math.random() * 40}%`, animationDelay: `${i * 30}ms` }}
          />
        ))}
      </div>
      {Array.from({ length: rows }).map((_, r) => (
        <div key={r} className="skeleton-table-row" style={{ animationDelay: `${r * 60}ms` }}>
          {Array.from({ length: cols }).map((_, c) => (
            <div
              key={c}
              className="skeleton-line"
              style={{ width: `${30 + Math.random() * 50}%`, animationDelay: `${r * 60 + c * 20}ms` }}
            />
          ))}
        </div>
      ))}
    </div>
  );
}

export function SkeletonMetric({ delay = 0 }) {
  return (
    <div className="skeleton-metric" style={{ animationDelay: `${delay}ms` }}>
      <div className="skeleton-line xshort" style={{ height: '12px' }} />
      <div className="skeleton-line" style={{ width: '40%', height: '28px', marginTop: '8px' }} />
      <div className="skeleton-line short" style={{ height: '6px', marginTop: '8px' }} />
    </div>
  );
}

export function SkeletonAvatar({ size = 32, delay = 0 }) {
  return (
    <div
      className="skeleton-circle"
      style={{ width: size, height: size, animationDelay: `${delay}ms` }}
    />
  );
}

export function SkeletonButton({ width = 120, height = 36, delay = 0 }) {
  return (
    <div
      className="skeleton"
      style={{ width, height, borderRadius: 'var(--radius)', animationDelay: `${delay}ms` }}
    />
  );
}

export function DashboardSkeleton() {
  return (
    <div className="skeleton-page">
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '24px' }}>
        <div>
          <div className="skeleton-line" style={{ width: '200px', height: '22px' }} />
          <div className="skeleton-line short" style={{ width: '300px', height: '14px', marginTop: '6px', animationDelay: '40ms' }} />
        </div>
        <SkeletonButton width={140} height={38} delay={60} />
      </div>
      {/* Metrics */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '16px', marginBottom: '24px' }}>
        {[0, 1, 2, 3].map(i => <SkeletonMetric key={i} delay={i * 60} />)}
      </div>
      {/* Charts */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '14px', marginBottom: '14px' }}>
        <SkeletonCard lines={4} delay={240} />
        <SkeletonCard lines={4} delay={280} />
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '14px', marginBottom: '24px' }}>
        <SkeletonCard lines={4} delay={320} />
        <SkeletonCard lines={4} delay={360} />
      </div>
      {/* Table */}
      <SkeletonTable rows={5} cols={5} />
    </div>
  );
}

export function ScanResultSkeleton() {
  return (
    <div className="skeleton-page">
      <div className="skeleton-line short" style={{ width: '140px', height: '14px', marginBottom: '20px' }} />
      <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '28px' }}>
        <SkeletonAvatar size={40} delay={40} />
        <div>
          <div className="skeleton-line" style={{ width: '200px', height: '20px', animationDelay: '60ms' }} />
          <div className="skeleton-line short" style={{ width: '80px', height: '14px', marginTop: '4px', animationDelay: '80ms' }} />
        </div>
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: '200px 1fr auto', gap: '16px', marginBottom: '32px' }}>
        <SkeletonCard lines={3} height="200px" delay={100} />
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: '8px' }}>
          {[0, 1, 2, 3, 4].map(i => (
            <div key={i} className="skeleton-metric" style={{ animationDelay: `${120 + i * 40}ms` }} />
          ))}
        </div>
        <SkeletonCard lines={2} delay={320} />
      </div>
      <SkeletonCard lines={2} delay={400} />
      <div style={{ marginTop: '16px' }}>
        <SkeletonTable rows={3} cols={4} />
      </div>
    </div>
  );
}
