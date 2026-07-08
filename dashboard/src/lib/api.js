// API client for LLM Observatory

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

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
    console.error(`Failed to fetch from endpoint: ${endpoint}`, error);
    throw error;
  }
}

export async function fetchOverview() {
  return fetchJson('/api/stats/overview');
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
  return fetchJson(`/api/traces${queryString}`);
}

export async function fetchTrace(traceId) {
  return fetchJson(`/api/traces/${traceId}`);
}

export async function fetchSessions() {
  return fetchJson('/api/traces/sessions');
}

export async function fetchCostSummary(params = {}) {
  const query = new URLSearchParams();
  if (params.from_dt) query.append('from_dt', params.from_dt);
  if (params.to_dt) query.append('to_dt', params.to_dt);
  
  const queryString = query.toString() ? `?${query.toString()}` : '';
  return fetchJson(`/api/cost/summary${queryString}`);
}

export async function fetchCostTimeseries(params = {}) {
  const query = new URLSearchParams();
  if (params.from_dt) query.append('from_dt', params.from_dt);
  if (params.to_dt) query.append('to_dt', params.to_dt);
  if (params.interval) query.append('interval', params.interval);
  
  const queryString = query.toString() ? `?${query.toString()}` : '';
  return fetchJson(`/api/cost/timeseries${queryString}`);
}

export async function fetchLatencyPercentiles(params = {}) {
  const query = new URLSearchParams();
  if (params.model) query.append('model', params.model);
  if (params.hours) query.append('hours', params.hours);
  
  const queryString = query.toString() ? `?${query.toString()}` : '';
  return fetchJson(`/api/latency/percentiles${queryString}`);
}

export async function fetchLatencyTimeseries(params = {}) {
  const query = new URLSearchParams();
  if (params.model) query.append('model', params.model);
  if (params.hours) query.append('hours', params.hours);
  
  const queryString = query.toString() ? `?${query.toString()}` : '';
  return fetchJson(`/api/latency/timeseries${queryString}`);
}

export async function fetchAlerts(params = {}) {
  const query = new URLSearchParams();
  if (params.resolved !== undefined) query.append('resolved', params.resolved);
  if (params.alert_type) query.append('alert_type', params.alert_type);
  if (params.limit) query.append('limit', params.limit);
  
  const queryString = query.toString() ? `?${query.toString()}` : '';
  return fetchJson(`/api/alerts${queryString}`);
}

export async function resolveAlert(alertId) {
  return fetchJson(`/api/alerts/${alertId}/resolve`, { method: 'POST' });
}
