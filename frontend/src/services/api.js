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

// Auth calls must never be swallowed by the global 401 handler — a failed
// login has to surface the server's real message (e.g. "Invalid credentials"
// or the password-policy violation), not a generic "Unauthorized".
const AUTH_PATHS = new Set([
  '/auth/login',
  '/auth/register',
  '/auth/refresh',
  '/auth/forgot-password',
  '/auth/reset-password',
]);

// Statuses whose body can be missing or unusable: an edge proxy answers 413
// with an HTML page, slowapi answers 429 with {error}, and a dropped connection
// can leave nothing at all. Each one still needs a sentence the user can act on
// instead of the generic "Request failed".
const STATUS_MESSAGES = {
  413: 'That file is over the 5 MB upload limit. Split it, or upload a .zip of the files you need scanned.',
  429: 'Too many scans in a row. Uploads are limited to 10 per minute — wait a minute, then try again.',
};

// The archive guard rejects unsafe zips with "archive rejected: <reason>". The
// reason is precise but internal, so each known one gets a plain sentence that
// says what is wrong with the file the user dropped.
const ARCHIVE_REASONS = [
  [/not a valid zip/i, 'That file could not be opened as a .zip — it may be corrupt or not really an archive.'],
  [/path traversal|absolute path/i, 'That archive contains a path that would escape the scan directory, so it was refused.'],
  [/symlink/i, 'That archive contains a symlink, which is not allowed in an upload.'],
  [/compression ratio/i, 'That archive is compressed far beyond what real source code compresses to (a zip bomb), so it was refused.'],
  [/entry limit/i, 'That archive holds too many files to scan.'],
  [/larger than \d+ MB|exceeds \d+ MB/i, 'One file inside that archive is over the 2 MB per-file limit.'],
];

function humanizeArchiveRejection(message) {
  if (!/^archive rejected:/i.test(message)) return message;
  for (const [pattern, sentence] of ARCHIVE_REASONS) {
    if (pattern.test(message)) return sentence;
  }
  return message.replace(/^archive rejected:\s*/i, 'Upload rejected: ');
}

// FastAPI returns 422 validation failures as an array of {loc, msg, type}.
// Rendering that through `new Error(array)` produced "[object Object]", which
// is what users saw when a password did not meet the policy.
export function formatApiError(body, status) {
  const detail = body?.detail ?? body?.error?.message ?? body?.error ?? body;
  if (typeof detail === 'string' && detail.trim()) {
    const message = humanizeArchiveRejection(detail);
    // slowapi's template ("Rate limit exceeded: 10 per 1 minute") is readable
    // only if you know the machinery; the auth lockout ships a real sentence and
    // must keep it.
    if (status === 429 && /^rate limit exceeded/i.test(message)) {
      return STATUS_MESSAGES[429];
    }
    return message;
  }
  if (Array.isArray(detail)) {
    const parts = detail
      .map((item) => {
        if (typeof item === 'string') return item;
        // FastAPI wraps validator messages as "Value error, <message>"; drop the
        // prefix so the user sees the sentence, not the framework's furniture.
        const msg = String(item?.msg || item?.message || '').replace(/^Value error,\s*/i, '');
        const loc = Array.isArray(item?.loc)
          ? item.loc.filter((p) => p !== 'body' && p !== 'query' && p !== 'path').join('.')
          : '';
        return loc ? `${loc}: ${msg}` : msg;
      })
      .filter(Boolean);
    if (parts.length) return parts.join(' · ');
  }
  if (detail && typeof detail === 'object' && detail.message) return String(detail.message);
  return STATUS_MESSAGES[status] || 'Request failed';
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

  const isAuthCall = AUTH_PATHS.has(path);
  let response = await doFetch();

  if (
    response.status === 401 &&
    !isAuthCall &&
    path !== '/auth/refresh' &&
    localStorage.getItem('sentinelai_token')
  ) {
    try {
      await refreshSession();
      response = await doFetch();
    } catch {
      redirectToLogin();
      throw new Error('Session expired. Please sign in again.');
    }
  }

  if (response.status === 401 && !isAuthCall) {
    redirectToLogin();
    throw new Error('Session expired. Please sign in again.');
  }

  if (!response.ok) {
    // An empty object, not a placeholder string: a placeholder would short-
    // circuit the status mapping below and show the generic message everywhere.
    const err = await response.json().catch(() => ({}));
    if (
      response.status === 404 &&
      (!err.detail || err.detail === 'Not Found' || err.detail === undefined)
    ) {
      throw new Error(
        'This feature is not available on the connected backend. ' +
        'The server you are talking to is older than this frontend — deploy the current backend.',
      );
    }
    const message = formatApiError(err, response.status);
    throw new Error(response.status === 401 ? 'Invalid username or password.' : message);
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
  // kind selects the engine: 'spec' (OpenAPI), 'deps' (manifests) or 'code' (SAST).
  upload: (file, apiName, kind = 'spec') => {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('kind', kind);
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
  // The per-scanner wrappers (sast.scanFile, deps.scanFile) are gone: scanning
  // now goes through scans.upload(file, apiName, kind), which persists the scan.
  // The stateless /security/* endpoints stay for API clients only.
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