import { StrictMode, useEffect, useState } from 'react';
import { createRoot } from 'react-dom/client';
import './style.css';

function App() {
  const [status, setStatus] = useState<'loading' | 'connected' | 'unavailable'>('loading');
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    const timeout = window.setTimeout(() => {
      controller.abort();
      setStatus('unavailable');
    }, 5000);
    setStatus('loading');
    fetch('/api/health', { signal: controller.signal })
      .then(async response => {
        if (!response.ok) throw new Error('Health request failed');
        const health = await response.json();
        if (health.status !== 'ok' || health.service !== 'platform-api') {
          throw new Error('Unexpected health response');
        }
        setStatus('connected');
      })
      .catch(() => { if (!controller.signal.aborted) setStatus('unavailable'); })
      .finally(() => window.clearTimeout(timeout));
    return () => {
      controller.abort();
      window.clearTimeout(timeout);
    };
  }, [attempt]);

  return (
    <main>
      <header><a className="brand" href="/">S / H <span>SunHacks 2026</span></a><span className="tag">Local workspace</span></header>
      <section className="hero">
        <p className="eyebrow">Application security & resilience</p>
        <h1>Understand the application.<br /><em>Connect the consequences.</em></h1>
        <p className="intro">One place to connect dependencies, security exposure, and recovery to the capabilities your users rely on.</p>
      </section>
      <section className="workspace" aria-labelledby="workspace-heading">
        <div className="section-title"><div><p className="eyebrow">Your applications</p><h2 id="workspace-heading">Start with the evidence</h2></div><span className="tag">Foundation</span></div>
        <div className="empty"><span className="graph-icon" aria-hidden="true">◇</span><h3>No application connected yet</h3><p>Connect an application to explore its capabilities, dependencies, and supporting evidence. The sample store is the next implementation step.</p></div>
        <div className="connection" role="status"><span className={`dot ${status}`} /><span>{status === 'loading' ? 'Connecting to platform API…' : status === 'connected' ? 'Platform API connected' : 'Platform API unavailable'}</span>{status === 'unavailable' && <button onClick={() => setAttempt(value => value + 1)}>Retry connection</button>}</div>
      </section>
      <section className="pillars" aria-label="Platform direction">
        {[
          ['01', 'Discover', 'Map services and dependencies to business capabilities using observed evidence.'],
          ['02', 'Understand exposure', 'Connect identity, reachability, and known vulnerabilities to application impact.'],
          ['03', 'Validate resilience', 'Predict failures, run controlled experiments, and verify recovery.'],
        ].map(([number, title, description]) => <article key={number}><span className="number">{number} / Planned</span><h3>{title}</h3><p>{description}</p></article>)}
      </section>
      <footer>Evidence coverage: no collectors connected. Application security and resilience have not been assessed.</footer>
    </main>
  );
}

createRoot(document.getElementById('root')!).render(<StrictMode><App /></StrictMode>);
