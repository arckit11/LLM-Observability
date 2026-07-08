export default function AlertBadge({ type }) {
  let badgeClass = 'badge-info';
  let label = type;

  if (type === 'high_cost_session') {
    badgeClass = 'badge-warning';
    label = 'High Cost';
  } else if (type === 'error_spike') {
    badgeClass = 'badge-error';
    label = 'Error Spike';
  } else if (type === 'high_latency') {
    badgeClass = 'badge-violet';
    label = 'High Latency';
  }

  return (
    <span className={`badge ${badgeClass}`}>
      {label}
    </span>
  );
}
