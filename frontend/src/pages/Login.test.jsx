import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { AuthProvider } from '../context/AuthContext';
import Login from './Login';

const loginMock = vi.fn();
const registerMock = vi.fn();

vi.mock('../services/api', () => ({
  auth: {
    login: (...args) => loginMock(...args),
    register: (...args) => registerMock(...args),
  },
}));

function renderLogin() {
  return render(
    <MemoryRouter>
      <AuthProvider>
        <Login />
      </AuthProvider>
    </MemoryRouter>,
  );
}

describe('Login', () => {
  beforeEach(() => {
    loginMock.mockReset();
    registerMock.mockReset();
  });

  it('renders the sign-in form by default', () => {
    const { container } = renderLogin();
    expect(container.querySelector('.login-btn')).toBeInTheDocument();
    expect(container.querySelector('.login-tab')).toHaveTextContent('Sign In');
    expect(screen.getByPlaceholderText('analyst@sentinel')).toBeInTheDocument();
    expect(screen.getByPlaceholderText('Enter password')).toBeInTheDocument();
    expect(screen.queryByPlaceholderText('Enter email')).not.toBeInTheDocument();
  });

  it('switches to register mode and shows the email field', async () => {
    const user = userEvent.setup();
    renderLogin();
    await user.click(screen.getByRole('button', { name: 'Register' }));
    expect(screen.getByPlaceholderText('analyst@company.io')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /create account/i })).toBeInTheDocument();
  });

  it('submits login credentials and stores the session', async () => {
    const { container } = renderLogin();
    const user = userEvent.setup();
    loginMock.mockResolvedValue({
      access_token: 'token-abc',
      user: { username: 'alice', email: 'alice@example.com' },
    });

    await user.type(screen.getByPlaceholderText('analyst@sentinel'), 'alice');
    await user.type(screen.getByPlaceholderText('Enter password'), 'secret123');
    await user.click(container.querySelector('.login-btn'));

    await waitFor(() => {
      expect(loginMock).toHaveBeenCalledWith({ username: 'alice', password: 'secret123' });
    });
    await waitFor(() => {
      expect(localStorage.getItem('sentinelai_token')).toBe('token-abc');
    });
  });

  it('submits registration data in register mode', async () => {
    const user = userEvent.setup();
    registerMock.mockResolvedValue({
      access_token: 'token-reg',
      user: { username: 'bob', email: 'bob@example.com' },
    });
    renderLogin();

    await user.click(screen.getByRole('button', { name: 'Register' }));
    await user.type(screen.getByPlaceholderText('analyst@sentinel'), 'bob');
    await user.type(screen.getByPlaceholderText('analyst@company.io'), 'bob@example.com');
    await user.type(screen.getByPlaceholderText('Enter password'), 'secret123');
    await user.click(screen.getByRole('button', { name: /create account/i }));

    await waitFor(() => {
      expect(registerMock).toHaveBeenCalledWith({
        username: 'bob',
        email: 'bob@example.com',
        password: 'secret123',
      });
    });
  });

  it('shows an error message when authentication fails', async () => {
    const { container } = renderLogin();
    const user = userEvent.setup();
    loginMock.mockRejectedValue(new Error('Invalid credentials'));

    await user.type(screen.getByPlaceholderText('analyst@sentinel'), 'alice');
    await user.type(screen.getByPlaceholderText('Enter password'), 'wrong');
    await user.click(container.querySelector('.login-btn'));

    expect(await screen.findByText(/Invalid credentials/i)).toBeInTheDocument();
  });

  it('toggles password visibility', async () => {
    const { container } = renderLogin();
    const user = userEvent.setup();
    const passwordInput = screen.getByPlaceholderText('Enter password');
    expect(passwordInput).toHaveAttribute('type', 'password');
    await user.click(container.querySelector('.pw-toggle'));
    expect(screen.getByPlaceholderText('Enter password')).toHaveAttribute('type', 'text');
  });
});
