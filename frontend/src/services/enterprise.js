import { API_ROOT } from '../config';

const TOKEN_KEY = 'sentinelai_token';

async function rootRequest(path, options = {}) {
  const headers = { ...options.headers };
  const token = localStorage.getItem(TOKEN_KEY);
  if (token) headers['Authorization'] = `Bearer ${token}`;
  if (options.body && !(options.body instanceof FormData)) {
    headers['Content-Type'] = 'application/json';
  }

  const res = await fetch(`${API_ROOT}${path}`, { ...options, headers, credentials: 'include' });

  if (res.status === 401) {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem('sentinelai_user');
    throw new Error('Session expired. Please sign in again.');
  }

  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    const detail = typeof body.detail === 'string' ? body.detail : null;
    if (res.status === 403) {
      throw new Error(detail || 'You do not have permission to view this organization.');
    }
    if (res.status === 404) {
      if (!detail || detail === 'Not Found') {
        throw new Error(
          'This feature is not available on the connected backend. ' +
          'The server you are talking to is older than this frontend — deploy the current backend.',
        );
      }
      throw new Error(detail);
    }
    throw new Error(detail || `Request failed (${res.status})`);
  }

  if (res.status === 204) return null;
  const type = res.headers.get('content-type');
  if (type && type.includes('application/json')) return res.json();
  return res;
}

const qs = (params = {}) => {
  const search = new URLSearchParams();
  Object.entries(params).forEach(([k, v]) => {
    if (v !== undefined && v !== null && v !== '') search.set(k, String(v));
  });
  const s = search.toString();
  return s ? `?${s}` : '';
};

export const enterprise = {
  scheduledScans: (orgId) => rootRequest(`/orgs/${orgId}/scheduled-scans`),
  createScheduledScan: (orgId, data) => rootRequest(`/orgs/${orgId}/scheduled-scans`, { method: 'POST', body: JSON.stringify(data) }),
  deleteScheduledScan: (orgId, id) => rootRequest(`/orgs/${orgId}/scheduled-scans/${id}`, { method: 'DELETE' }),

  templates: (orgId) => rootRequest(`/orgs/${orgId}/templates`),
  createTemplate: (orgId, data) => rootRequest(`/orgs/${orgId}/templates`, { method: 'POST', body: JSON.stringify(data) }),

  policies: (orgId) => rootRequest(`/orgs/${orgId}/policies`),
  createPolicy: (orgId, data) => rootRequest(`/orgs/${orgId}/policies`, { method: 'POST', body: JSON.stringify(data) }),

  webhooks: (orgId) => rootRequest(`/orgs/${orgId}/webhooks`),
  createWebhook: (orgId, data) => rootRequest(`/orgs/${orgId}/webhooks`, { method: 'POST', body: JSON.stringify(data) }),
  testWebhook: (orgId, id) => rootRequest(`/orgs/${orgId}/webhooks/${id}/test`, { method: 'POST' }),

  compliance: (orgId) => rootRequest(`/orgs/${orgId}/compliance`),
  complianceFrameworks: () => rootRequest('/compliance/frameworks'),

  exports: (orgId) => rootRequest(`/orgs/${orgId}/exports`),
  createExport: (orgId, data) => rootRequest(`/orgs/${orgId}/exports`, { method: 'POST', body: JSON.stringify(data) }),

  executiveReport: (orgId) => rootRequest(`/orgs/${orgId}/executive-report`),
  analyticsHistory: (orgId, months = 6) => rootRequest(`/orgs/${orgId}/analytics/history${qs({ months })}`),

  compare: (scanId1, scanId2) =>
    rootRequest('/scans/compare', {
      method: 'POST',
      body: JSON.stringify({ scan_id_1: Number(scanId1), scan_id_2: Number(scanId2) }),
    }),
};
