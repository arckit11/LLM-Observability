'use client';

import { useEffect, useState } from 'react';
import TraceViewer from '@/components/TraceViewer';
import { fetchTraces } from '@/lib/api';

export default function TracesPage() {
  const [groupedTraces, setGroupedTraces] = useState({});
  const [loading, setLoading] = useState(true);
  const [sessionIdFilter, setSessionIdFilter] = useState('');
  const [modelFilter, setModelFilter] = useState('');
  const [total, setTotal] = useState(0);
  const [offset, setOffset] = useState(0);
  const LIMIT = 100;

  async function loadData(newOffset = 0) {
    setLoading(true);
    try {
      const params = { limit: LIMIT, offset: newOffset };
      if (sessionIdFilter) params.session_id = sessionIdFilter;
      if (modelFilter) params.model = modelFilter;

      const result = await fetchTraces(params);
      const rawSpans = result.data || [];
      setTotal(result.total || 0);
      setOffset(newOffset);

      // Group spans by trace_id
      const grouped = {};
      rawSpans.forEach((span) => {
        const tid = span.trace_id || 'unknown';
        if (!grouped[tid]) {
          grouped[tid] = [];
        }
        grouped[tid].push(span);
      });

      setGroupedTraces(grouped);
    } catch (err) {
      console.error('Failed to load traces:', err);
      setGroupedTraces({});
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadData(0);
  }, [sessionIdFilter, modelFilter]);

  const traceEntries = Object.entries(groupedTraces);

  return (
    <div className="page-container">
      <header className="page-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h1>Trace Explorer</h1>
          <p>Replay, inspect and debug full agent execution flows step-by-step</p>
        </div>
        {total > 0 && (
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '6px 14px', background: 'rgba(6, 182, 212, 0.1)', border: '1px solid rgba(6, 182, 212, 0.3)', borderRadius: 'var(--radius-full)', color: 'var(--cyan)', fontSize: '12px' }}>
            <span style={{ width: '6px', height: '6px', borderRadius: '50%', backgroundColor: 'var(--cyan)', display: 'inline-block', animation: 'pulse-glow 2s ease-in-out infinite' }}></span>
            {total.toLocaleString()} spans captured
          </div>
        )}
      </header>

      {/* Filters Section */}
      <section style={{ display: 'flex', gap: '16px', marginBottom: '24px', alignItems: 'center' }}>
        <div style={{ flex: 1, position: 'relative' }}>
          <input
            type="text"
            placeholder="Search by Session ID (e.g. user-42)"
            value={sessionIdFilter}
            onChange={(e) => setSessionIdFilter(e.target.value)}
            className="search-input"
            style={{ width: '100%' }}
          />
          <span style={{ position: 'absolute', left: '16px', top: '50%', transform: 'translateY(-50%)', opacity: 0.5 }}>🔍</span>
        </div>

        <select
          value={modelFilter}
          onChange={(e) => setModelFilter(e.target.value)}
          className="search-input"
          style={{ width: '220px', paddingLeft: '16px', appearance: 'none', background: 'var(--bg-primary) url("data:image/svg+xml;charset=utf-8,%3Csvg xmlns=\'http://www.w3.org/2000/svg\' viewBox=\'0 0 24 24\' fill=\'none\' stroke=\'%2364748b\' stroke-width=\'2\' stroke-linecap=\'round\' stroke-linejoin=\'round\'%3E%3Cpolyline points=\'6 9 12 15 18 9\'/%3E%3C/svg%3E") no-repeat right 16px center', backgroundSize: '16px' }}
        >
          <option value="">All Models</option>
          <option value="gpt-4o">GPT-4o</option>
          <option value="gpt-4o-mini">GPT-4o Mini</option>
          <option value="claude-3-5-sonnet">Claude 3.5 Sonnet</option>
          <option value="claude-3-haiku">Claude Haiku</option>
          <option value="gemini-1.5-flash">Gemini 1.5 Flash</option>
          <option value="gemini-1.5-pro">Gemini 1.5 Pro</option>
        </select>

        <button onClick={() => loadData(0)} className="btn btn-primary" style={{ padding: '8px 20px', height: '40px' }}>
          Refresh
        </button>
      </section>

      {/* Spans/Traces View */}
      {loading ? (
        <div style={{ display: 'flex', justifyContent: 'center', padding: '100px' }}>
          <div style={{ width: '30px', height: '30px', border: '3px solid rgba(255,255,255,0.1)', borderTopColor: 'var(--cyan)', borderRadius: '50%', animation: 'spin 1s linear infinite' }} />
        </div>
      ) : (
        <div>
          {traceEntries.map(([traceId, spans]) => (
            <TraceViewer key={traceId} traceId={traceId} spans={spans} />
          ))}
          {traceEntries.length === 0 && (
            <div className="glass-card" style={{ padding: '60px', textAlign: 'center', color: 'var(--text-tertiary)', border: '1px dashed var(--glass-border)' }}>
              <div style={{ fontSize: '48px', marginBottom: '16px', opacity: 0.4 }}>📡</div>
              <h3 style={{ marginBottom: '8px', color: 'var(--text-secondary)' }}>No traces captured yet</h3>
              <p style={{ fontSize: '13px', maxWidth: '400px', margin: '0 auto', lineHeight: '1.6' }}>
                Run your SDK-instrumented code to see traces appear here in real time.
                <br />
                <code style={{ fontSize: '12px', color: 'var(--cyan)', marginTop: '8px', display: 'inline-block' }}>
                  @observe(name=&quot;my-agent&quot;)
                </code>
              </p>
            </div>
          )}

          {/* Pagination */}
          {total > LIMIT && (
            <div style={{ display: 'flex', justifyContent: 'center', gap: '12px', marginTop: '24px' }}>
              <button
                onClick={() => loadData(Math.max(0, offset - LIMIT))}
                disabled={offset === 0}
                className="btn btn-secondary btn-sm"
              >
                ← Previous
              </button>
              <span style={{ fontSize: '13px', color: 'var(--text-tertiary)', alignSelf: 'center' }}>
                {offset + 1}–{Math.min(offset + LIMIT, total)} of {total}
              </span>
              <button
                onClick={() => loadData(offset + LIMIT)}
                disabled={offset + LIMIT >= total}
                className="btn btn-secondary btn-sm"
              >
                Next →
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
