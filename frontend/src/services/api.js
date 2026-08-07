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

async function request(path, options = {}) {
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
    throw new Error(err.detail || 'Request failed');
  }

  if (response.status === 204) return null;

  const contentType = response.headers.get('content-type');
  if (contentType && contentType.includes('application/json')) {
    return response.json();
  }
  return response;
}

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

export const health = {
  check: () => request('/health'),
};
