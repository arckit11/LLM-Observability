'use client';

import { useState } from 'react';

export default function TraceViewer({ traceId, spans = [] }) {
  const [isOpen, setIsOpen] = useState(false);
  const [activeTabs, setActiveTabs] = useState({}); // spanId -> 'prompt' | 'response'

  const totalCost = spans.reduce((acc, s) => acc + (s.cost_usd || 0), 0);
  const totalLatency = spans.reduce((acc, s) => acc + (s.latency_ms || 0), 0);
  const modelNames = Array.from(new Set(spans.map((s) => s.model))).filter(Boolean);
  const hasErrors = spans.some((s) => s.error);
  const baseTime = spans.length > 0 ? new Date(spans[0].created_at || spans[0].timestamp) : new Date();

  const toggleOpen = () => setIsOpen(!isOpen);

  const setTab = (spanId, tab) => {
    setActiveTabs((prev) => ({ ...prev, [spanId]: tab }));
  };

  return (
    <div className={`trace-group-card ${hasErrors ? 'has-error' : ''}`} style={{ marginBottom: '16px', border: '1px solid var(--glass-border)', borderRadius: 'var(--radius-lg)', background: 'var(--glass-bg)', overflow: 'hidden' }}>
      <div 
        onClick={toggleOpen}
        style={{ padding: '16px 20px', display: 'flex', alignItems: 'center', justifyContent: 'space-between', cursor: 'pointer', transition: 'background 150ms' }}
        className="trace-header-hover"
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
          <span style={{ fontSize: '18px', color: 'var(--text-tertiary)' }}>{isOpen ? '▼' : '▶'}</span>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span style={{ fontWeight: '600', fontFamily: 'var(--font-mono)', fontSize: '13px', color: 'var(--cyan)' }}>
                {traceId.substring(0, 8)}...
              </span>
              {spans[0]?.name && (
                <span style={{ fontSize: '12px', padding: '2px 8px', borderRadius: 'var(--radius-sm)', background: 'var(--bg-elevated)', color: 'var(--text-secondary)' }}>
                  {spans[0].name}
                </span>
              )}
            </div>
            <div style={{ fontSize: '11px', color: 'var(--text-tertiary)', marginTop: '4px' }}>
              {baseTime.toLocaleString()} · {spans.length} span{spans.length > 1 ? 's' : ''}
            </div>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '24px', fontSize: '13px' }}>
          <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
            {modelNames.map((m) => (
              <span key={m} style={{ fontSize: '11px', border: '1px solid var(--glass-border)', padding: '2px 6px', borderRadius: 'var(--radius-sm)', color: 'var(--text-secondary)' }}>
                {m}
              </span>
            ))}
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end' }}>
            <span style={{ fontWeight: '600', color: 'var(--text-primary)' }}>{totalLatency} ms</span>
            <span style={{ fontSize: '11px', color: 'var(--text-tertiary)' }}>latency</span>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end' }}>
            <span style={{ fontWeight: '600', color: 'var(--emerald)' }}>${totalCost.toFixed(5)}</span>
            <span style={{ fontSize: '11px', color: 'var(--text-tertiary)' }}>cost</span>
          </div>

          {hasErrors && (
            <span className="badge badge-error" style={{ fontSize: '10px' }}>Failed</span>
          )}
        </div>
      </div>

      {isOpen && (
        <div style={{ borderTop: '1px solid var(--glass-border)', background: 'rgba(0,0,0,0.15)', padding: '20px' }}>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            {spans.map((span, idx) => {
              const currentTab = activeTabs[span.span_id] || 'prompt';
              return (
                <div 
                  key={span.span_id || idx} 
                  style={{ border: '1px solid var(--glass-border)', borderRadius: 'var(--radius-md)', background: 'var(--bg-primary)', overflow: 'hidden' }}
                >
                  {/* Span Header */}
                  <div style={{ padding: '12px 16px', display: 'flex', alignItems: 'center', justifyContent: 'space-between', background: 'rgba(255,255,255,0.02)', borderBottom: '1px solid var(--glass-border)' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                      <span style={{ fontSize: '11px', fontFamily: 'var(--font-mono)', color: 'var(--text-tertiary)' }}>
                        #{idx + 1}
                      </span>
                      <span style={{ fontWeight: '600', fontSize: '13px', color: 'var(--text-primary)' }}>
                        {span.name || 'observed-fn'}
                      </span>
                      <span style={{ fontSize: '11px', color: 'var(--text-tertiary)' }}>
                        {span.model}
                      </span>
                    </div>

                    <div style={{ display: 'flex', alignItems: 'center', gap: '16px', fontSize: '12px', color: 'var(--text-secondary)' }}>
                      <span>🏎️ {span.latency_ms}ms</span>
                      <span>🎟️ {span.tokens_in || 0} → {span.tokens_out || 0}</span>
                      <span style={{ color: 'var(--emerald)' }}>💰 ${span.cost_usd?.toFixed(5) || '0.00'}</span>
                    </div>
                  </div>

                  {/* Span Body */}
                  <div style={{ padding: '16px' }}>
                    {span.error && (
                      <div style={{ marginBottom: '16px', padding: '12px', background: 'rgba(244, 63, 94, 0.1)', borderLeft: '3px solid var(--rose)', borderRadius: '4px', color: 'var(--rose)', fontSize: '13px' }}>
                        <strong>Error:</strong> {span.error}
                      </div>
                    )}

                    <div style={{ display: 'flex', borderBottom: '1px solid var(--glass-border)', marginBottom: '12px' }}>
                      <button 
                        onClick={() => setTab(span.span_id, 'prompt')}
                        style={{ padding: '8px 16px', fontSize: '12px', fontWeight: '500', color: currentTab === 'prompt' ? 'var(--cyan)' : 'var(--text-tertiary)', borderBottom: currentTab === 'prompt' ? '2px solid var(--cyan)' : 'none' }}
                      >
                        Prompt Messages
                      </button>
                      <button 
                        onClick={() => setTab(span.span_id, 'response')}
                        style={{ padding: '8px 16px', fontSize: '12px', fontWeight: '500', color: currentTab === 'response' ? 'var(--cyan)' : 'var(--text-tertiary)', borderBottom: currentTab === 'response' ? '2px solid var(--cyan)' : 'none' }}
                      >
                        Response Output
                      </button>
                    </div>

                    <div style={{ background: '#070a13', borderRadius: 'var(--radius-sm)', padding: '14px', border: '1px solid rgba(255,255,255,0.02)' }}>
                      <pre style={{ margin: 0, fontFamily: 'var(--font-mono)', fontSize: '12px', overflowX: 'auto', whiteSpace: 'pre-wrap', color: '#e2e8f0', lineHeight: '1.5' }}>
                        {currentTab === 'prompt' ? span.prompt : (span.response || '(No response captured)')}
                      </pre>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
