// API client for LLM Observatory with automatic demo data fallback for public deployment previews

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

// Mock data generator for recruiters when the backend is offline (e.g., Vercel preview)
const MOCK_DATA = {
  overview: {
    total_spans: 1420,
    total_cost: 3.8420,
    active_sessions: 14,
    error_rate: 0.024,
    avg_latency: 685.2,
    spans_today: 412,
    top_models: [
      { model: 'gpt-4o', call_count: 520, total_cost: 2.82 },
      { model: 'gpt-4o-mini', call_count: 480, total_cost: 0.12 },
      { model: 'claude-3-5-sonnet', call_count: 310, total_cost: 0.85 },
      { model: 'gemini-1.5-flash', call_count: 110, total_cost: 0.052 }
    ],
    cost_trend: [
      { hour: '09:00 AM', cost_usd: 0.12 },
      { hour: '10:00 AM', cost_usd: 0.28 },
      { hour: '11:00 AM', cost_usd: 0.42 },
      { hour: '12:00 PM', cost_usd: 0.15 },
      { hour: '01:00 PM', cost_usd: 0.32 },
      { hour: '02:00 PM', cost_usd: 0.28 },
      { hour: '03:00 PM', cost_usd: 0.54 },
      { hour: '04:00 PM', cost_usd: 0.72 }
    ],
    recent_traces: [
      { trace_id: 'tr-recruiter-demo-1', name: 'response-generator', model: 'gpt-4o', latency_ms: 850, cost_usd: 0.0035, error: null, created_at: new Date().toISOString() },
      { trace_id: 'tr-recruiter-demo-1', name: 'product-matcher', model: 'gpt-4o-mini', latency_ms: 220, cost_usd: 0.00012, error: null, created_at: new Date(Date.now() - 2000).toISOString() },
      { trace_id: 'tr-recruiter-demo-2', name: 'sentiment-analyser', model: 'claude-3-5-sonnet', latency_ms: 410, cost_usd: 0.0015, error: null, created_at: new Date(Date.now() - 5000).toISOString() },
      { trace_id: 'tr-recruiter-demo-3', name: 'failing-parser', model: 'gpt-4-turbo', latency_ms: 180, cost_usd: 0.0, error: 'RateLimitError: Rate limit exceeded, retry after 30s', created_at: new Date(Date.now() - 10000).toISOString() }
    ]
  },
  traces: {
    total: 3,
    limit: 100,
    offset: 0,
    data: [
      {
        id: 101,
        span_id: 'sp-1',
        trace_id: 'tr-recruiter-demo-1',
        session_id: 'user-recruiter',
        name: 'intent-extractor',
        model: 'gpt-4o-mini',
        prompt: 'User message: "I need running shoes under 3000 rupees"',
        response: '{\n  "action": "search",\n  "category": "shoes",\n  "constraints": {\n    "price_max": 3000,\n    "type": "running"\n  }\n}',
        tokens_in: 45,
        tokens_out: 42,
        cost_usd: 0.00003,
        latency_ms: 320,
        error: null,
        created_at: new Date().toISOString()
      },
      {
        id: 102,
        span_id: 'sp-2',
        trace_id: 'tr-recruiter-demo-1',
        session_id: 'user-recruiter',
        name: 'product-matcher',
        model: 'gpt-4o-mini',
        prompt: 'Find products matching intent: {"action": "search", "category": "shoes", ...}',
        response: '[\n  {"name": "Nike Pegasus 40", "price": 2800},\n  {"name": "Adidas Duramo Speed", "price": 2400}\n]',
        tokens_in: 80,
        tokens_out: 65,
        cost_usd: 0.00005,
        latency_ms: 280,
        error: null,
        created_at: new Date().toISOString()
      },
      {
        id: 103,
        span_id: 'sp-3',
        trace_id: 'tr-recruiter-demo-1',
        session_id: 'user-recruiter',
        name: 'response-generator',
        model: 'gpt-4o',
        prompt: 'Generate conversational shopping response for products: Nike Pegasus, Adidas Duramo...',
        response: 'Here are two great running shoes under 3000 rupees:\n1. **Nike Pegasus 40** (₹2,800)\n2. **Adidas Duramo Speed** (₹2,400)\n\nWhich one would you like to know more about?',
        tokens_in: 250,
        tokens_out: 85,
        cost_usd: 0.0025,
        latency_ms: 950,
        error: null,
        created_at: new Date().toISOString()
      },
      {
        id: 104,
        span_id: 'sp-4',
        trace_id: 'tr-recruiter-demo-2',
        session_id: 'analytics-recruiter',
        name: 'sentiment-analyser',
        model: 'claude-3-5-sonnet',
        prompt: 'Analyze review: "The battery dies too fast, terrible product."',
        response: 'Negative',
        tokens_in: 32,
        tokens_out: 4,
        cost_usd: 0.00015,
        latency_ms: 410,
        error: null,
        created_at: new Date().toISOString()
      },
      {
        id: 105,
        span_id: 'sp-5',
        trace_id: 'tr-recruiter-demo-3',
        session_id: 'ops-recruiter',
        name: 'failing-parser',
        model: 'gpt-4-turbo',
        prompt: 'Parse input logs: ...',
        response: '',
        tokens_in: 12000,
        tokens_out: 0,
        cost_usd: 0.12,
        latency_ms: 180,
        error: 'RateLimitError: Rate limit exceeded, retry after 30s',
        created_at: new Date().toISOString()
      }
    ]
  },
  costSummary: [
    { model: 'gpt-4o', total_cost: 2.82, call_count: 520, avg_cost_per_call: 0.0054, total_tokens: 380400 },
    { model: 'claude-3-5-sonnet', total_cost: 0.85, call_count: 310, avg_cost_per_call: 0.0027, total_tokens: 188400 },
    { model: 'gpt-4o-mini', total_cost: 0.12, call_count: 480, avg_cost_per_call: 0.00025, total_tokens: 880400 },
    { model: 'gemini-1.5-flash', total_cost: 0.052, call_count: 110, avg_cost_per_call: 0.00047, total_tokens: 144500 }
  ],
  costTimeseries: [
    { hour: '2026-07-08T09:00:00Z', cost_usd: 0.12 },
    { hour: '2026-07-08T10:00:00Z', cost_usd: 0.28 },
    { hour: '2026-07-08T11:00:00Z', cost_usd: 0.42 },
    { hour: '2026-07-08T12:00:00Z', cost_usd: 0.15 },
    { hour: '2026-07-08T01:00:00Z', cost_usd: 0.32 },
    { hour: '2026-07-08T02:00:00Z', cost_usd: 0.28 },
    { hour: '2026-07-08T03:00:00Z', cost_usd: 0.54 },
    { hour: '2026-07-08T04:00:00Z', cost_usd: 0.72 }
  ],
  latencyPercentiles: [
    { model: 'gpt-4o-mini', p50: 220, p95: 580, p99: 950 },
    { model: 'gpt-4o', p50: 850, p95: 1950, p99: 3100 },
    { model: 'claude-3-5-sonnet', p50: 410, p95: 1150, p99: 1800 },
    { model: 'gemini-1.5-flash', p50: 180, p95: 380, p99: 620 }
  ],
  latencyTimeseries: [
    { hour: '2026-07-08T09:00:00Z', latency_ms: 320 },
    { hour: '2026-07-08T10:00:00Z', latency_ms: 450 },
    { hour: '2026-07-08T11:00:00Z', latency_ms: 620 },
    { hour: '2026-07-08T12:00:00Z', latency_ms: 250 },
    { hour: '2026-07-08T01:00:00Z', latency_ms: 540 },
    { hour: '2026-07-08T02:00:00Z', latency_ms: 380 },
    { hour: '2026-07-08T03:00:00Z', latency_ms: 850 },
    { hour: '2026-07-08T04:00:00Z', latency_ms: 710 }
  ],
  alerts: [
    { id: 1, alert_type: 'high_latency', threshold_value: 5000, current_value: 5200, session_id: 'user-slow-demo', model: 'gpt-4o', message: 'Span 516a39f5 (gpt-4o) took 5200ms (threshold: 5000ms).', fired_at: new Date(Date.now() - 15 * 60 * 1000).toISOString(), resolved: false },
    { id: 2, alert_type: 'error_spike', threshold_value: 0.10, current_value: 0.15, session_id: null, model: null, message: 'Error rate is 15.0% over the last 5 minutes (threshold: 10%).', fired_at: new Date(Date.now() - 45 * 60 * 1000).toISOString(), resolved: false }
  ]
};

async function fetchJson(endpoint, options = {}) {
  const url = `${API_URL}${endpoint}`;
  try {
    const res = await fetch(url, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
    });
    if (!res.ok) {
      throw new Error(`API Error: ${res.status} ${res.statusText}`);
    }
    return await res.json();
  } catch (error) {
    console.error(`Failed to fetch from endpoint: ${endpoint}. Falling back to demo preview data.`);
    throw error;
  }
}

export async function fetchOverview() {
  return fetchJson('/api/stats/overview').catch(() => MOCK_DATA.overview);
}

export async function fetchTraces(params = {}) {
  const query = new URLSearchParams();
  if (params.session_id) query.append('session_id', params.session_id);
  if (params.model) query.append('model', params.model);
  if (params.from_dt) query.append('from_dt', params.from_dt);
  if (params.to_dt) query.append('to_dt', params.to_dt);
  if (params.limit) query.append('limit', params.limit);
  if (params.offset) query.append('offset', params.offset);

  const queryString = query.toString() ? `?${query.toString()}` : '';
  return fetchJson(`/api/traces${queryString}`).catch(() => {
    let filteredData = [...MOCK_DATA.traces.data];
    if (params.session_id) {
      filteredData = filteredData.filter(t => t.session_id.includes(params.session_id));
    }
    if (params.model) {
      filteredData = filteredData.filter(t => t.model === params.model);
    }
    return {
      total: filteredData.length,
      limit: params.limit || 100,
      offset: params.offset || 0,
      data: filteredData
    };
  });
}

export async function fetchTrace(traceId) {
  return fetchJson(`/api/traces/${traceId}`).catch(() => {
    return MOCK_DATA.traces.data.filter(s => s.trace_id === traceId);
  });
}

export async function fetchSessions() {
  return fetchJson('/api/traces/sessions').catch(() => {
    return [
      { session_id: 'user-recruiter', span_count: 3, total_cost: 0.00258 },
      { session_id: 'analytics-recruiter', span_count: 1, total_cost: 0.00015 },
      { session_id: 'ops-recruiter', span_count: 1, total_cost: 0.12 }
    ];
  });
}

export async function fetchCostSummary(params = {}) {
  const query = new URLSearchParams();
  if (params.from_dt) query.append('from_dt', params.from_dt);
  if (params.to_dt) query.append('to_dt', params.to_dt);
  
  const queryString = query.toString() ? `?${query.toString()}` : '';
  return fetchJson(`/api/cost/summary${queryString}`).catch(() => MOCK_DATA.costSummary);
}

export async function fetchCostTimeseries(params = {}) {
  const query = new URLSearchParams();
  if (params.from_dt) query.append('from_dt', params.from_dt);
  if (params.to_dt) query.append('to_dt', params.to_dt);
  if (params.interval) query.append('interval', params.interval);
  
  const queryString = query.toString() ? `?${query.toString()}` : '';
  return fetchJson(`/api/cost/timeseries${queryString}`).catch(() => MOCK_DATA.costTimeseries);
}

export async function fetchLatencyPercentiles(params = {}) {
  const query = new URLSearchParams();
  if (params.model) query.append('model', params.model);
  if (params.hours) query.append('hours', params.hours);
  
  const queryString = query.toString() ? `?${query.toString()}` : '';
  return fetchJson(`/api/latency/percentiles${queryString}`).catch(() => MOCK_DATA.latencyPercentiles);
}

export async function fetchLatencyTimeseries(params = {}) {
  const query = new URLSearchParams();
  if (params.model) query.append('model', params.model);
  if (params.hours) query.append('hours', params.hours);
  
  const queryString = query.toString() ? `?${query.toString()}` : '';
  return fetchJson(`/api/latency/timeseries${queryString}`).catch(() => MOCK_DATA.latencyTimeseries);
}

export async function fetchAlerts(params = {}) {
  const query = new URLSearchParams();
  if (params.resolved !== undefined) query.append('resolved', params.resolved);
  if (params.alert_type) query.append('alert_type', params.alert_type);
  if (params.limit) query.append('limit', params.limit);
  
  const queryString = query.toString() ? `?${query.toString()}` : '';
  return fetchJson(`/api/alerts${queryString}`).catch(() => {
    return MOCK_DATA.alerts.filter(a => a.resolved === (params.resolved === 'true' || params.resolved === true));
  });
}

export async function resolveAlert(alertId) {
  return fetchJson(`/api/alerts/${alertId}/resolve`, { method: 'POST' }).catch(() => {
    MOCK_DATA.alerts = MOCK_DATA.alerts.map(a => a.id === alertId ? { ...a, resolved: true } : a);
    return { status: 'resolved' };
  });
}
