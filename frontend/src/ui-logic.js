const KEY = 'mcdr-session-urls-v1';
export function readSession() {
  try {
    const data = JSON.parse(sessionStorage.getItem(KEY) || '[]');
    if (!Array.isArray(data)) return [];
    return data.filter(x => x && /^[A-Za-z0-9]{8}$/.test(x.code) && ['gcp', 'aws'].includes(x.provider)).map(({code, provider}) => ({code, provider}));
  } catch { return []; }
}
export function writeSession(items) { try { sessionStorage.setItem(KEY, JSON.stringify(items)); } catch { /* session storage may be disabled */ } }
export async function fetchStatus() {
  const response = await fetch('/api/status', { cache: 'no-store', signal: AbortSignal.timeout(8000) });
  if (!response.ok) throw new Error('status unavailable');
  const result = await response.json();
  if (!['gcp', 'aws'].includes(result.serving_provider) || !['primary', 'secondary'].includes(result.role) || !['active', 'frozen', 'standby'].includes(result.writer_mode)) throw new Error('invalid status');
  return result;
}
export async function verifyRecord(code, expectedOrigin) {
  try {
    const response = await fetch(`/api/urls/${encodeURIComponent(code)}`, { cache: 'no-store', signal: AbortSignal.timeout(8000) });
    if (response.status === 404) {
      const body = await response.json();
      return body.detail === 'Short code not found' ? 'Not found' : 'Verification unavailable';
    }
    if (!response.ok) return 'Verification unavailable';
    const data = await response.json();
    return data.exists === true && data.origin_cloud === expectedOrigin ? 'Available' : 'Verification unavailable';
  } catch { return 'Verification unavailable'; }
}
export function messageForStatus(status) {
  if (status === 403) return 'You are not authorized to create a short URL.';
  if (status === 429) return 'Too many requests. Please try again later.';
  if (status === 503) return 'Writing is currently unavailable. Please try again later.';
  return 'Could not create a short URL. Please check the URL and try again.';
}
