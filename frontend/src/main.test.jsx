// @vitest-environment jsdom
import React from 'react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { act, cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { App } from './main.jsx';

const reply = (status, body) => ({ ok: status >= 200 && status < 300, status, json: async () => body });
const current = (provider = 'gcp', mode = 'active') => ({ serving_provider: provider, role: provider === 'gcp' ? 'primary' : 'secondary', writer_mode: mode });
beforeEach(() => { sessionStorage.clear(); });
afterEach(() => { cleanup(); vi.restoreAllMocks(); vi.unstubAllGlobals(); });

describe('DR session UI', () => {
  it('creates a record with the provider from the response and restores this tab session', async () => {
    vi.stubGlobal('fetch', vi.fn(async (path, init) => {
      if (path === '/api/status') return reply(200, current());
      if (path === '/api/shorten') return reply(201, { code: 'Abcd1234', serving_provider: 'gcp' });
      if (path === '/api/urls/Abcd1234') return reply(200, { exists: true, origin_cloud: 'gcp' });
      throw Error(path);
    }));
    const view = render(<App />);
    await screen.findByText('Google Cloud', { exact: false });
    fireEvent.change(screen.getByLabelText('Long URL'), { target: { value: 'https://example.com' } });
    fireEvent.click(screen.getByRole('button', { name: 'Shorten' }));
    await screen.findByText('Abcd1234');
    await screen.findByText('Available');
    expect(JSON.parse(sessionStorage.getItem('mcdr-session-urls-v1'))).toEqual([{ code: 'Abcd1234', provider: 'gcp' }]);
    view.unmount(); render(<App />);
    expect(screen.getByText('Abcd1234')).toBeTruthy();
  });
  it('rechecks session records when the observed provider changes', async () => {
    sessionStorage.setItem('mcdr-session-urls-v1', JSON.stringify([{ code: 'Abcd1234', provider: 'gcp' }]));
    let next = current(); let refresh;
    const original = globalThis.setInterval;
    vi.spyOn(globalThis, 'setInterval').mockImplementation((fn, delay) => { if (delay === 10000) refresh = fn; return original(fn, delay); });
    vi.stubGlobal('fetch', vi.fn(async path => path === '/api/status' ? reply(200, next) : next.serving_provider === 'gcp' ? reply(200, { exists: true, origin_cloud: 'gcp' }) : reply(404, { detail: 'Short code not found' })));
    render(<App />); await screen.findByText('Available');
    next = current('aws', 'standby'); await act(async () => { await refresh(); });
    await screen.findByText('Not found');
    expect(screen.getByText(/Connection moved from GCP to AWS/)).toBeTruthy();
    expect(screen.getByRole('button', { name: 'Shorten' }).disabled).toBe(true);
  });
  it('marks stale status uncertain on network failure and disables writes', async () => {
    let refresh; const original = globalThis.setInterval;
    vi.spyOn(globalThis, 'setInterval').mockImplementation((fn, delay) => { if (delay === 10000) refresh = fn; return original(fn, delay); });
    const fetcher = vi.fn().mockResolvedValueOnce(reply(200, current())).mockRejectedValueOnce(Error('offline'));
    vi.stubGlobal('fetch', fetcher); render(<App />);
    await screen.findByText('Google Cloud', { exact: false });
    await act(async () => { await refresh(); });
    expect(screen.getByText('Connection uncertain')).toBeTruthy();
    expect(screen.getByRole('button', { name: 'Shorten' }).disabled).toBe(true);
  });
  it.each([403, 429, 503])('reports HTTP %s without creating a session entry', async code => {
    vi.stubGlobal('fetch', vi.fn(async path => path === '/api/status' ? reply(200, current()) : reply(code, {})));
    render(<App />); await screen.findByText('Google Cloud', { exact: false });
    fireEvent.change(screen.getByLabelText('Long URL'), { target: { value: 'https://example.com' } });
    fireEvent.click(screen.getByRole('button', { name: 'Shorten' }));
    await waitFor(() => expect(screen.getByRole('alert')).toBeTruthy());
    expect(JSON.parse(sessionStorage.getItem('mcdr-session-urls-v1'))).toEqual([]);
  });
  it('reports verification unavailable on backend errors', async () => {
    sessionStorage.setItem('mcdr-session-urls-v1', JSON.stringify([{ code: 'Abcd1234', provider: 'aws' }]));
    vi.stubGlobal('fetch', vi.fn(async path => path === '/api/status' ? reply(200, current('aws', 'frozen')) : reply(503, {})));
    render(<App />); await screen.findByText('Verification unavailable');
    expect(screen.getByRole('button', { name: 'Shorten' }).disabled).toBe(true);
  });
});

it('does not mark a conflicting origin as available', async () => {
  sessionStorage.setItem('mcdr-session-urls-v1', JSON.stringify([{ code: 'Abcd1234', provider: 'gcp' }]));
  vi.stubGlobal('fetch', vi.fn(async path => path === '/api/status' ? reply(200, current()) : reply(200, { exists: true, origin_cloud: 'aws' })));
  render(<App />);
  await screen.findByText('Verification unavailable');
  expect(screen.queryByText('Available')).toBeNull();
});


it('does not mistake a missing API Gateway route for a missing record', async () => {
  sessionStorage.setItem('mcdr-session-urls-v1', JSON.stringify([{ code: 'Abcd1234', provider: 'gcp' }]));
  vi.stubGlobal('fetch', vi.fn(async path => path === '/api/status' ? reply(200, current('aws', 'standby')) : reply(404, { message: 'Not Found' })));
  render(<App />);
  await screen.findByText('Verification unavailable');
  expect(screen.queryByText('Not found')).toBeNull();
});
