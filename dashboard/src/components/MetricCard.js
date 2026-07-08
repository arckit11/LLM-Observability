export default function MetricCard({ title, value, icon, trend, trendLabel, accentColor }) {
  const accentClass = accentColor ? `accent-${accentColor}` : '';
  const iconColorClass = accentColor || 'cyan';

  return (
    <div className={`metric-card ${accentClass}`}>
      <div className="metric-card-header">
        <span className="metric-card-label">{title}</span>
        <div className={`metric-card-icon ${iconColorClass}`}>
          {icon}
        </div>
      </div>
      <div className="metric-card-value">{value}</div>
      {trend !== undefined && (
        <div className={`metric-card-trend ${trend >= 0 ? 'up' : 'down'}`}>
          <span>{trend >= 0 ? '▲' : '▼'}</span>
          <span>{Math.abs(trend)}%</span>
          <span style={{ color: 'var(--text-tertiary)', marginLeft: '4px', fontWeight: 'normal' }}>
            {trendLabel || 'vs yesterday'}
          </span>
        </div>
      )}
    </div>
  );
}
