import { useMemo } from 'react';
import {
  PieChart, Pie, Cell, ResponsiveContainer, Tooltip, Legend,
  BarChart, Bar, XAxis, YAxis, CartesianGrid,
  LineChart, Line,
} from 'recharts';
import './Charts.css';

const SEVERITY_COLORS = {
  Critical: '#ff2244',
  High: '#ff6622',
  Medium: '#ffaa00',
  Low: '#00ff88',
  Info: '#5a8a80',
};

const CHART_THEME = {
  bg: 'transparent',
  grid: 'rgba(0,255,170,0.04)',
  axisLine: 'rgba(0,255,170,0.08)',
  tick: '#6b7a70',
  tooltipBg: '#0d1210',
  tooltipBorder: 'rgba(0,255,170,0.15)',
  tooltipText: '#c8d4cc',
};

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
                fill={SEVERITY_COLORS[entry.name] || '#5a8a80'}
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
          fill="#00d4ff"
          radius={[3, 3, 0, 0]}
          animationDuration={800}
        />
      </BarChart>
    </ResponsiveContainer>
  );
}

export function RiskTrendChart({ data }) {
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
          stroke="#ff6622"
          strokeWidth={2}
          dot={{ fill: '#ff6622', r: 3, strokeWidth: 0 }}
          activeDot={{ r: 5, stroke: '#ff6622', strokeWidth: 2, fill: '#0d1210' }}
          animationDuration={1000}
        />
      </LineChart>
    </ResponsiveContainer>
  );
}

export function OwaspBarChart({ data }) {
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
                  <span className="chart-tooltip-dot" style={{ background: '#aa66ff' }} />
                  <span className="chart-tooltip-name">Findings:</span>
                  <span className="chart-tooltip-value">{item.count}</span>
                </div>
              </div>
            );
          }}
        />
        <Bar
          dataKey="count"
          fill="#aa66ff"
          radius={[0, 3, 3, 0]}
          animationDuration={800}
        />
      </BarChart>
    </ResponsiveContainer>
  );
}
