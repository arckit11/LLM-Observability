'use client';

import { useEffect, useState } from 'react';
import MetricCard from '@/components/MetricCard';
import { CostBarChart, TimeseriesLineChart } from '@/components/Charts';
import { fetchCostSummary, fetchCostTimeseries } from '@/lib/api';

export default function CostPage() {
  const [summary, setSummary] = useState([]);
  const [timeseries, setTimeseries] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadData() {
      try {
        const [sumRes, timeRes] = await Promise.all([
          fetchCostSummary(),
          fetchCostTimeseries()
        ]);
        setSummary(sumRes);
        setTimeseries(timeRes);
      } catch (err) {
        console.error('Failed to load cost data:', err);
        setSummary([]);
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

  const totalCost = summary.reduce((acc, curr) => acc + (curr.total_cost || 0), 0);
  const totalCalls = summary.reduce((acc, curr) => acc + (curr.call_count || 0), 0);
  const avgCostPerCall = totalCalls > 0 ? (totalCost / totalCalls) : 0;
  const totalTokens = summary.reduce((acc, curr) => acc + (curr.total_tokens || 0), 0);

  return (
    <div className="page-container">
      <header className="page-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h1>Cost Analytics</h1>
          <p>Track pricing, usage and token counts across models and agents</p>
        </div>
        {totalCalls > 0 && (
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '6px 14px', background: 'rgba(16, 185, 129, 0.1)', border: '1px solid rgba(16, 185, 129, 0.3)', borderRadius: 'var(--radius-full)', color: 'var(--emerald)', fontSize: '12px' }}>
            <span style={{ width: '6px', height: '6px', borderRadius: '50%', backgroundColor: 'var(--emerald)', display: 'inline-block', animation: 'pulse-glow 2s ease-in-out infinite' }}></span>
            Live — {totalTokens.toLocaleString()} tokens tracked
          </div>
        )}
      </header>

      {/* KPI stats */}
      <section className="grid-3" style={{ marginBottom: '30px' }}>
        <MetricCard
          title="Total Spend"
          value={`$${totalCost.toFixed(4)}`}
          icon="💸"
          accentColor="emerald"
        />
        <MetricCard
          title="Total LLM Calls"
          value={totalCalls}
          icon="📞"
          accentColor="cyan"
        />
        <MetricCard
          title="Avg Cost per Call"
          value={`$${avgCostPerCall.toFixed(5)}`}
          icon="⚖️"
          accentColor="violet"
        />
      </section>

      {/* Charts */}
      <section className="grid-2" style={{ marginBottom: '30px' }}>
        <div className="chart-container">
          <h3 className="chart-container-title">Spend by Model (USD)</h3>
          {summary.length > 0 ? (
            <CostBarChart data={summary} />
          ) : (
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '250px', color: 'var(--text-tertiary)', fontSize: '13px' }}>
              No cost data yet — run observed LLM calls to populate
            </div>
          )}
        </div>
        <div className="chart-container">
          <h3 className="chart-container-title">Hourly Spend Trend</h3>
          {timeseries.length > 0 ? (
            <TimeseriesLineChart
              data={timeseries}
              dataKey="cost_usd"
              color="#10b981"
              name="Spend (USD)"
            />
          ) : (
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '250px', color: 'var(--text-tertiary)', fontSize: '13px' }}>
              No hourly data yet
            </div>
          )}
        </div>
      </section>

      {/* Breakdown Table */}
      <section className="data-table-wrapper">
        <div className="data-table-header">
          <span className="data-table-title">Model-by-Model Cost Breakdown</span>
        </div>
        <table className="data-table">
          <thead>
            <tr>
              <th>Model Name</th>
              <th>Total Cost</th>
              <th>LLM Calls</th>
              <th>Est. Tokens</th>
              <th>Avg Cost/Call</th>
            </tr>
          </thead>
          <tbody>
            {summary.map((item, index) => (
              <tr key={index}>
                <td style={{ fontWeight: '600', color: 'var(--text-primary)' }}>{item.model}</td>
                <td style={{ color: 'var(--emerald)', fontWeight: '500' }}>${Number(item.total_cost || 0).toFixed(5)}</td>
                <td>{item.call_count}</td>
                <td>{item.total_tokens?.toLocaleString() || 'N/A'}</td>
                <td style={{ color: 'var(--text-secondary)' }}>${Number(item.avg_cost_per_call || 0).toFixed(5)}</td>
              </tr>
            ))}
            {summary.length === 0 && (
              <tr>
                <td colSpan="5" style={{ textAlign: 'center', padding: '40px', color: 'var(--text-tertiary)' }}>
                  No cost data recorded yet. Run your instrumented code to start tracking.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </section>
    </div>
  );
}
