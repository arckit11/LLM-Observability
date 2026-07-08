'use client';

import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  LineChart,
  Line,
  AreaChart,
  Area,
  PieChart,
  Pie,
  Cell,
  Legend,
} from 'recharts';

const ACCENT_COLORS = ['#06b6d4', '#8b5cf6', '#10b981', '#f59e0b', '#f43f5e', '#ec4899', '#3b82f6'];

// Custom Tooltip component matching glass design
const CustomTooltip = ({ active, payload, label, formatter }) => {
  if (active && payload && payload.length) {
    return (
      <div className="chart-tooltip">
        <p className="chart-tooltip-label">{label}</p>
        {payload.map((item, index) => (
          <div key={index} className="chart-tooltip-item">
            <div>
              <span 
                className="chart-tooltip-dot" 
                style={{ backgroundColor: item.color || item.payload.fill || '#06b6d4' }} 
              />
              <span style={{ color: 'var(--text-secondary)' }}>{item.name}:</span>
            </div>
            <span className="chart-tooltip-value">
              {formatter ? formatter(item.value) : item.value}
            </span>
          </div>
        ))}
      </div>
    );
  }
  return null;
};

export function CostBarChart({ data }) {
  const chartData = data.map((d) => ({
    name: d.model || 'unknown',
    cost: d.total_cost || 0.0,
    calls: d.call_count || 0,
  }));

  const formatCost = (val) => `$${Number(val).toFixed(4)}`;

  return (
    <ResponsiveContainer width="100%" height={300}>
      <BarChart data={chartData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" vertical={false} />
        <XAxis 
          dataKey="name" 
          stroke="var(--text-tertiary)" 
          fontSize={11} 
          tickLine={false} 
        />
        <YAxis 
          stroke="var(--text-tertiary)" 
          fontSize={11} 
          tickLine={false} 
          axisLine={false}
          tickFormatter={(val) => `$${Number(val).toFixed(2)}`}
        />
        <Tooltip content={<CustomTooltip formatter={formatCost} />} cursor={{ fill: 'rgba(255,255,255,0.02)' }} />
        <Bar dataKey="cost" name="Cost" fill="url(#cyan-gradient)" radius={[4, 4, 0, 0]}>
          <defs>
            <linearGradient id="cyan-gradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#06b6d4" stopOpacity={0.8} />
              <stop offset="100%" stopColor="#06b6d4" stopOpacity={0.2} />
            </linearGradient>
          </defs>
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}

export function TimeseriesLineChart({ data, dataKey = 'cost_usd', color = '#8b5cf6', name = 'Cost' }) {
  const formatVal = (val) => {
    if (dataKey.includes('cost')) return `$${Number(val).toFixed(4)}`;
    if (dataKey.includes('latency')) return `${Number(val).toFixed(0)} ms`;
    return val;
  };

  const chartData = data.map((d) => ({
    time: d.hour ? new Date(d.hour).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : 
          d.timestamp ? new Date(d.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : 
          'N/A',
    value: d[dataKey] || 0.0,
  }));

  const gradientId = `gradient-${dataKey}`;

  return (
    <ResponsiveContainer width="100%" height={300}>
      <AreaChart data={chartData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
        <defs>
          <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor={color} stopOpacity={0.4} />
            <stop offset="95%" stopColor={color} stopOpacity={0.0} />
          </linearGradient>
        </defs>
        <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" vertical={false} />
        <XAxis 
          dataKey="time" 
          stroke="var(--text-tertiary)" 
          fontSize={11} 
          tickLine={false} 
        />
        <YAxis 
          stroke="var(--text-tertiary)" 
          fontSize={11} 
          tickLine={false} 
          axisLine={false}
          tickFormatter={(val) => dataKey.includes('cost') ? `$${Number(val).toFixed(2)}` : val}
        />
        <Tooltip content={<CustomTooltip formatter={formatVal} />} />
        <Area 
          type="monotone" 
          dataKey="value" 
          name={name} 
          stroke={color} 
          strokeWidth={2}
          fillOpacity={1} 
          fill={`url(#${gradientId})`} 
        />
      </AreaChart>
    </ResponsiveContainer>
  );
}

export function ModelPieChart({ data }) {
  const chartData = data.map((d) => ({
    name: d.model || 'unknown',
    value: d.call_count || 0,
  }));

  return (
    <ResponsiveContainer width="100%" height={260}>
      <PieChart>
        <Pie
          data={chartData}
          cx="50%"
          cy="45%"
          innerRadius={60}
          outerRadius={80}
          paddingAngle={4}
          dataKey="value"
        >
          {chartData.map((entry, index) => (
            <Cell key={`cell-${index}`} fill={ACCENT_COLORS[index % ACCENT_COLORS.length]} />
          ))}
        </Pie>
        <Tooltip content={<CustomTooltip formatter={(val) => `${val} calls`} />} />
        <Legend 
          verticalAlign="bottom" 
          align="center"
          iconType="circle"
          iconSize={8}
          wrapperStyle={{ fontSize: '11px', paddingTop: '10px', color: 'var(--text-secondary)' }}
        />
      </PieChart>
    </ResponsiveContainer>
  );
}

export function LatencyBarChart({ data }) {
  const chartData = data.map((d) => ({
    name: d.model || 'unknown',
    p50: Math.round(d.p50 || 0),
    p95: Math.round(d.p95 || 0),
    p99: Math.round(d.p99 || 0),
  }));

  return (
    <ResponsiveContainer width="100%" height={300}>
      <BarChart data={chartData} margin={{ top: 10, right: 10, left: -10, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" vertical={false} />
        <XAxis 
          dataKey="name" 
          stroke="var(--text-tertiary)" 
          fontSize={11} 
          tickLine={false} 
        />
        <YAxis 
          stroke="var(--text-tertiary)" 
          fontSize={11} 
          tickLine={false} 
          axisLine={false}
          tickFormatter={(val) => `${val}ms`}
        />
        <Tooltip content={<CustomTooltip formatter={(val) => `${val} ms`} />} cursor={{ fill: 'rgba(255,255,255,0.02)' }} />
        <Legend verticalAlign="top" height={36} iconType="circle" iconSize={8} wrapperStyle={{ fontSize: '11px' }} />
        <Bar dataKey="p50" name="P50" fill="#06b6d4" radius={[3, 3, 0, 0]} />
        <Bar dataKey="p95" name="P95" fill="#8b5cf6" radius={[3, 3, 0, 0]} />
        <Bar dataKey="p99" name="P99" fill="#f43f5e" radius={[3, 3, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  );
}
