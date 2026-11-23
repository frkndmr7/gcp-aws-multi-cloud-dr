import React, { useEffect, useRef, useState } from 'react';
import { createRoot } from 'react-dom/client';
import { readSession, writeSession, fetchStatus, verifyRecord, messageForStatus } from './ui-logic.js';
import './style.css';

export function App() {
  const [status, setStatus] = useState(null);
  const [connectionError, setConnectionError] = useState(false);
  const [notice, setNotice] = useState('');
  const [items, setItems] = useState(readSession);
  const [availability, setAvailability] = useState({});
  const [url, setUrl] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const lastProvider = useRef(null);
  useEffect(() => {
    let live = true, pending = false;
    async function refresh() {
      if (pending) return;
      pending = true;
      try {
        const next = await fetchStatus();
        if (!live) return;
        if (lastProvider.current && lastProvider.current !== next.serving_provider) {
          setNotice(`Connection moved from ${lastProvider.current.toUpperCase()} to ${next.serving_provider.toUpperCase()}.`);
        }
        lastProvider.current = next.serving_provider;
        setStatus(next); setConnectionError(false);
      } catch {
        if (live) { setStatus(null); setConnectionError(true); }
      } finally { pending = false; }
    }
    refresh();
    const timer = setInterval(refresh, 10000);
    return () => { live = false; clearInterval(timer); };
  }, []);
  useEffect(() => { writeSession(items); }, [items]);
  useEffect(() => {
    let live = true;
    if (!status) { setAvailability({}); return () => { live = false; }; }
    setAvailability({});
    Promise.all(items.map(async item => [item.code, await verifyRecord(item.code, item.provider)])).then(results => {
      if (live) setAvailability(Object.fromEntries(results));
    });
    return () => { live = false; };
  }, [status?.serving_provider, connectionError, items]);
  const submit = async event => {
    event.preventDefault();
    if (!status || connectionError || status.writer_mode !== 'active' || busy) return;
    setBusy(true); setError('');
    try {
      const response = await fetch('/api/shorten', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ original_url: url }) });
      if (!response.ok) throw new Error(messageForStatus(response.status));
      const result = await response.json();
      if (!/^[A-Za-z0-9]{8}$/.test(result.code) || !['gcp', 'aws'].includes(result.serving_provider)) {
        throw new Error('The URL may have been created, but the response could not be verified.');
      }
      setItems(current => [{ code: result.code, provider: result.serving_provider }, ...current.filter(item => item.code !== result.code)]);
      setUrl('');
    } catch (err) { setError(err.message || 'Request failed.'); }
    finally { setBusy(false); }
  };
  const label = status?.serving_provider === 'gcp' ? 'Google Cloud' : status?.serving_provider === 'aws' ? 'AWS' : 'Unknown';
  const canWrite = !!status && !connectionError && status.writer_mode === 'active' && !busy;
  return <main>
    <h1>URL Shortener</h1>
    <section aria-label="Current connection" className="status-panel">
      <p className="eyebrow">CURRENT CONNECTION</p>
      {status ? <><h2>{label} <span>— {status.role === 'primary' ? 'Primary' : 'Secondary'}</span></h2><p>Writer mode: <strong>{status.writer_mode[0].toUpperCase() + status.writer_mode.slice(1)}</strong></p></> : <h2>Connection uncertain</h2>}
      <p className="hint">This is the backend reached by this browser, not global Route 53 health.</p>
      {connectionError && <p role="alert">Cannot connect to the API. We will retry automatically.</p>}
      {notice && <p role="status">{notice}</p>}
    </section>
    <form onSubmit={submit}><label htmlFor="url">Long URL</label><input id="url" type="url" required value={url} onChange={e => setUrl(e.target.value)} placeholder="https://example.com" disabled={!canWrite} /><button type="submit" disabled={!canWrite}>{busy ? 'Shortening…' : 'Shorten'}</button></form>
    {!canWrite && !busy && <p className="hint">URL creation is unavailable while the writer is not active or the connection is uncertain.</p>}
    {error && <p role="alert">{error}</p>}
    <section><h2>Your Shortened URLs</h2><p className="hint">Only URLs created in this browser tab are shown.</p>
      {!items.length ? <p>No URLs created in this tab yet.</p> : <ul>{items.map(item => {
        const link = `${window.location.origin}/r/${item.code}`;
        return <li key={item.code}><strong>{item.code}</strong> <span className="badge">{item.provider === 'gcp' ? 'Google Cloud' : 'AWS'}</span><br /><a href={link}>{link}</a><br /><small>{availability[item.code] || 'Verification unavailable'}</small></li>;
      })}</ul>}
      {items.length > 0 && <p className="hint">Not found can mean replication is delayed. Verification unavailable can mean a network or service error.</p>}
    </section>
  </main>;
}

if (document.getElementById('root')) createRoot(document.getElementById('root')).render(<App />);
