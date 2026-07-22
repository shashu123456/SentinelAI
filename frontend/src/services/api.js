const API_BASE = import.meta.env.VITE_API_URL || '/api';

async function request(path, options = {}) {
  const token = localStorage.getItem('sentinelai_token');
  const headers = { ...options.headers };

  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  if (!(options.body instanceof FormData)) {
    headers['Content-Type'] = 'application/json';
  }

  const response = await fetch(`${API_BASE}${path}`, { ...options, headers });

  if (response.status === 401) {
    localStorage.removeItem('sentinelai_token');
    localStorage.removeItem('sentinelai_user');
    window.location.href = '/login';
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
