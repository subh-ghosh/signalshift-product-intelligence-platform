import { useNavigate } from "react-router-dom"
import { useState } from "react"

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
    <div className="auth-shell">
      <section className="hero-surface">
        <div className="auth-layout">
          <aside className="auth-showcase">
            <div className="page-grid">
              <div className="app-brand">
                <span className="app-brand__mark">S</span>
                <span className="app-brand__text">
                  <span className="app-brand__name">SignalShift</span>
                  <span className="app-brand__meta">Private Workspace</span>
                </span>
              </div>

              <div>
                <div className="panel__eyebrow">Manager access</div>
                <h1 className="page-title" style={{ maxWidth: "11ch" }}>
                  Enter the insight room.
                </h1>
                <p className="hero-copy">
                  Authenticate into the premium monitoring workspace for live sentiment tracking,
                  issue diagnostics, and export-ready reporting.
                </p>
              </div>

              <div className="surface-grid surface-grid--2">
                <div className="panel panel--tight">
                  <div className="status-badge is-positive">Live alerts</div>
                  <p className="panel__text" style={{ marginTop: 12 }}>
                    Watch customer risk signals refresh in a calmer, cleaner product shell.
                  </p>
                </div>
                <div className="panel panel--tight">
                  <div className="status-badge">Reports</div>
                  <p className="panel__text" style={{ marginTop: 12 }}>
                    Export structured CSV and executive PDF briefs without leaving the dashboard.
                  </p>
                </div>
              </div>
            </div>

            <div className="panel panel--muted">
              <div className="panel__eyebrow">Demo credentials</div>
              <div className="surface-grid surface-grid--2">
                <div>
                  <div className="muted" style={{ fontSize: "0.8rem", fontWeight: 700 }}>
                    Email
                  </div>
                  <strong>netflix_admin@signalshift.com</strong>
                </div>
                <div>
                  <div className="muted" style={{ fontSize: "0.8rem", fontWeight: 700 }}>
                    Security key
                  </div>
                  <strong>admin123</strong>
                </div>
              </div>
            </div>
          </aside>

          <div className="auth-panel">
            <div>
              <div className="panel__eyebrow">Authorized sign in</div>
              <h2 className="panel__title panel__title--section">Workspace session</h2>
              <p className="panel__text">
                Use the current demo account to continue into the redesigned analytics suite.
              </p>
            </div>

            <div className="field-stack">
              <label className="field-label">
                Admin email
                <span className="input-shell">
                  <span aria-hidden="true">@</span>
                  <input
                    type="text"
                    placeholder="name@company.com"
                    value={email}
                    onChange={(event) => setEmail(event.target.value)}
                  />
                </span>
              </label>

              <label className="field-label">
                Security key
                <span className="input-shell">
                  <span aria-hidden="true">•</span>
                  <input
                    type="password"
                    placeholder="Enter your password"
                    value={password}
                    onChange={(event) => setPassword(event.target.value)}
                  />
                </span>
              </label>
            </div>

            <button className="btn-primary" onClick={handleLogin}>
              Authorize session
            </button>

            <div className="auth-note">
              Access is scoped to the current research workspace and preserves the existing demo
              authentication flow.
            </div>

            {error ? <div className="auth-note error-note">{error}</div> : null}
          </div>
        </div>
      </section>
    </div>
  )
}
