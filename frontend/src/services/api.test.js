import { describe, expect, it } from 'vitest';
import { formatApiError } from './api';

// The bodies below are copied from real responses captured from the running
// API (uvicorn on a throwaway SQLite file), so these cases match what the UI
// actually receives.

describe('formatApiError', () => {
  it('keeps the server sentence for an oversize upload', () => {
    expect(formatApiError({ detail: 'File too large. Max: 5MB' }, 413))
      .toBe('File too large. Max: 5MB');
  });

  it('falls back to a real sentence when a 413 carries no JSON (proxy page)', () => {
    const message = formatApiError({}, 413);
    expect(message).toContain('5 MB upload limit');
    expect(message).not.toBe('Request failed');
  });

  it('rewrites the limiter 429 template into plain language', () => {
    const message = formatApiError({ error: 'Rate limit exceeded: 10 per 1 minute' }, 429);
    expect(message).toContain('10 per minute');
    expect(message.toLowerCase()).not.toContain('rate limit exceeded');
  });

  it('keeps the auth lockout 429 message', () => {
    expect(
      formatApiError({ detail: 'Too many failed attempts. Please try again later.' }, 429),
    ).toBe('Too many failed attempts. Please try again later.');
  });

  it('explains a traversal archive rejection', () => {
    expect(formatApiError({ detail: 'archive rejected: path traversal entry' }, 422))
      .toBe('That archive contains a path that would escape the scan directory, so it was refused.');
  });

  it('names a zip bomb as a zip bomb', () => {
    const message = formatApiError(
      { detail: 'archive rejected: compression ratio 2048:1 exceeds 100:1' },
      422,
    );
    expect(message).toContain('zip bomb');
  });

  it('explains an entry-limit rejection', () => {
    expect(
      formatApiError({ detail: 'archive rejected: 10001 entries exceeds the 10000 entry limit' }, 422),
    ).toBe('That archive holds too many files to scan.');
  });

  it('keeps the allowed-extension list for a wrong file type', () => {
    expect(formatApiError({ detail: "Invalid file type for kind 'spec'. Allowed: .json, .yaml, .yml" }, 422))
      .toBe("Invalid file type for kind 'spec'. Allowed: .json, .yaml, .yml");
  });

  it('renders FastAPI validation arrays without [object Object]', () => {
    const body = { detail: [{ loc: ['body', 'password'], msg: 'Value error, Password is too weak' }] };
    expect(formatApiError(body, 422)).toBe('password: Password is too weak');
  });

  it('is still generic when nothing is known', () => {
    expect(formatApiError({}, 500)).toBe('Request failed');
  });
});
