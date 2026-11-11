import { API_BASE } from '../config';

let refreshPromise = null;

function refreshSession() {
  if (!refreshPromise) {
    refreshPromise = fetch(`${API_BASE}/auth/refresh`, { method: 'POST', credentials: 'include' })
      .then(async (res) => {
        if (!res.ok) throw new Error('Refresh failed');
        const data = await res.json();
        localStorage.setItem('sentinelai_token', data.access_token);
        localStorage.setItem('sentinelai_user', JSON.stringify(data.user));
        window.dispatchEvent(new Event('sentinelai:auth-refresh'));
        return data;
      })
      .finally(() => {
        refreshPromise = null;
      });
  }
  return refreshPromise;
}

function redirectToLogin() {
  localStorage.removeItem('sentinelai_token');
  localStorage.removeItem('sentinelai_user');
  if (window.location.pathname !== '/login') {
    window.location.href = '/login';
  }
}

// Check if running in Electron
const isElectron = typeof window !== 'undefined' && window.electron !== undefined;

async function request(path, options = {}) {
  // In Electron, try IPC first for real-time data
  if (isElectron && window.electron) {
    try {
      const electronResult = await window.electron[`${path.replace('/', '')}`]();
      // If the electron method returns data, use it directly
      if (electronResult && !electronResult.startsWith('Error') && electronResult !== null) {
        return electronResult;
      }
    } catch (ipcError) {
      console.warn('IPC request failed, falling back to HTTP:', ipcError);
    }
  }

  const headers = { ...options.headers };
  const token = localStorage.getItem('sentinelai_token');
  if (token) headers['Authorization'] = `Bearer ${token}`;
  if (!(options.body instanceof FormData)) headers['Content-Type'] = 'application/json';

  const doFetch = () => fetch(`${API_BASE}${path}`, { ...options, headers, credentials: 'include' });

  let response = await doFetch();

  if (response.status === 401 && path !== '/auth/refresh') {
    try {
      await refreshSession();
      response = await doFetch();
    } catch {
      redirectToLogin();
      throw new Error('Unauthorized');
    }
  }

  if (response.status === 401) {
    redirectToLogin();
    throw new Error('Unauthorized');
  }

  if (!response.ok) {
    const err = await response.json().catch(() => ({ detail: 'Request failed' }));
    if (response.status === 404 && (!err.detail || err.detail === 'Not Found')) {
      throw new Error(
        'This feature is not available on the connected backend. ' +
        'The server you are talking to is older than this frontend — deploy the current backend.',
      );
    }
    throw new Error(err.detail || 'Request failed');
  }

  if (response.status === 204) return null;

  const contentType = response.headers.get('content-type');
  if (contentType && contentType.includes('application/json')) {
    return response.json();
  }
  return response;
}

// Keep existing exports but they'll use IPC in Electron
export const auth = {
  register: (data) => request('/auth/register', { method: 'POST', body: JSON.stringify(data) }),
  login: (data) => request('/auth/login', { method: 'POST', body: JSON.stringify(data) }),
  me: () => request('/auth/me'),
  refresh: () => request('/auth/refresh', { method: 'POST' }),
  logout: () => request('/auth/logout', { method: 'POST' }),
  logoutAll: () => request('/auth/logout-all', { method: 'POST' }),
  forgotPassword: (email) => request('/auth/forgot-password', { method: 'POST', body: JSON.stringify({ email }) }),
  resetPassword: (token, newPassword) => request('/auth/reset-password', { method: 'POST', body: JSON.stringify({ token, new_password: newPassword }) }),
};

export const scans = {
  list: () => request('/scans/'),
  get: (id) => request(`/scans/${id}`),
  dashboard: () => request('/scans/dashboard'),
  upload: (file, apiName) => {
    const formData = new FormData();
    formData.append('file', file);
    if (apiName) formData.append('api_name', apiName);
    return request('/scans/upload', { method: 'POST', body: formData });
  },
  uploadAsync: (file, apiName, enableAi = true) => {
    const formData = new FormData();
    formData.append('file', file);
    if (apiName) formData.append('api_name', apiName);
    formData.append('enable_ai', enableAi);
    return request('/scans/upload/async', { method: 'POST', body: formData });
  },
  getTask: (taskId) => request(`/scans/task/${taskId}`),
  delete: (id) => request(`/scans/${id}`, { method: 'DELETE' }),
  downloadPdf: async (id) => {
    const token = localStorage.getItem('sentinelai_token');
    const response = await fetch(`${API_BASE}/scans/${id}/report/pdf`, {
      headers: { 'Authorization': `Bearer ${token}` },
    });
    if (!response.ok) throw new Error('Failed to download PDF');
    const blob = await response.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `sentinelai-report-${id}.pdf`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    window.URL.revokeObjectURL(url);
  },
  downloadJson: async (id) => {
    const token = localStorage.getItem('sentinelai_token');
    const response = await fetch(`${API_BASE}/scans/${id}/report/json`, {
      headers: { 'Authorization': `Bearer ${token}` },
    });
    if (!response.ok) throw new Error('Failed to download JSON');
    const blob = await response.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `sentinelai-report-${id}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    window.URL.revokeObjectURL(url);
  },
};

export const security = {
  sast: {
    scanFile: (file) => {
      const formData = new FormData();
      formData.append('file', file);
      return request('/security/sast/scan', { method: 'POST', body: formData });
    },
    scanText: (code, filename) => {
      const formData = new FormData();
      formData.append('code', code);
      formData.append('filename', filename);
      return request('/security/sast/scan/text', { method: 'POST', body: formData });
    },
  },
  deps: {
    scanFile: (file) => {
      const formData = new FormData();
      formData.append('file', file);
      return request('/security/deps/scan', { method: 'POST', body: formData });
    },
  },
  copilot: {
    chat: (message, scanId) => request('/security/copilot/chat', {
      method: 'POST',
      body: JSON.stringify({ message, scan_id: scanId || null }),
    }),
    sidebar: () => request('/security/copilot/sidebar'),
    loadContext: (scanId) => request('/security/copilot/context', {
      method: 'POST',
      body: JSON.stringify({ scan_id: scanId || null }),
    }),
    clear: () => request('/security/copilot/clear', { method: 'POST' }),
    commands: () => request('/security/copilot/commands'),
  },
};

export const analytics = {
  getDashboard: () => request('/scans/analytics'),
};

export const organizations = {
  list: () => request('/organizations'),
  create: (data) => request('/organizations', { method: 'POST', body: JSON.stringify(data) }),
  get: (id) => request(`/organizations/${id}`),
  update: (id, data) => request(`/organizations/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
  getSettings: (orgId) => request(`/organizations/${orgId}/settings`),
  updateSettings: (orgId, data) => request(`/organizations/${orgId}/settings`, { method: 'PATCH', body: JSON.stringify(data) }),
  dashboard: (orgId) => request(`/organizations/${orgId}/dashboard`),
  analytics: (orgId) => request(`/organizations/${orgId}/analytics`),
  listMembers: (orgId) => request(`/organizations/${orgId}/members`),
  inviteMember: (orgId, data) => request(`/organizations/${orgId}/members`, { method: 'POST', body: JSON.stringify(data) }),
  updateMemberRole: (orgId, userId, data) => request(`/organizations/${orgId}/members/${userId}/role`, { method: 'PATCH', body: JSON.stringify(data) }),
  removeMember: (orgId, userId) => request(`/organizations/${orgId}/members/${userId}`, { method: 'DELETE' }),
};

export const teams = {
  list: (orgId) => request(`/organizations/${orgId}/teams`),
  create: (orgId, data) => request(`/organizations/${orgId}/teams`, { method: 'POST', body: JSON.stringify(data) }),
  get: (orgId, teamId) => request(`/organizations/${orgId}/teams/${teamId}`),
  addMember: (orgId, teamId, data) => request(`/organizations/${orgId}/teams/${teamId}/members`, { method: 'POST', body: JSON.stringify(data) }),
  removeMember: (orgId, teamId) => request(`/organizations/${orgId}/teams/${teamId}`, { method: 'DELETE' }),
};

export const invitations = {
  list: (orgId) => request(`/organizations/${orgId}/invitations`),
  send: (orgId, data) => request(`/organizations/${orgId}/invitations`, { method: 'POST', body: JSON.stringify(data) }),
  revoke: (orgId, inviteId) => request(`/organizations/${orgId}/invitations/${inviteId}`, { method: 'DELETE' }),
  accept: (orgId, token) => request(`/organizations/${orgId}/invitations/accept`, { method: 'POST', body: JSON.stringify({ token }) }),
  cleanup: (orgId) => request(`/organizations/${orgId}/invitations/cleanup`, { method: 'POST' }),
};

export const apiKeys = {
  list: (orgId) => request(`/organizations/${orgId}/api-keys`),
  create: (orgId, data) => request(`/organizations/${orgId}/api-keys`, { method: 'POST', body: JSON.stringify(data) }),
  revoke: (orgId, keyId) => request(`/organizations/${orgId}/api-keys/${keyId}`, { method: 'DELETE' }),
};

export const audit = {
  list: (params = {}) => {
    const qs = new URLSearchParams();
    Object.entries(params).forEach(([k, v]) => {
      if (v !== undefined && v !== null && v !== '') qs.set(k, String(v));
    });
    return request(`/audit/logs?${qs.toString()}`);
  },
  get: (id) => request(`/audit/logs/${id}`),
  stats: () => request('/audit/stats'),
  modules: () => request('/audit/modules'),
  actions: (module) => {
    const qs = module ? `?module=${module}` : '';
    return request(`/audit/actions${qs}`);
  },
  exportCsv: async (params = {}) => {
    const qs = new URLSearchParams();
    Object.entries(params).forEach(([k, v]) => {
      if (v !== undefined && v !== null && v !== '') qs.set(k, String(v));
    });
    const token = localStorage.getItem('sentinelai_token');
    const response = await fetch(`${API_BASE}/audit/export?${qs.toString()}`, {
      headers: { 'Authorization': `Bearer ${token}` },
    });
    if (!response.ok) throw new Error('Export failed');
    const blob = await response.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `audit-logs-${new Date().toISOString().split('T')[0]}.csv`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    window.URL.revokeObjectURL(url);
  },
};

export const testimonials = {
  list: () => request('/testimonials'),
};

export const health = {
  check: () => request('/health'),
  detailed: () => request('/health/detailed'),
  metrics: () => {
    if (isElectron && window.electron) {
      return window.electron.getMetricsSnapshot();
    }
    return fetch(`${API_BASE.replace('/api', '')}/metrics`).then(r => r.text());
  },
};

export { request };