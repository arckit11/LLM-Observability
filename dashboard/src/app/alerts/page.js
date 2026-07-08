'use client';

import { useEffect, useState } from 'react';
import MetricCard from '@/components/MetricCard';
import AlertBadge from '@/components/AlertBadge';
import { fetchAlerts, resolveAlert } from '@/lib/api';

export default function AlertsPage() {
  const [alerts, setAlerts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showResolved, setShowResolved] = useState(false);

  async function loadData() {
    setLoading(true);
    try {
      const data = await fetchAlerts({ resolved: showResolved });
      setAlerts(data);
    } catch (err) {
      console.error('Failed to load alerts:', err);
      setAlerts([]);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadData();
  }, [showResolved]);

  const handleResolve = async (id) => {
    try {
      await resolveAlert(id);
      // Optimistic update
      setAlerts((prev) => prev.filter((a) => a.id !== id));
    } catch (err) {
      console.error('Failed to resolve alert', err);
    }
  };

  if (loading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', padding: '100px' }}>
        <div style={{ width: '30px', height: '30px', border: '3px solid rgba(255,255,255,0.1)', borderTopColor: 'var(--cyan)', borderRadius: '50%', animation: 'spin 1s linear infinite' }} />
      </div>
    );
  }

  const activeCount = alerts.filter(a => !a.resolved).length;

  return (
    <div className="page-container">
      <header className="page-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h1>Alert Manager</h1>
          <p>Monitor cost thresholds, response latency violations and provider outages</p>
        </div>
      </header>

      {/* Overview stats cards */}
      <section className="grid-2" style={{ marginBottom: '30px' }}>
        <MetricCard
          title="Active System Alerts"
          value={activeCount}
          icon="🚨"
          accentColor={activeCount > 0 ? 'rose' : 'emerald'}
        />
        <div className="glass-card" style={{ padding: '24px', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <div>
            <h4 style={{ fontWeight: '600', marginBottom: '4px' }}>Alert Filter Settings</h4>
            <p style={{ fontSize: '12px', color: 'var(--text-tertiary)' }}>Show unresolved warnings or historical resolved logs</p>
          </div>
          <div style={{ display: 'flex', background: 'var(--bg-primary)', borderRadius: 'var(--radius-md)', padding: '4px', border: '1px solid var(--glass-border)' }}>
            <button
              onClick={() => setShowResolved(false)}
              style={{ padding: '6px 16px', fontSize: '12px', borderRadius: 'var(--radius-sm)', background: !showResolved ? 'var(--bg-elevated)' : 'transparent', color: !showResolved ? 'var(--cyan)' : 'var(--text-secondary)' }}
            >
              Active
            </button>
            <button
              onClick={() => setShowResolved(true)}
              style={{ padding: '6px 16px', fontSize: '12px', borderRadius: 'var(--radius-sm)', background: showResolved ? 'var(--bg-elevated)' : 'transparent', color: showResolved ? 'var(--cyan)' : 'var(--text-secondary)' }}
            >
              Resolved
            </button>
          </div>
        </div>
      </section>

      {/* How alerts work info */}
      <section className="glass-card" style={{ padding: '20px 24px', marginBottom: '24px', borderLeft: '3px solid var(--cyan)' }}>
        <h4 style={{ marginBottom: '8px', color: 'var(--text-primary)', fontSize: '14px' }}>🔔 How Alerts Work</h4>
        <p style={{ fontSize: '12px', color: 'var(--text-secondary)', lineHeight: '1.7', margin: 0 }}>
          Alerts fire <strong>automatically</strong> when your SDK-instrumented calls trigger threshold violations.
          Three built-in rules are active:
          <br />
          <span style={{ color: 'var(--amber)' }}>• High Cost Session</span> — fires when a session&apos;s cumulative cost exceeds <code>$0.50</code>
          <br />
          <span style={{ color: 'var(--rose)' }}>• Error Spike</span> — fires when error rate exceeds <code>10%</code> in the last 5 minutes
          <br />
          <span style={{ color: 'var(--violet)' }}>• High Latency</span> — fires when a single LLM call exceeds <code>5000ms</code>
        </p>
      </section>

      {/* Alerts Table */}
      <section className="data-table-wrapper">
        <div className="data-table-header">
          <span className="data-table-title">{showResolved ? 'Resolved Logs' : 'Active Incidents'}</span>
          <button onClick={loadData} className="btn btn-secondary btn-sm">
            Refresh
          </button>
        </div>
        <table className="data-table">
          <thead>
            <tr>
              <th>Fired Time</th>
              <th>Incident Type</th>
              <th>Details / Message</th>
              <th>Target Model / Session</th>
              <th>Current Value</th>
              {!showResolved && <th>Action</th>}
            </tr>
          </thead>
          <tbody>
            {alerts.map((alert) => (
              <tr key={alert.id}>
                <td style={{ color: 'var(--text-tertiary)' }}>
                  {new Date(alert.fired_at).toLocaleString()}
                </td>
                <td>
                  <AlertBadge type={alert.alert_type} />
                </td>
                <td style={{ fontWeight: '500', color: 'var(--text-primary)' }}>
                  {alert.message || 'Alert triggered'}
                </td>
                <td>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
                    {alert.model && <span style={{ fontSize: '12px' }}>Model: <code>{alert.model}</code></span>}
                    {alert.session_id && <span style={{ fontSize: '12px' }}>Session: <code>{alert.session_id}</code></span>}
                    {!alert.model && !alert.session_id && <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>System-wide</span>}
                  </div>
                </td>
                <td style={{ fontWeight: '600' }}>
                  {alert.alert_type.includes('cost') ? `$${Number(alert.current_value).toFixed(4)}` :
                   alert.alert_type.includes('latency') ? `${Math.round(alert.current_value)} ms` :
                   `${(Number(alert.current_value) * 100).toFixed(1)}%`}
                </td>
                {!showResolved && (
                  <td>
                    <button
                      onClick={() => handleResolve(alert.id)}
                      className="btn btn-secondary btn-sm"
                      style={{ borderColor: 'var(--emerald-glow)', color: 'var(--emerald)' }}
                    >
                      Acknowledge & Resolve
                    </button>
                  </td>
                )}
              </tr>
            ))}
            {alerts.length === 0 && (
              <tr>
                <td colSpan={showResolved ? 5 : 6} style={{ textAlign: 'center', padding: '40px', color: 'var(--text-tertiary)' }}>
                  {showResolved ? 'No resolved alerts found.' : '✨ No active system alerts! All parameters nominal.'}
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </section>
    </div>
  );
}
