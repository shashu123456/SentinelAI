import { describe, it, expect, beforeEach, vi } from 'vitest';

const DEFAULT_API = 'https://sentinelai-backend-3lru.onrender.com';

async function loadConfig() {
  vi.resetModules();
  return import('./config.js');
}

describe('config', () => {
  beforeEach(() => {
    delete import.meta.env.VITE_API_URL;
    delete import.meta.env.VITE_WS_URL;
  });

  it('falls back to the production backend URL when no env vars are set', async () => {
    const { API_BASE, WS_BASE } = await loadConfig();
    expect(API_BASE).toBe(`${DEFAULT_API}/api`);
    expect(WS_BASE).toBe(`wss://${DEFAULT_API.replace('https://', '')}`);
  });

  it('uses VITE_API_URL when provided and converts http -> ws', async () => {
    import.meta.env.VITE_API_URL = 'http://localhost:8000';
    const { API_BASE, WS_BASE } = await loadConfig();
    expect(API_BASE).toBe('http://localhost:8000/api');
    expect(WS_BASE).toBe('ws://localhost:8000');
  });

  it('converts https -> wss', async () => {
    import.meta.env.VITE_API_URL = 'https://api.example.com';
    const { WS_BASE } = await loadConfig();
    expect(WS_BASE).toBe('wss://api.example.com');
  });

  it('strips trailing slashes from the base URL', async () => {
    import.meta.env.VITE_API_URL = 'https://api.example.com/';
    const { API_BASE, WS_BASE } = await loadConfig();
    expect(API_BASE).toBe('https://api.example.com/api');
    expect(WS_BASE).toBe('wss://api.example.com');
  });

  it('lets VITE_WS_URL override the WebSocket host independently', async () => {
    import.meta.env.VITE_API_URL = 'http://localhost:8000';
    import.meta.env.VITE_WS_URL = 'wss://ws.example.com';
    const { API_BASE, WS_BASE } = await loadConfig();
    expect(API_BASE).toBe('http://localhost:8000/api');
    expect(WS_BASE).toBe('wss://ws.example.com');
  });
});
