import { useMemo } from 'react';
import {
  PieChart, Pie, Cell, ResponsiveContainer, Tooltip, Legend,
  BarChart, Bar, XAxis, YAxis, CartesianGrid,
  LineChart, Line,
} from 'recharts';
import './Charts.css';

/* Chart colours live in styles/tokens.css. SVG presentation attributes cannot
   resolve var(), so tokens are resolved to concrete values at render time. */
function token(name, fallback) {
  if (typeof window === 'undefined' || !document?.documentElement) return fallback;
  const value = getComputedStyle(document.documentElement).getPropertyValue(name).trim();
  return value || fallback;
}

function severityColors() {
  return {
    Critical: token('--severity-critical', '#D92D20'),
    High: token('--severity-high', '#E8590C'),
    Medium: token('--severity-medium', '#B54708'),
    Low: token('--severity-low', '#A9D41C'),
    Info: token('--text-tertiary', '#B0AAFF'),
  };
}

function chartTheme() {
  return {
    bg: 'transparent',
    grid: token('--chart-grid', 'rgba(33,24,49,0.10)'),
    axisLine: token('--chart-axis', 'rgba(33,24,49,0.18)'),
    tick: token('--chart-tick', '#4A3A63'),
    tooltipBg: token('--bg-elevated', '#EAE8FF'),
    tooltipBorder: token('--border-subtle', '#C9C5FF'),
    tooltipText: token('--text-primary', '#211831'),
  };
}

function CustomTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null;
  return (
    <div className="chart-tooltip">
      {label && <div className="chart-tooltip-label">{label}</div>}
      {payload.map((entry, i) => (
        <div key={i} className="chart-tooltip-item">
          <span className="chart-tooltip-dot" style={{ background: entry.color || entry.fill }} />
          <span className="chart-tooltip-name">{entry.name}:</span>
          <span className="chart-tooltip-value">{entry.value}</span>
        </div>
      ))}
    </div>
  );
}

export function SeverityDonut({ distribution }) {
  const SEVERITY_COLORS = severityColors();
  const data = useMemo(() => {
    if (!distribution) return [];
    return Object.entries(distribution)
      .filter(([, v]) => v > 0)
      .map(([name, value]) => ({ name, value }));
  }, [distribution]);

  const total = useMemo(() => data.reduce((s, d) => s + d.value, 0), [data]);

  if (!data.length) {
    return (
      <div className="chart-empty">
        <span className="chart-empty-text">No findings yet</span>
      </div>
    );
  }

  return (
    <div className="chart-container">
      <ResponsiveContainer width="100%" height={220}>
        <PieChart>
          <Pie
            data={data}
            cx="50%"
            cy="50%"
            innerRadius={55}
            outerRadius={80}
            paddingAngle={3}
            dataKey="value"
            strokeWidth={0}
            animationBegin={0}
            animationDuration={800}
          >
            {data.map((entry) => (
              <Cell
                key={entry.name}
                fill={SEVERITY_COLORS[entry.name] || SEVERITY_COLORS.Info}
              />
            ))}
          </Pie>
          <Tooltip content={<CustomTooltip />} />
          <text
            x="50%"
            y="48%"
            textAnchor="middle"
            dominantBaseline="middle"
            className="chart-center-number"
          >
            {total}
          </text>
          <text
            x="50%"
            y="58%"
            textAnchor="middle"
            dominantBaseline="middle"
            className="chart-center-label"
          >
            TOTAL
          </text>
        </PieChart>
      </ResponsiveContainer>
      <div className="chart-legend">
        {data.map((entry) => (
          <div key={entry.name} className="chart-legend-item">
            <span
              className="chart-legend-dot"
              style={{ background: SEVERITY_COLORS[entry.name] }}
            />
            <span className="chart-legend-name">{entry.name}</span>
            <span className="chart-legend-value">{entry.value}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

export function ScanActivityChart({ data }) {
  const CHART_THEME = chartTheme();
  const chartData = useMemo(() => {
    if (!data?.length) return [];
    return data.map((d) => ({
      date: d.date.slice(5),
      scans: d.scans,
    }));
  }, [data]);

  if (!chartData.length) {
    return (
      <div className="chart-empty">
        <span className="chart-empty-text">No scan activity</span>
      </div>
    );
  }

  return (
    <ResponsiveContainer width="100%" height={200}>
      <BarChart data={chartData} margin={{ top: 8, right: 8, bottom: 0, left: -20 }}>
        <CartesianGrid strokeDasharray="3 3" stroke={CHART_THEME.grid} vertical={false} />
        <XAxis
          dataKey="date"
          tick={{ fill: CHART_THEME.tick, fontSize: 10, fontFamily: 'var(--font-mono)' }}
          axisLine={{ stroke: CHART_THEME.axisLine }}
          tickLine={false}
          interval="preserveStartEnd"
        />
        <YAxis
          tick={{ fill: CHART_THEME.tick, fontSize: 10, fontFamily: 'var(--font-mono)' }}
          axisLine={false}
          tickLine={false}
          allowDecimals={false}
        />
        <Tooltip content={<CustomTooltip />} />
        <Bar
          dataKey="scans"
          name="Scans"
          fill={token('--chart-1', '#A9D41C')}
          radius={[3, 3, 0, 0]}
          animationDuration={800}
        />
      </BarChart>
    </ResponsiveContainer>
  );
}

export function RiskTrendChart({ data }) {
  const CHART_THEME = chartTheme();
  const RISK_COLOR = token('--chart-4', '#E8590C');
  const chartData = useMemo(() => {
    if (!data?.length) return [];
    return data.map((d) => ({
      date: d.date.slice(5),
      score: d.score,
    }));
  }, [data]);

  if (!chartData.length) {
    return (
      <div className="chart-empty">
        <span className="chart-empty-text">No risk trend data</span>
      </div>
    );
  }

  return (
    <ResponsiveContainer width="100%" height={200}>
      <LineChart data={chartData} margin={{ top: 8, right: 8, bottom: 0, left: -20 }}>
        <CartesianGrid strokeDasharray="3 3" stroke={CHART_THEME.grid} vertical={false} />
        <XAxis
          dataKey="date"
          tick={{ fill: CHART_THEME.tick, fontSize: 10, fontFamily: 'var(--font-mono)' }}
          axisLine={{ stroke: CHART_THEME.axisLine }}
          tickLine={false}
          interval="preserveStartEnd"
        />
        <YAxis
          domain={[0, 100]}
          tick={{ fill: CHART_THEME.tick, fontSize: 10, fontFamily: 'var(--font-mono)' }}
          axisLine={false}
          tickLine={false}
        />
        <Tooltip content={<CustomTooltip />} />
        <Line
          type="monotone"
          dataKey="score"
          name="Risk Score"
          stroke={RISK_COLOR}
          strokeWidth={2}
          dot={{ fill: RISK_COLOR, r: 3, strokeWidth: 0 }}
          activeDot={{ r: 5, stroke: RISK_COLOR, strokeWidth: 2, fill: token('--bg-elevated', '#EAE8FF') }}
          animationDuration={1000}
        />
      </LineChart>
    </ResponsiveContainer>
  );
}

export function OwaspBarChart({ data }) {
  const CHART_THEME = chartTheme();
  const BAR_COLOR = token('--chart-2', '#33264A');
  const chartData = useMemo(() => {
    if (!data?.length) return [];
    return data.slice(0, 6).map((d) => ({
      name: d.category.length > 12 ? d.category.slice(0, 12) + '…' : d.category,
      fullName: d.category,
      count: d.count,
    }));
  }, [data]);

  if (!chartData.length) {
    return (
      <div className="chart-empty">
        <span className="chart-empty-text">No OWASP data</span>
      </div>
    );
  }

  return (
    <ResponsiveContainer width="100%" height={200}>
      <BarChart data={chartData} layout="vertical" margin={{ top: 8, right: 8, bottom: 0, left: 8 }}>
        <CartesianGrid strokeDasharray="3 3" stroke={CHART_THEME.grid} horizontal={false} />
        <XAxis
          type="number"
          tick={{ fill: CHART_THEME.tick, fontSize: 10, fontFamily: 'var(--font-mono)' }}
          axisLine={{ stroke: CHART_THEME.axisLine }}
          tickLine={false}
          allowDecimals={false}
        />
        <YAxis
          dataKey="name"
          type="category"
          tick={{ fill: CHART_THEME.tick, fontSize: 10, fontFamily: 'var(--font-mono)' }}
          axisLine={false}
          tickLine={false}
          width={100}
        />
        <Tooltip
          content={({ active, payload }) => {
            if (!active || !payload?.length) return null;
            const item = payload[0].payload;
            return (
              <div className="chart-tooltip">
                <div className="chart-tooltip-label">{item.fullName}</div>
                <div className="chart-tooltip-item">
                  <span className="chart-tooltip-dot" style={{ background: BAR_COLOR }} />
                  <span className="chart-tooltip-name">Findings:</span>
                  <span className="chart-tooltip-value">{item.count}</span>
                </div>
              </div>
            );
          }}
        />
        <Bar
          dataKey="count"
          fill={BAR_COLOR}
          radius={[0, 3, 3, 0]}
          animationDuration={800}
        />
      </BarChart>
    </ResponsiveContainer>
  );
}
