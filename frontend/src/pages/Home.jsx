import { useNavigate } from "react-router-dom"
import AppShell from "../components/AppShell"

const previewCards = [
  { label: "Live Signals", value: "13", note: "active priorities" },
  { label: "Customer Mood", value: "44.7%", note: "positive sentiment" },
  { label: "Exec Exports", value: "PDF + CSV", note: "ready for leadership" },
]

const highlights = [
  { title: "Executive summaries", copy: "AI-generated briefings that translate noisy review streams into an actionable narrative." },
  { title: "Critical issue tracking", copy: "Trend lines, anomaly alerts, and drill-down evidence across product areas." },
  { title: "Operational controls", copy: "Keep upload, sync, export, and analysis workflows accessible from the same workspace." },
]

export default function Home() {
  const navigate = useNavigate()

  return (
    <AppShell activePath="/" title="SignalShift" subtitle="Workspace Overview" searchPlaceholder="Search reports, teams, or issues...">
      <section className="route-frame hero-grid">
        <div className="hero-card">
          <div className="hero-card__content">
            <div className="eyebrow">Customer Intelligence Platform</div>
            <h1 className="hero-title">A calmer control room for customer signals.</h1>
            <p className="hero-copy">
              SignalShift turns app review data into an executive-ready workspace with softer navigation, cleaner cards, and faster paths from detection to action.
            </p>

            <div className="button-row" style={{ marginTop: 24 }}>
              <button className="btn-primary" onClick={() => navigate("/login")}>
                Enter Workspace
              </button>
              <button className="btn-secondary" onClick={() => navigate("/dashboard")}>
                View Dashboard Preview
              </button>
            </div>

            <div className="hero-metrics">
              {previewCards.map((card) => (
                <div key={card.label} className="hero-mini-card">
                  <span>{card.label}</span>
                  <strong>{card.value}</strong>
                  <span>{card.note}</span>
                </div>
              ))}
            </div>
          </div>
        </div>

        <div className="utility-stack">
          <div className="utility-card">
            <div className="utility-card__title">
              <div>
                <h3>Workspace Preview</h3>
                <div className="section-kicker">Reference-inspired layout adapted for analytics operations.</div>
              </div>
              <span className="tag tag--warm">New Visual System</span>
            </div>

            <div className="info-list">
              {highlights.map((item) => (
                <div key={item.title} className="info-list__item">
                  <div>
                    <strong>{item.title}</strong>
                    <span>{item.copy}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="utility-card">
            <div className="utility-card__title">
              <div>
                <h3>Why This Refresh</h3>
                <div className="section-kicker">What the redesign changes across the product.</div>
              </div>
              <span className="tag">SignalShift</span>
            </div>
            <div className="info-list">
              <div className="info-list__item">
                <div>
                  <strong>Unified surfaces</strong>
                  <span>Home, login, and dashboard now share the same editorial shell and control language.</span>
                </div>
              </div>
              <div className="info-list__item">
                <div>
                  <strong>Cleaner analytics</strong>
                  <span>Charts, alerts, summaries, and exports are grouped into calmer, easier-to-scan layouts.</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>
    </AppShell>
  )
}
