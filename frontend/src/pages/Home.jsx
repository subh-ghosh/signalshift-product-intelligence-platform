import { useNavigate } from "react-router-dom"

const previewHeights = ["42%", "66%", "88%", "70%", "84%", "62%", "44%"]

export default function Home() {
  const navigate = useNavigate()

  return (
    <div className="home-shell">
      <section className="hero-surface">
        <div className="home-layout">
          <div className="page-grid">
            <div className="panel panel--muted">
              <div className="panel__eyebrow">Customer Intelligence Platform</div>
              <h1 className="hero-lead">Turn feedback noise into product direction.</h1>
              <p className="hero-copy">
                SignalShift surfaces sentiment shifts, emerging complaints, and executive-ready
                narratives in one premium workspace. The experience is now built to feel like a
                modern analytics product from first click to final report.
              </p>
              <div className="cta-row">
                <button className="btn-primary" onClick={() => navigate("/login")}>
                  Open Workspace
                </button>
                <button className="btn-secondary" onClick={() => navigate("/dashboard")}>
                  Jump to Dashboard
                </button>
              </div>
            </div>

            <div className="surface-grid surface-grid--2">
              <div className="panel panel--tight">
                <div className="status-badge is-positive">Live sentiment tracking</div>
                <p className="panel__text" style={{ marginTop: 14 }}>
                  Continuous analysis, rapid alerting, and clean executive summaries for product
                  and CX teams.
                </p>
              </div>
              <div className="panel panel--tight">
                <div className="status-badge is-warning">Retention intelligence</div>
                <p className="panel__text" style={{ marginTop: 14 }}>
                  Spot the issues customers feel first, then export structured evidence and
                  explainable reporting.
                </p>
              </div>
            </div>
          </div>

          <div className="panel dashboard-preview">
            <div className="panel__header">
              <div>
                <div className="panel__eyebrow">Preview</div>
                <h2 className="panel__title panel__title--section">Income-style insight canvas</h2>
                <p className="panel__text">
                  A softer dashboard shell, elevated cards, and a clearer story around momentum,
                  critical signals, and review evidence.
                </p>
              </div>
              <div className="status-badge">Workspace v3</div>
            </div>

            <div className="feature-card feature-card--highlight">
              <div className="surface-grid surface-grid--2" style={{ alignItems: "end" }}>
                <div>
                  <div className="panel__eyebrow">Momentum</div>
                  <div className="panel__title panel__title--section">+24%</div>
                  <p className="panel__text">Positive sentiment is tracking above the trailing quarter.</p>
                </div>
                <div className="feature-card__cta">
                  <span className="muted">Weekly product pulse</span>
                  <strong className="mono">$2.6k</strong>
                </div>
              </div>

              <div className="preview-bars">
                {previewHeights.map((height, index) => (
                  <span key={index} style={{ height }} />
                ))}
              </div>
            </div>
          </div>
        </div>
      </section>
    </div>
  )
}
