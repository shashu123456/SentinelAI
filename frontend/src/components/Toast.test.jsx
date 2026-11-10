import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect } from 'vitest';
import { ToastProvider, useToast } from './Toast';

function Trigger() {
  const { success, error, info } = useToast();
  return (
    <div>
      <button onClick={() => success('Saved successfully')}>success</button>
      <button onClick={() => error('Something broke')}>error</button>
      <button onClick={() => info('FYI')}>info</button>
    </div>
  );
}

function renderToasts() {
  return render(
    <ToastProvider>
      <Trigger />
    </ToastProvider>,
  );
}

describe('Toast', () => {
  it('renders a success toast with its message', async () => {
    const user = userEvent.setup();
    renderToasts();
    await user.click(screen.getByRole('button', { name: 'success' }));
    expect(screen.getByText('Saved successfully')).toBeInTheDocument();
    expect(screen.getByText('Saved successfully').closest('.toast')).toHaveClass('toast-success');
  });

  it('renders an error toast with the error styling', async () => {
    const user = userEvent.setup();
    renderToasts();
    await user.click(screen.getByRole('button', { name: 'error' }));
    expect(screen.getByText('Something broke')).toBeInTheDocument();
    expect(screen.getByText('Something broke').closest('.toast')).toHaveClass('toast-error');
  });

  it('removes a toast when its close button is clicked', async () => {
    const user = userEvent.setup();
    renderToasts();
    await user.click(screen.getByRole('button', { name: 'success' }));
    const toast = screen.getByText('Saved successfully');
    expect(toast).toBeInTheDocument();
    await user.click(toast.closest('.toast').querySelector('.toast-close'));
    // Removal waits for the exit animation before unmounting.
    await waitFor(() =>
      expect(screen.queryByText('Saved successfully')).not.toBeInTheDocument()
    );
  });

  it('stacks multiple toasts', async () => {
    const user = userEvent.setup();
    renderToasts();
    await user.click(screen.getByRole('button', { name: 'success' }));
    await user.click(screen.getByRole('button', { name: 'info' }));
    expect(screen.getByText('Saved successfully')).toBeInTheDocument();
    expect(screen.getByText('FYI')).toBeInTheDocument();
  });
});
