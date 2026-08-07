import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, beforeEach } from 'vitest';
import { AuthProvider, useAuth } from './AuthContext';

function Probe({ onReady }) {
  const { user, token, loading, isAuthenticated, login, logout } = useAuth();
  return (
    <div>
      <div data-testid="loading">{String(loading)}</div>
      <div data-testid="user">{user ? user.username : 'none'}</div>
      <div data-testid="token">{token || 'none'}</div>
      <div data-testid="auth">{String(isAuthenticated)}</div>
      <button onClick={() => login('tok123', { username: 'alice', email: 'a@x.com' })}>login</button>
      <button onClick={logout}>logout</button>
    </div>
  );
}

function renderWithAuth() {
  return render(
    <AuthProvider>
      <Probe />
    </AuthProvider>,
  );
}

describe('AuthContext', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it('starts logged out when localStorage is empty', async () => {
    renderWithAuth();
    expect(await screen.findByTestId('auth')).toHaveTextContent('false');
    expect(screen.getByTestId('user')).toHaveTextContent('none');
    expect(screen.getByTestId('token')).toHaveTextContent('none');
  });

  it('restores an existing session from localStorage on mount', async () => {
    localStorage.setItem('sentinelai_token', 'saved-token');
    localStorage.setItem('sentinelai_user', JSON.stringify({ username: 'bob', email: 'b@x.com' }));
    renderWithAuth();
    await waitFor(() => expect(screen.getByTestId('loading')).toHaveTextContent('false'));
    expect(screen.getByTestId('auth')).toHaveTextContent('true');
    expect(screen.getByTestId('user')).toHaveTextContent('bob');
    expect(screen.getByTestId('token')).toHaveTextContent('saved-token');
  });

  it('ignores corrupted saved user data and stays logged out', async () => {
    localStorage.setItem('sentinelai_token', 'bad-token');
    localStorage.setItem('sentinelai_user', '{not-json');
    renderWithAuth();
    await waitFor(() => expect(screen.getByTestId('loading')).toHaveTextContent('false'));
    expect(screen.getByTestId('auth')).toHaveTextContent('false');
  });

  it('login persists the session and updates state', async () => {
    const user = userEvent.setup();
    renderWithAuth();
    await screen.findByTestId('auth');
    await user.click(screen.getByRole('button', { name: 'login' }));
    expect(screen.getByTestId('auth')).toHaveTextContent('true');
    expect(screen.getByTestId('user')).toHaveTextContent('alice');
    expect(localStorage.getItem('sentinelai_token')).toBe('tok123');
    expect(JSON.parse(localStorage.getItem('sentinelai_user')).username).toBe('alice');
  });

  it('logout clears state and localStorage', async () => {
    const user = userEvent.setup();
    localStorage.setItem('sentinelai_token', 'tok');
    localStorage.setItem('sentinelai_user', JSON.stringify({ username: 'x' }));
    renderWithAuth();
    await waitFor(() => expect(screen.getByTestId('auth')).toHaveTextContent('true'));
    await user.click(screen.getByRole('button', { name: 'logout' }));
    expect(screen.getByTestId('auth')).toHaveTextContent('false');
    expect(localStorage.getItem('sentinelai_token')).toBeNull();
    expect(localStorage.getItem('sentinelai_user')).toBeNull();
  });
});
