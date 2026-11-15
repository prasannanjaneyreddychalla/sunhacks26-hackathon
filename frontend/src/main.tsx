import { StrictMode, useEffect, useRef, useState } from "react";
import type { ButtonHTMLAttributes } from "react";
import { createRoot } from "react-dom/client";
import "./style.css";

type Result = {
  status: string;
  detail: string;
  latency_ms?: number | null;
  checked_at: string;
};
type Phase = {
  results: Record<string, Result>;
  started_at: string;
  ended_at?: string;
};
type Run = {
  id: string;
  target_id: string | null;
  status: string;
  phase: string;
  started_at: string;
  message: string;
  phases: Record<string, Phase>;
  actions: { at: string; label: string }[];
  interrupted_submission?: { recovered: boolean; detail: string };
};
type Service = {
  id: string;
  label: string;
  description: string;
  calls: number;
  errors: number;
  last_status: number | null;
  last_seen: string | null;
};
type Target = {
  id: string;
  label: string;
  service: string;
  operation: string;
  resource: string;
  description: string;
  predicted: string[];
};
type Capability = {
  id: string;
  label: string;
  services: string[];
  path: string[];
  note?: string;
};
type Observation = {
  id: number;
  at: string;
  service: string;
  operation: string;
  caller: string;
  status: number;
  phase: string;
  resource: string;
  injected: number;
  latency_ms: number;
};
type Snapshot = {
  connected: boolean;
  connection: { app_url: string } | null;
  services: Service[];
  targets: Target[];
  capabilities: Capability[];
  run: Run | null;
  runs: {
    id: string;
    target_id: string | null;
    status: string;
    started_at: string;
  }[];
  active_run_id: string | null;
  fault: { target_id: string; expires_at: string } | null;
  events: Observation[];
};

const paths = {
  grid: "M3 3h7v7H3zM14 3h7v7h-7zM3 14h7v7H3zM14 14h7v7h-7z",
  pulse: "M2 12h5l3-8 4 16 3-8h5",
  arrow: "M4 12h16M14 6l6 6-6 6",
  external: "M14 3h7v7M21 3L10 14M10 5H4v15h15v-6",
  check: "M5 12l4 4L19 6",
  close: "M6 6l12 12M6 18L18 6",
  clock: "M12 7v5l4 2M22 12a10 10 0 1 1-20 0 10 10 0 0 1 20 0",
  search: "M21 21l-5-5M18 10a7 7 0 1 1-14 0 7 7 0 0 1 14 0",
  menu: "M4 6h16M4 12h16M4 18h16",
  cloud: "M6 18a4 4 0 1 1 .8-7.9A6 6 0 0 1 18 8a5 5 0 0 1 0 10H6z",
  help: "M9 8a3 3 0 1 1 5 2c-2 1-2 2-2 3M12 17v.1M22 12a10 10 0 1 1-20 0 10 10 0 0 1 20 0",
  stop: "M6 6h12v12H6z",
  play: "M7 4l14 8-14 8z",
  chevron: "M9 5l7 7-7 7",
} as const;
function Icon({
  name,
  size = 20,
}: {
  name: keyof typeof paths;
  size?: number;
}) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.7"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d={paths[name]} />
    </svg>
  );
}
function Mark() {
  return (
    <span className="mark" aria-hidden="true">
      <i />
      <i />
      <i />
      <i />
    </span>
  );
}
function Button({
  children,
  className = "",
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement>) {
  const [ripple, setRipple] = useState<{
    x: number;
    y: number;
    id: number;
  } | null>(null);
  return (
    <button
      {...props}
      className={"button " + className}
      onPointerDown={(event) => {
        const box = event.currentTarget.getBoundingClientRect();
        setRipple({
          x: event.clientX - box.left,
          y: event.clientY - box.top,
          id: Date.now(),
        });
      }}
    >
      {children}
      {ripple && (
        <i
          key={ripple.id}
          className="ripple"
          style={{ left: ripple.x, top: ripple.y }}
          onAnimationEnd={() => setRipple(null)}
        />
      )}
    </button>
  );
}
function Badge({
  result,
  pending = false,
}: {
  result?: Result;
  pending?: boolean;
}) {
  const status = result?.status;
  return (
    <span
      className={"badge " + (status || (pending ? "checking" : "empty"))}
      title={result?.detail}
    >
      {status === "pass" ? (
        <Icon name="check" size={13} />
      ) : status === "fail" ? (
        <Icon name="close" size={13} />
      ) : null}
      {status
        ? (
            {
              pass: "Working",
              fail: "Failed",
              blocked: "Blocked",
              unknown: "Unknown",
            } as Record<string, string>
          )[status] || status
        : pending
          ? "Checking"
          : "—"}
    </span>
  );
}
function time(value: string) {
  return new Date(value).toLocaleTimeString([], {
    hour: "numeric",
    minute: "2-digit",
    second: "2-digit",
  });
}
function About({ close }: { close: () => void }) {
  const ref = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    ref.current?.showModal();
  }, []);
  return (
    <dialog ref={ref} onCancel={close} aria-labelledby="about-title">
      <div className="dialog-head">
        <h2 id="about-title">Meet Pitwall</h2>
        <Button
          className="icon-button"
          aria-label="Close about"
          onClick={close}
        >
          <Icon name="close" />
        </Button>
      </div>
      <p className="pitch">
        Pitwall shows you what breaks when part of your app goes down. Switch
        off a dependency, see which features stop working, and check that
        everything recovers.
      </p>
      <p>
        This lab uses the real Quiz application and a local AWS emulator.
        Results come from HTTP journeys and captured application requests.
      </p>
      <p>
        Paths are defined from the application source. Internal managed-service
        links are not fully traced. Available services do not establish security
        or resilience.
      </p>
      <a href="http://localhost:8000/docs" target="_blank" rel="noreferrer">
        API documentation <Icon name="external" size={14} />
      </a>
      <div className="dialog-actions">
        <Button className="primary" onClick={close}>
          Got it
        </Button>
      </div>
    </dialog>
  );
}

function App() {
  const [data, setData] = useState<Snapshot | null>(null);
  const [error, setError] = useState("");
  const [pending, setPending] = useState(false);
  const [targetId, setTargetId] = useState("score-writes");
  const [duration, setDuration] = useState(45);
  const [view, setView] = useState("experiment");
  const [query, setQuery] = useState("");
  const [selectedService, setSelectedService] = useState<string | null>(null);
  const [selectedCap, setSelectedCap] = useState("score");
  const [selectedPhase, setSelectedPhase] = useState("during");
  const [history, setHistory] = useState("");
  const [about, setAbout] = useState(false);
  const [navOpen, setNavOpen] = useState(false);
  const [tick, setTick] = useState(Date.now());
  const search = useRef<HTMLInputElement>(null);
  useEffect(() => {
    let active = true;
    const controller = new AbortController();
    async function poll() {
      try {
        const response = await fetch(
          "/api/pitwall" + (history ? "?run_id=" + history : ""),
          { signal: controller.signal },
        );
        if (!response.ok)
          throw new Error(
            "Could not load Pitwall (HTTP " + response.status + ")",
          );
        const next = await response.json();
        if (!Array.isArray(next.services) || !Array.isArray(next.capabilities))
          throw new Error("Unexpected Pitwall response");
        if (active) {
          setData(next);
          setError("");
        }
      } catch (problem) {
        if (active)
          setError(
            problem instanceof Error
              ? problem.message
              : "Connection interrupted",
          );
      }
    }
    void poll();
    const interval = window.setInterval(poll, 1800);
    return () => {
      active = false;
      controller.abort();
      window.clearInterval(interval);
    };
  }, [history]);
  useEffect(() => {
    const interval = window.setInterval(() => setTick(Date.now()), 1000);
    return () => window.clearInterval(interval);
  }, []);
  useEffect(() => {
    function key(event: KeyboardEvent) {
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        search.current?.focus();
      }
      if (event.key === "Escape") setNavOpen(false);
    }
    window.addEventListener("keydown", key);
    return () => window.removeEventListener("keydown", key);
  }, []);
  const run = data?.run;
  const busy = Boolean(data?.active_run_id) || pending;
  const target = data?.targets.find((item) => item.id === targetId);
  const runTarget = data?.targets.find((item) => item.id === run?.target_id);
  const results =
    run?.phases.during?.results || run?.phases.baseline?.results || {};
  const recovered = run?.phases.recovery?.results;
  const freshRecovered =
    recovered &&
    Object.keys(recovered).length === 9 &&
    Object.values(recovered).every((result) => result.status === "pass");
  const pass = Object.values(results).filter(
    (result) => result.status === "pass",
  ).length;
  const failed = Object.values(results).filter(
    (result) => result.status === "fail",
  ).length;
  const blocked = Object.values(results).filter(
    (result) => result.status === "blocked",
  ).length;
  const cap = data?.capabilities.find((item) => item.id === selectedCap);
  const selectedResult = run?.phases[selectedPhase]?.results[selectedCap];
  const remaining = data?.fault
    ? Math.max(0, Math.ceil((Date.parse(data.fault.expires_at) - tick) / 1000))
    : 0;
  async function action(baseline: boolean) {
    setPending(true);
    setError("");
    setHistory("");
    try {
      const response = await fetch("/api/experiments", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          target_id: baseline ? null : targetId,
          duration_seconds: duration,
        }),
      });
      const value = await response.json();
      if (!response.ok)
        throw new Error(value.detail || "Could not start the check");
      const next = await fetch("/api/pitwall");
      setData(await next.json());
      setSelectedPhase(baseline ? "baseline" : "during");
      setView("experiment");
    } catch (problem) {
      setError(problem instanceof Error ? problem.message : "Request failed");
    } finally {
      setPending(false);
    }
  }
  async function restore() {
    try {
      const response = await fetch("/api/experiments/restore", {
        method: "POST",
      });
      if (!response.ok) throw new Error("Restore request failed");
      const next = await fetch("/api/pitwall");
      setData(await next.json());
    } catch (problem) {
      setError(
        problem instanceof Error ? problem.message : "Restore request failed",
      );
    }
  }
  function navigation(next: string) {
    setView(next);
    setNavOpen(false);
  }
  const filtered =
    data?.services.filter((service) =>
      (service.label + " " + service.description)
        .toLowerCase()
        .includes(query.toLowerCase()),
    ) || [];
  const observed =
    data?.events
      .filter(
        (event) =>
          event.phase === selectedPhase &&
          cap?.services.includes(event.service) &&
          (cap.path.some((node) => node.includes(event.caller)) ||
            (selectedCap === "interface" && event.operation === "GetObject")),
      )
      .slice(0, 6) || [];
  return (
    <div className="console">
      <a className="skip-link" href="#workspace">
        Skip to workspace
      </a>
      <header className="topbar">
        <div className="brand-group">
          <Button
            className="icon-button hamburger"
            aria-label="Toggle navigation"
            onClick={() => setNavOpen(!navOpen)}
          >
            <Icon name="menu" />
          </Button>
          <a className="brand" href="/">
            <Mark />
            <span>Pitwall</span>
          </a>
          <span className="brand-divider" />
          <span className="workspace-name">
            Quiz lab <span className="local-chip">Local</span>
          </span>
        </div>
        <label className="search">
          <Icon name="search" size={19} />
          <input
            ref={search}
            aria-label="Filter services"
            placeholder="Find a service"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
          />
          <kbd>Ctrl K</kbd>
        </label>
        <div className="top-actions">
          <span
            className={
              "connection " +
              (error ? "offline" : data?.connected ? "online" : "")
            }
          >
            <i />
            {error
              ? "Disconnected"
              : data?.connected
                ? "Quiz lab connected"
                : "Quiz lab not connected"}
          </span>
          <Button
            className="icon-button"
            aria-label="About Pitwall"
            onClick={() => setAbout(true)}
          >
            <Icon name="help" />
          </Button>
          <span className="avatar">P</span>
        </div>
      </header>
      {navOpen && (
        <button
          className="scrim"
          aria-label="Close navigation"
          onClick={() => setNavOpen(false)}
        />
      )}
      <aside className={"sidebar " + (navOpen ? "open" : "")}>
        <div className="nav-label">APPLICATION RESILIENCE</div>
        <nav aria-label="Main navigation">
          <Button
            className={"nav-item " + (view === "experiment" ? "selected" : "")}
            aria-current={view === "experiment" ? "page" : undefined}
            onClick={() => navigation("experiment")}
          >
            <Icon name="grid" />
            Experiment lab
          </Button>
          <Button
            className={"nav-item " + (view === "activity" ? "selected" : "")}
            aria-current={view === "activity" ? "page" : undefined}
            onClick={() => navigation("activity")}
          >
            <Icon name="pulse" />
            Request activity
          </Button>
          <Button className="nav-item" onClick={() => setAbout(true)}>
            <Icon name="help" />
            About Pitwall
          </Button>
        </nav>
        <div className="sidebar-app">
          <span className="service-icon blue">
            <Icon name="cloud" />
          </span>
          <strong>Serverless Quiz</strong>
          <p>
            One application.
            <br />
            The whole dependency story.
          </p>
          <a
            href={
              data?.connection?.app_url ||
              "http://localhost:4567/quiz-lab-webapp/index.html"
            }
            target="_blank"
            rel="noreferrer"
          >
            Open Quiz app <Icon name="external" size={14} />
          </a>
        </div>
        <div className="sidebar-footer">
          <span className="tiny-colors">
            <i />
            <i />
            <i />
            <i />
          </span>
          <p>
            See what breaks.
            <br />
            Know what recovers.
          </p>
          <small>Built for SunHacks 2026</small>
        </div>
      </aside>
      <main id="workspace">
        <div className="breadcrumb">
          Workspace <Icon name="chevron" size={13} /> Serverless Quiz{" "}
          <Icon name="chevron" size={13} />{" "}
          {view === "experiment" ? "Experiments" : "Activity"}
        </div>
        <div className="page-heading">
          <div>
            <span className="eyebrow">PITWALL / QUIZ LAB</span>
            <h1>
              {view === "experiment"
                ? "See what breaks."
                : "Follow every call."}
            </h1>
            <p>
              {view === "experiment"
                ? "Test a dependency. See the impact. Verify recovery."
                : "Observed application requests through the local Pitwall gateway."}
            </p>
          </div>
          <a
            className="button outlined"
            href={
              data?.connection?.app_url ||
              "http://localhost:4567/quiz-lab-webapp/index.html"
            }
            target="_blank"
            rel="noreferrer"
          >
            Open Quiz app <Icon name="external" size={16} />
          </a>
        </div>
        {error && (
          <div className="alert fail" role="alert">
            {error}. Last loaded results may be stale.
          </div>
        )}
        {!data?.connected && !error && (
          <div className="alert">
            {data
              ? "Connect the running Quiz lab with scripts/pitwall.ps1 Up before starting an experiment."
              : "Connecting to Pitwall…"}
          </div>
        )}
        <section className="control-panel" aria-label="Experiment controls">
          <div className="controls-top">
            <span className="section-kicker">
              <Icon name="pulse" size={17} />
              CONTROLLED EXPERIMENT
            </span>
            <span className="scope-label">
              One target · local lab only · automatic restore
            </span>
          </div>
          <div className="controls">
            <label className="target-field">
              <span>Dependency to interrupt</span>
              <select
                aria-label="Dependency to interrupt"
                value={targetId}
                disabled={busy}
                onChange={(event) => {
                  setTargetId(event.target.value);
                  setSelectedService(null);
                }}
              >
                {(data?.targets || []).map((item) => (
                  <option key={item.id} value={item.id}>
                    {
                      data?.services.find(
                        (service) => service.id === item.service,
                      )?.label
                    }{" "}
                    · {item.label}
                  </option>
                ))}
              </select>
            </label>
            <label className="duration-field">
              <span>Maximum fault window</span>
              <select
                aria-label="Maximum fault window"
                value={duration}
                disabled={busy}
                onChange={(event) => setDuration(Number(event.target.value))}
              >
                <option value={30}>30 seconds</option>
                <option value={45}>45 seconds</option>
                <option value={60}>60 seconds</option>
              </select>
            </label>
            <Button
              className="outlined"
              disabled={busy || !data?.connected}
              onClick={() => action(true)}
            >
              Check baseline
            </Button>
            <Button
              className="primary"
              disabled={busy || !data?.connected}
              onClick={() => action(false)}
            >
              <Icon name="play" size={16} />
              Run experiment
            </Button>
            <Button
              className="restore"
              disabled={!busy && !data?.fault}
              onClick={restore}
            >
              <Icon name="stop" size={15} />
              Restore all
            </Button>
          </div>
          <div className="control-note">
            <span>
              {target?.description || "Choose a dependency to begin."}
            </span>
            <span>Failure mode: HTTP 503</span>
          </div>
        </section>
        <section
          className={"run-strip " + (data?.fault ? "fault-active" : "")}
          aria-live="polite"
        >
          <div>
            <span className={"live-dot " + (busy ? "pulsing" : "")} />
            <strong>
              {data?.fault
                ? "Fault active · restores in " + remaining + "s"
                : busy
                  ? "Checks in progress"
                  : run
                    ? "Latest result"
                    : "Ready when you are"}
            </strong>
            <span>
              {run?.message ||
                "Start with a baseline to see the application working normally."}
            </span>
          </div>
          <label className="history">
            <Icon name="clock" size={15} />
            <select
              aria-label="Experiment history"
              value={history}
              disabled={busy}
              onChange={(event) => setHistory(event.target.value)}
            >
              <option value="">Latest run</option>
              {data?.runs.map((item) => (
                <option key={item.id} value={item.id}>
                  {time(item.started_at)} ·{" "}
                  {data.targets.find((t) => t.id === item.target_id)?.label ||
                    "Baseline"}{" "}
                  · {item.status}
                </option>
              ))}
            </select>
          </label>
        </section>
        {view === "experiment" ? (
          <>
            <section className="metrics" aria-label="Measured results">
              <Metric
                label={
                  run?.phases.during
                    ? "Working during fault"
                    : "Baseline working"
                }
                value={Object.keys(results).length ? pass + " / 9" : "—"}
                color="blue"
                detail={
                  runTarget
                    ? Object.keys(run?.phases.during?.results || {}).length ===
                      9
                      ? runTarget.predicted.length +
                        " affected expected · " +
                        (failed + blocked) +
                        " observed"
                      : "Expected to affect " +
                        runTarget.predicted.length +
                        (runTarget.predicted.length === 1
                          ? " capability"
                          : " capabilities")
                    : "Capabilities verified by journeys"
                }
              />
              <Metric
                label="Failed capabilities"
                value={Object.keys(results).length ? String(failed) : "—"}
                color="red"
                detail="Expected result was not returned"
              />
              <Metric
                label="Blocked downstream"
                value={Object.keys(results).length ? String(blocked) : "—"}
                color="yellow"
                detail="An earlier step did not complete"
              />
              <Metric
                label="Working after restore"
                value={
                  recovered
                    ? Object.values(recovered).filter(
                        (result) => result.status === "pass",
                      ).length + " / 9"
                    : "—"
                }
                color="green"
                detail={
                  recovered
                    ? "Fresh requests checked after the fault"
                    : "Recovery has not been measured"
                }
              />
            </section>
            <div className="comparison">
              <section className="panel dependencies">
                <div className="panel-heading">
                  <div>
                    <h2>Dependencies</h2>
                    <p>
                      {data?.services.length || 0} configured services ·
                      request-level evidence
                    </p>
                  </div>
                  <span className="tag">LOCALSTACK</span>
                </div>
                <div className="list-caption">
                  <span>SERVICE</span>
                  <span>API CALLS / ERRORS</span>
                </div>
                {filtered.map((service, index) => (
                  <button
                    className={
                      "service-row " +
                      (selectedService === service.id ||
                      (!selectedService && target?.service === service.id)
                        ? "focused"
                        : "")
                    }
                    key={service.id}
                    onClick={() =>
                      setSelectedService(
                        selectedService === service.id ? null : service.id,
                      )
                    }
                    aria-pressed={selectedService === service.id}
                  >
                    <span className={"service-letter color-" + (index % 4)}>
                      {service.label.slice(0, 1)}
                    </span>
                    <span className="service-copy">
                      <strong>{service.label}</strong>
                      <small>
                        {service.last_status === null
                          ? service.id === "lambda" &&
                            data?.events.some((event) =>
                              event.caller.endsWith("Function"),
                            )
                            ? "Functions observed as callers"
                            : "No API requests observed"
                          : service.last_status >= 500
                            ? "Errors observed"
                            : "Last request responded"}
                      </small>
                    </span>
                    <span className="request-count">
                      {service.calls}
                      <small className={service.errors ? "error-count" : ""}>
                        {service.errors
                          ? service.errors + " errors"
                          : "0 errors"}
                      </small>
                    </span>
                  </button>
                ))}
                {!filtered.length && (
                  <p className="empty-note">No services match this filter.</p>
                )}
                <div className="panel-foot">
                  Counts belong to the selected run. Last responses include live
                  traffic. Unobserved services have no measured request status.
                </div>
              </section>
              <section className="panel capabilities">
                <div className="panel-heading">
                  <div>
                    <h2>What can the app do?</h2>
                    <p>The same journeys. Three points in time.</p>
                  </div>
                  <span className="tag">MEASURED</span>
                </div>
                <div className="table-wrap">
                  <table className="capability-table">
                    <thead>
                      <tr>
                        <th>CAPABILITY</th>
                        <th>BEFORE</th>
                        <th>WITH FAULT</th>
                        <th>AFTER</th>
                      </tr>
                    </thead>
                    <tbody>
                      {data?.capabilities.map((item) => (
                        <tr
                          key={item.id}
                          className={
                            (selectedCap === item.id ? "selected-cap " : "") +
                            (selectedService &&
                            item.services.includes(selectedService)
                              ? "related"
                              : "")
                          }
                        >
                          <th scope="row">
                            <button
                              className="cap-name"
                              onClick={() => setSelectedCap(item.id)}
                            >
                              {item.label}
                              <Icon name="chevron" size={12} />
                            </button>
                          </th>
                          {["baseline", "during", "recovery"].map((phase) => (
                            <td key={phase}>
                              <button
                                className="result-button"
                                aria-label={
                                  item.label + " " + phase + " details"
                                }
                                onClick={() => {
                                  setSelectedCap(item.id);
                                  setSelectedPhase(phase);
                                }}
                              >
                                <Badge
                                  result={run?.phases[phase]?.results[item.id]}
                                  pending={
                                    run?.status === "running" &&
                                    run.phase === phase
                                  }
                                />
                              </button>
                            </td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                {!run && (
                  <div className="empty-comparison">
                    <Icon name="pulse" size={25} />
                    <strong>A baseline turns assumptions into evidence.</strong>
                    <p>
                      Run the real Quiz journeys, then compare what changes.
                    </p>
                  </div>
                )}
                <div className="legend">
                  <span>
                    <i className="green-dot" />
                    Working
                  </span>
                  <span>
                    <i className="red-dot" />
                    Failed
                  </span>
                  <span>
                    <i className="yellow-dot" />
                    Blocked by an earlier step
                  </span>
                  <span>
                    <i />
                    Unknown / not checked
                  </span>
                </div>
                {run?.interrupted_submission && (
                  <div
                    className={
                      "recovery-note " +
                      (run.interrupted_submission.recovered
                        ? "recovered"
                        : "gap")
                    }
                  >
                    <Icon name="pulse" size={19} />
                    <div>
                      <strong>
                        {run.interrupted_submission.recovered
                          ? "Submission result is available"
                          : freshRecovered
                            ? "New requests work. An earlier score is still missing."
                            : "An accepted submission still has no saved result."}
                      </strong>
                      <p>{run.interrupted_submission.detail}</p>
                    </div>
                  </div>
                )}
                <div className="cap-footer">
                  <span>
                    {runTarget
                      ? (run?.phases.during
                          ? "Fault tested: "
                          : "Selected fault: ") + runTarget.label
                      : "Baseline check · no fault"}
                  </span>
                  <span>Private test data · no real email</span>
                </div>
              </section>
            </div>
            <section className="panel evidence">
              <div className="panel-heading">
                <div>
                  <h2>Understand the path</h2>
                  <p>
                    {cap?.label || "Select a capability to inspect its path."}
                  </p>
                </div>
                <div className="phase-tabs">
                  {["baseline", "during", "recovery"].map((phase) => (
                    <Button
                      key={phase}
                      className={selectedPhase === phase ? "active" : ""}
                      onClick={() => setSelectedPhase(phase)}
                    >
                      {
                        (
                          {
                            baseline: "Before",
                            during: "With fault",
                            recovery: "After",
                          } as Record<string, string>
                        )[phase]
                      }
                    </Button>
                  ))}
                </div>
              </div>
              <div className="evidence-body">
                <div className="path-label">SOURCE-DEFINED PATH</div>
                <div className="path">
                  {cap?.path.map((node, index) => (
                    <span className="path-part" key={node}>
                      <span className="path-node">{node}</span>
                      {index < cap.path.length - 1 && (
                        <Icon name="arrow" size={17} />
                      )}
                    </span>
                  ))}
                </div>
                <div className="result-detail">
                  <Badge result={selectedResult} />
                  <span>
                    {selectedResult?.detail ||
                      "This capability has not been measured in this phase."}
                  </span>
                </div>
                {cap?.note && <p className="muted small">{cap.note}</p>}
                <div className="path-label observed-title">
                  OBSERVED CALLS IN THIS PHASE
                </div>
                {observed.length ? (
                  <div className="observed-list">
                    {observed.map((event) => (
                      <div key={event.id}>
                        <span>{event.caller}</span>
                        <Icon name="arrow" size={13} />
                        <strong>
                          {event.service} · {event.operation}
                        </strong>
                        <code>{event.resource.split("/").pop()}</code>
                        <span
                          className={
                            event.status >= 500 ? "http-error" : "http-ok"
                          }
                        >
                          {event.status}
                          {event.injected ? " · injected" : ""}
                        </span>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="muted small">
                    No matching requests observed. Internal managed-service
                    transitions are not fully traced.
                  </p>
                )}
              </div>
            </section>
            {run && (
              <section className="panel timeline">
                <div className="panel-heading">
                  <h2>Experiment timeline</h2>
                  <span className="muted small">{run.id.slice(0, 8)}</span>
                </div>
                <ol>
                  {run.actions.map((action, index) => (
                    <li key={index}>
                      <time>{time(action.at)}</time>
                      <i />
                      <span>{action.label}</span>
                    </li>
                  ))}
                </ol>
              </section>
            )}
          </>
        ) : (
          <section className="panel activity">
            <div className="panel-heading">
              <div>
                <h2>Request activity</h2>
                <p>
                  Latest 300 requests for this run. Payloads and credentials are
                  not recorded.
                </p>
              </div>
              <span className="tag">OBSERVED</span>
            </div>
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    {[
                      "TIME",
                      "CALLER",
                      "SERVICE / OPERATION",
                      "PHASE",
                      "HTTP",
                      "LATENCY",
                    ].map((label) => (
                      <th key={label}>{label}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {data?.events.map((event) => (
                    <tr key={event.id}>
                      <td>{time(event.at)}</td>
                      <td>{event.caller}</td>
                      <td>
                        <strong>{event.service}</strong>
                        <small>{event.operation}</small>
                      </td>
                      <td>{event.phase}</td>
                      <td className={event.status >= 500 ? "http-error" : ""}>
                        {event.status}
                        {event.injected ? " · injected" : ""}
                      </td>
                      <td>{event.latency_ms} ms</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {!data?.events.length && (
              <p className="empty-note">
                No requests observed yet. Open the Quiz app or run a baseline.
              </p>
            )}
          </section>
        )}
        <footer>
          <span>
            <i className="green-dot" />
            {error ? "Results may be stale" : "Local experiment workspace"}
          </span>
          <span>
            Source-defined paths + observed calls. Provider internals are
            outside this view.
          </span>
          <span>Pitwall</span>
        </footer>
      </main>
      {about && <About close={() => setAbout(false)} />}
    </div>
  );
}
function Metric({
  label,
  value,
  detail,
  color,
}: {
  label: string;
  value: string;
  detail: string;
  color: string;
}) {
  return (
    <div className="metric">
      <span>
        {label}
        <i className={color + "-dot"} />
      </span>
      <strong>{value}</strong>
      <small>{detail}</small>
    </div>
  );
}
createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
