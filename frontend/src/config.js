const API_URL = (import.meta.env.VITE_API_URL || 'https://sentinelai-backend-3lru.onrender.com').replace(/\/+$/, '');
const WS_URL = (import.meta.env.VITE_WS_URL || API_URL).replace(/\/+$/, '');

export const API_BASE = `${API_URL}/api`;

export const WS_BASE = WS_URL.replace(/^http/, 'ws');
