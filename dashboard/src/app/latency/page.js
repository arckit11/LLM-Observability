'use client';

import { useEffect, useState } from 'react';
import MetricCard from '@/components/MetricCard';
import { LatencyBarChart, TimeseriesLineChart } from '@/components/Charts';
import { fetchLatencyPercentiles, fetchLatencyTimeseries } from '@/lib/api';

export default function LatencyPage() {
  const [percentiles, setPercentiles] = useState([]);
  const [timeseries, setTimeseries] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadData() {
      try {
        const [pctRes, timeRes] = await Promise.all([
          fetchLatencyPercentiles(),
          fetchLatencyTimeseries()
        ]);
        setPercentiles(pctRes);
        setTimeseries(timeRes);
      } catch (err) {
        console.error('Failed to load latency data:', err);
        setPercentiles([]);
        setTimeseries([]);
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, []);

  if (loading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', padding: '100px' }}>
        <div style={{ width: '30px', height: '30px', border: '3px solid rgba(255,255,255,0.1)', borderTopColor: 'var(--cyan)', borderRadius: '50%', animation: 'spin 1s linear infinite' }} />
      </div>
    );
  }

  // Calculate generic aggregate percentiles for overview cards
  const overallP50 = percentiles.length > 0 ? Math.round(percentiles.reduce((acc, c) => acc + c.p50, 0) / percentiles.length) : 0;
  const overallP95 = percentiles.length > 0 ? Math.round(percentiles.reduce((acc, c) => acc + c.p95, 0) / percentiles.length) : 0;
  const overallP99 = percentiles.length > 0 ? Math.round(percentiles.reduce((acc, c) => acc + c.p99, 0) / percentiles.length) : 0;

  return (
    <div className="page-container">
      <header className="page-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h1>Latency Metrics</h1>
          <p>Analyse speed, response time percentiles and latency trends</p>
        </div>
        {percentiles.length > 0 && (
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '6px 14px', background: 'rgba(139, 92, 246, 0.1)', border: '1px solid rgba(139, 92, 246, 0.3)', borderRadius: 'var(--radius-full)', color: 'var(--violet)', fontSize: '12px' }}>
            <span style={{ width: '6px', height: '6px', borderRadius: '50%', backgroundColor: 'var(--violet)', display: 'inline-block', animation: 'pulse-glow 2s ease-in-out infinite' }}></span>
            Live — {percentiles.length} model{percentiles.length !== 1 ? 's' : ''} tracked
          </div>
        )}
      </header>

      {/* Metric Cards Grid */}
      <section className="grid-3" style={{ marginBottom: '30px' }}>
        <MetricCard
          title="Overall P50 (Median)"
          value={`${overallP50} ms`}
          icon="⚡"
          accentColor="cyan"
        />
        <MetricCard
          title="Overall P95 (Slowest 5%)"
          value={`${overallP95} ms`}
          icon="🐢"
          accentColor="violet"
        />
        <MetricCard
          title="Overall P99 (Outliers)"
          value={`${overallP99} ms`}
          icon="🚨"
          accentColor="rose"
        />
      </section>

      {/* Latency Charts */}
      <section className="grid-2" style={{ marginBottom: '30px' }}>
        <div className="chart-container">
          <h3 className="chart-container-title">Percentiles by Model</h3>
          {percentiles.length > 0 ? (
            <LatencyBarChart data={percentiles} />
          ) : (
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '250px', color: 'var(--text-tertiary)', fontSize: '13px' }}>
              No latency data yet
            </div>
          )}
        </div>
        <div className="chart-container">
          <h3 className="chart-container-title">Latency Trend Over Time</h3>
          {timeseries.length > 0 ? (
            <TimeseriesLineChart
              data={timeseries}
              dataKey="latency_ms"
              color="#8b5cf6"
              name="Latency (ms)"
            />
          ) : (
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '250px', color: 'var(--text-tertiary)', fontSize: '13px' }}>
              No hourly data yet
            </div>
          )}
        </div>
      </section>

      {/* Percentiles Table */}
      <section className="data-table-wrapper">
        <div className="data-table-header">
          <span className="data-table-title">Detailed Percentile Breakdown by Model</span>
        </div>
        <table className="data-table">
          <thead>
            <tr>
              <th>Model Name</th>
              <th>P50 (Median)</th>
              <th>P95 (95th Percentile)</th>
              <th>P99 (99th Percentile)</th>
            </tr>
          </thead>
          <tbody>
            {percentiles.map((item, index) => (
              <tr key={index}>
                <td style={{ fontWeight: '600', color: 'var(--text-primary)' }}>{item.model}</td>
                <td>{Math.round(item.p50)} ms</td>
                <td style={{ color: 'var(--amber)', fontWeight: '500' }}>{Math.round(item.p95)} ms</td>
                <td style={{ color: 'var(--rose)', fontWeight: '500' }}>{Math.round(item.p99)} ms</td>
              </tr>
            ))}
            {percentiles.length === 0 && (
              <tr>
                <td colSpan="4" style={{ textAlign: 'center', padding: '40px', color: 'var(--text-tertiary)' }}>
                  No latency data recorded yet. Run your instrumented code to start tracking.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </section>
    </div>
  );
}
