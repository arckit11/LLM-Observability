'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import MetricCard from '@/components/MetricCard';
import { ModelPieChart, TimeseriesLineChart } from '@/components/Charts';
import { fetchOverview } from '@/lib/api';

export default function OverviewPage() {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);

  async function loadData() {
    try {
      const data = await fetchOverview();
      setStats(data);
    } catch (err) {
      console.error('Failed to load overview:', err);
      setStats({
        total_spans: 0,
        total_cost: 0,
        active_sessions: 0,
        error_rate: 0,
        avg_latency: 0,
        spans_today: 0,
        top_models: [],
        recent_traces: [],
        cost_trend: [],
      });
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadData();
    // Auto-refresh every 10 seconds
    const interval = setInterval(loadData, 10000);
    return () => clearInterval(interval);
  }, []);

  if (loading) {
    return (
      <div className="page-container" style={{ display: 'flex', flexDirection: 'column', gap: '30px', justifyContent: 'center', height: '80vh', alignItems: 'center' }}>
        <div style={{ width: '40px', height: '40px', border: '3px solid rgba(255,255,255,0.1)', borderTopColor: 'var(--cyan)', borderRadius: '50%', animation: 'spin 1s linear infinite' }} />
        <span style={{ color: 'var(--text-secondary)', fontSize: '14px' }}>Connecting to observatory...</span>
      </div>
    );
  }

  const errorRateVal = stats.error_rate !== undefined ? (Number(stats.error_rate) * 100).toFixed(1) : '0.0';

  return (
    <div className="page-container">
      <header className="page-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h1>Observatory Overview</h1>
          <p>Real-time metrics, costs and latency analysis across LLM services</p>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '6px 14px', background: 'rgba(6, 182, 212, 0.1)', border: '1px solid rgba(6, 182, 212, 0.3)', borderRadius: 'var(--radius-full)', color: 'var(--cyan)', fontSize: '12px' }}>
          <span style={{ width: '6px', height: '6px', borderRadius: '50%', backgroundColor: 'var(--cyan)', display: 'inline-block', animation: 'pulse-glow 2s ease-in-out infinite' }}></span>
          Live — auto-refreshing
        </div>
      </header>

      {/* Metric Cards Grid */}
      <section className="grid-4" style={{ marginBottom: '30px' }}>
        <MetricCard
          title="Total Spans"
          value={stats.total_spans || 0}
          icon="🔄"
          accentColor="cyan"
        />
        <MetricCard
          title="Total Cost"
          value={`$${Number(stats.total_cost || 0).toFixed(4)}`}
          icon="💰"
          accentColor="emerald"
        />
        <MetricCard
          title="Active Sessions"
          value={stats.active_sessions || 0}
          icon="👥"
          accentColor="violet"
        />
        <MetricCard
          title="Error Rate"
          value={`${errorRateVal}%`}
          icon="🔥"
          accentColor={Number(errorRateVal) > 5 ? 'rose' : 'amber'}
        />
      </section>

      {/* Chart Section */}
      <section className="grid-2" style={{ marginBottom: '30px' }}>
        <div className="chart-container">
          <h3 className="chart-container-title">Volume by Model</h3>
          {(stats.top_models || []).length > 0 ? (
            <ModelPieChart data={stats.top_models || []} />
          ) : (
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '250px', color: 'var(--text-tertiary)', fontSize: '13px' }}>
              No model data yet — run observed calls to populate
            </div>
          )}
        </div>
        <div className="chart-container">
          <h3 className="chart-container-title">Hourly Cost Trend</h3>
          {(stats.cost_trend || []).length > 0 ? (
            <TimeseriesLineChart
              data={stats.cost_trend || []}
              dataKey="cost_usd"
              color="#10b981"
              name="Cost (USD)"
            />
          ) : (
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '250px', color: 'var(--text-tertiary)', fontSize: '13px' }}>
              No hourly data yet
            </div>
          )}
        </div>
      </section>

      {/* Recent Traces Table */}
      <section className="data-table-wrapper">
        <div className="data-table-header">
          <span className="data-table-title">Recent Activity</span>
          <Link href="/traces" className="btn btn-secondary btn-sm">
            Explore All Traces
          </Link>
        </div>
        <table className="data-table">
          <thead>
            <tr>
              <th>Time</th>
              <th>Span ID / Name</th>
              <th>Model</th>
              <th>Latency</th>
              <th>Cost</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {(stats.recent_traces || []).map((trace, index) => (
              <tr key={index}>
                <td style={{ color: 'var(--text-tertiary)' }}>
                  {new Date(trace.created_at || trace.timestamp).toLocaleTimeString()}
                </td>
                <td>
                  <div style={{ display: 'flex', flexDirection: 'column' }}>
                    <span style={{ fontWeight: '600', color: 'var(--text-primary)' }}>{trace.name || 'observed-fn'}</span>
                    <span style={{ fontFamily: 'var(--font-mono)', fontSize: '11px', color: 'var(--text-tertiary)' }}>{trace.trace_id.substring(0, 8)}</span>
                  </div>
                </td>
                <td>{trace.model}</td>
                <td>{trace.latency_ms} ms</td>
                <td style={{ color: 'var(--emerald)', fontWeight: '500' }}>
                  ${Number(trace.cost_usd || 0).toFixed(5)}
                </td>
                <td>
                  <span className={`badge ${trace.error ? 'badge-error' : 'badge-success'}`}>
                    {trace.error ? 'Error' : 'Success'}
                  </span>
                </td>
              </tr>
            ))}
            {(!stats.recent_traces || stats.recent_traces.length === 0) && (
              <tr>
                <td colSpan="6" style={{ textAlign: 'center', padding: '40px', color: 'var(--text-tertiary)' }}>
                  <div style={{ marginBottom: '8px', fontSize: '20px', opacity: 0.4 }}>📡</div>
                  Waiting for traces... Run your <code>@observe</code> instrumented code to see activity here.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </section>
    </div>
  );
}
