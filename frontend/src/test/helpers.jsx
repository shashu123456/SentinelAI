/**
 * Shared testing helpers.
 *
 * Tests stay short and consistent by using these instead of re-implementing
 * provider nesting, session seeding, and API mocking:
 *
 *   import { renderWithProviders, seedSession, mockApi } from '../test/helpers';
 */
import { render } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';

import { AuthProvider } from '../context/AuthContext';

/** Seed a logged-in session the way AuthContext expects it. */
export function seedSession({ token = 'test-token', username = 'tester' } = {}) {
  localStorage.setItem('sentinelai_token', token);
  localStorage.setItem(
    'sentinelai_user',
    JSON.stringify({ username, email: `${username}@example.com` }),
  );
  return { token, username };
}

/** Render a component inside the app's providers. */
export function renderWithProviders(
  ui,
  { route = '/', withAuth = true, withRouter = true } = {},
) {
  let tree = ui;
  if (withAuth) tree = <AuthProvider>{tree}</AuthProvider>;
  if (withRouter) tree = <MemoryRouter initialEntries={[route]}>{tree}</MemoryRouter>;
  return render(tree);
}

/**
 * Build a mock for `../services/api`.
 *
 *   vi.mock('../services/api', () => mockApi({
 *     scans: { list: vi.fn().mockResolvedValue([]) },
 *   }));
 *
 * Pass `request` to stub the low-level fetch wrapper, or named namespaces to
 * stub the typed helpers. Unspecified members resolve to `undefined`.
 */
export function mockApi(shape = {}, { request } = {}) {
  return { request: request ?? (async () => null), ...shape };
}

/** A `fetch`-compatible JSON response for tests that stub global fetch. */
export function jsonResponse(body, init = {}) {
  const text = typeof body === 'string' ? body : JSON.stringify(body);
  return {
    ok: (init.status ?? 200) < 400,
    status: init.status ?? 200,
    statusText: init.statusText ?? 'OK',
    headers: new Headers({ 'Content-Type': 'application/json' }),
    json: async () => JSON.parse(text),
    text: async () => text,
  };
}

/** Resolve after pending microtasks (props updates, awaited promises). */
export function flush() {
  return new Promise((resolve) => setTimeout(resolve, 0));
}
