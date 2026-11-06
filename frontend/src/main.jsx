import React, { useEffect, useState } from 'react';
import { createRoot } from 'react-dom/client';
import './style.css';

function App() {
  const [status, setStatus] = useState(null);
  const [statusError, setStatusError] = useState(false);
  const [url, setUrl] = useState('');
  const [shortUrl, setShortUrl] = useState('');
  const [error, setError] = useState('');
  useEffect(() => {
    let mounted = true;
    const refresh = async () => {
      try {
        const response = await fetch('/api/status', { cache: 'no-store' });
        if (!response.ok) throw new Error();
        const result = await response.json();
        if (mounted) { setStatus(result); setStatusError(false); }
      } catch { if (mounted) { setStatus(null); setStatusError(true); } }
    };
    refresh();
    const timer = setInterval(refresh, 10000);
    return () => { mounted = false; clearInterval(timer); };
  }, []);
  const submit = async (event) => {
    event.preventDefault(); setError(''); setShortUrl('');
    try {
      const response = await fetch('/api/shorten', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ original_url: url }) });
      if (!response.ok) throw new Error(response.status === 503 ? 'Writing is currently unavailable.' : 'Please check the URL and try again.');
      const result = await response.json();
      setShortUrl(new URL(result.short_path, window.location.origin).href);
    } catch (err) { setError(err.message || 'Request failed.'); }
  };
  return <main><h1>URL Shortener</h1><p>Serving: {status?.serving_provider?.toUpperCase() ?? 'Unavailable'} · Role: {status?.role ?? 'Unknown'} · Mode: {status?.writer_mode ?? 'Unknown'}</p>{statusError && <p role="alert">Cannot connect to the API. Check that the backend is running; we will retry automatically.</p>}<form onSubmit={submit}><label htmlFor="url">Long URL</label><input id="url" type="url" required value={url} onChange={(e) => setUrl(e.target.value)} placeholder="https://example.com" /><button type="submit" disabled={!status || status.writer_mode !== 'active'}>Shorten</button></form>{shortUrl && <p>Short URL: <a href={shortUrl}>{shortUrl}</a></p>}{error && <p role="alert">{error}</p>}</main>;
}

createRoot(document.getElementById('root')).render(<App />);
