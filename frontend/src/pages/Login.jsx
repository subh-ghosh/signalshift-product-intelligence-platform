import { useNavigate } from "react-router-dom"
import { useState } from "react"
import AppShell from "../components/AppShell"

const accessNotes = [
  "Private workspace with review ingestion and export controls.",
  "Built for operator briefings, incident response, and product trend reviews.",
  "Demo account remains unchanged for this prototype.",
]

export default function Login() {
  const navigate = useNavigate()
  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [error, setError] = useState("")

  const handleLogin = () => {
    const validEmail = "netflix_admin@signalshift.com"
    const validPassword = "admin123"

    if (email === validEmail && password === validPassword) {
      localStorage.setItem("token", "demo-user")
      navigate("/dashboard")
    } else {
      setError("Invalid credentials. Please contact IT.")
    }
  }

  return (
    <AppShell activePath="/login" title="SignalShift" subtitle="Secure Operator Access" searchPlaceholder="Search help articles or workspace docs...">
      <section className="route-frame hero-grid">
        <div className="hero-card">
          <div className="hero-card__content">
            <div className="eyebrow">Manager Access</div>
            <h1 className="hero-title">Sign in to the redesigned operations workspace.</h1>
            <p className="hero-copy">
              Use the private operator account to access the rebuilt dashboard, export controls, and live issue evidence from the current analysis run.
            </p>

            <div className="hero-metrics">
              <div className="hero-mini-card">
                <span>Demo Email</span>
                <strong style={{ fontSize: "0.98rem" }}>netflix_admin@signalshift.com</strong>
                <span>Manager account</span>
              </div>
              <div className="hero-mini-card">
                <span>Security Key</span>
                <strong>admin123</strong>
                <span>Prototype credential</span>
              </div>
              <div className="hero-mini-card">
                <span>Post-login</span>
                <strong>Dashboard</strong>
                <span>Insights workspace</span>
              </div>
            </div>
          </div>
        </div>

        <div className="utility-stack">
          <div className="utility-card">
            <div className="utility-card__title">
              <div>
                <h3>Authorize Session</h3>
                <div className="section-kicker">Access card aligned with the new product shell.</div>
              </div>
              <span className="tag tag--success">Private</span>
            </div>

            <div className="login-form">
              <input
                type="text"
                placeholder="Admin Email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
              />
              <input
                type="password"
                placeholder="Security Key"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />

              <div className="login-form__hint">Demo access is unchanged for this prototype.</div>

              <div className="button-row" style={{ marginTop: 6 }}>
                <button className="btn-primary" onClick={handleLogin}>
                  Authorize Session
                </button>
                <button className="btn-secondary" onClick={() => navigate("/")}>
                  Back Home
                </button>
              </div>
            </div>

            {error && (
              <p
                className="status-text is-error"
                style={{
                  marginTop: 18,
                  padding: "12px 14px",
                  borderRadius: 16,
                  background: "rgba(234, 90, 106, 0.08)",
                  border: "1px solid rgba(234, 90, 106, 0.14)",
                }}
              >
                {error}
              </p>
            )}
          </div>

          <div className="utility-card">
            <div className="utility-card__title">
              <div>
                <h3>Access Notes</h3>
                <div className="section-kicker">What remains available in the new interface.</div>
              </div>
            </div>
            <div className="info-list">
              {accessNotes.map((item) => (
                <div key={item} className="info-list__item">
                  <div>
                    <strong>{item}</strong>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>
    </AppShell>
  )
}
