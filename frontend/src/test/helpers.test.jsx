import { screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { flush, jsonResponse, mockApi, renderWithProviders, seedSession } from './helpers';

function Probe() {
  return <p>rendered through providers</p>;
}

describe('test helpers', () => {
  it('renders a component inside router and auth providers', async () => {
    renderWithProviders(<Probe />, { route: '/dashboard' });
    expect(await screen.findByText('rendered through providers')).toBeInTheDocument();
  });

  it('seeds a session AuthContext can restore', () => {
    const session = seedSession({ username: 'helper' });
    expect(session.username).toBe('helper');
    expect(localStorage.getItem('sentinelai_token')).toBe('test-token');
    expect(JSON.parse(localStorage.getItem('sentinelai_user')).username).toBe('helper');
  });

  it('builds fetch-compatible JSON responses', async () => {
    const response = jsonResponse({ ok: true }, { status: 201 });
    expect(response.ok).toBe(true);
    expect(response.status).toBe(201);
    await expect(response.json()).resolves.toEqual({ ok: true });
  });

  it('composes API mocks with a default request stub', async () => {
    const api = mockApi({ scans: { list: async () => ['a'] } });
    expect(await api.request('/anything')).toBeNull();
    expect(await api.scans.list()).toEqual(['a']);
  });

  it('flushes pending microtasks', async () => {
    await expect(flush()).resolves.toBeUndefined();
  });
});
