import { Link } from "react-router-dom"

const navItems = [
  { label: "Overview", to: "/dashboard" },
  { label: "Signals", to: "/dashboard" },
  { label: "Analysis", to: "/dashboard" },
  { label: "Workspace", to: "/dashboard" },
]

export default function AppShell({ children }) {
  return (
    <div className="app-shell app-shell--dashboard">
      <div className="app-shell__frame">
        <header className="app-header">
          <Link to="/" className="app-brand" aria-label="SignalShift home">
            <span className="app-brand__mark">S</span>
            <span className="app-brand__text">
              <span className="app-brand__name">SignalShift</span>
              <span className="app-brand__meta">Insight Workspace</span>
            </span>
          </Link>

          <nav className="app-nav" aria-label="Primary">
            {navItems.map((item, index) => (
              <Link
                key={item.label}
                className={`app-nav__item${index === 0 ? " is-active" : ""}`}
                to={item.to}
              >
                {item.label}
              </Link>
            ))}
          </nav>

          <div className="app-header__tools">
            <label className="app-search" aria-label="Search">
              <span aria-hidden="true">⌕</span>
              <input
                type="text"
                readOnly
                value=""
                placeholder="Search insight streams, issues, and reports"
              />
            </label>
            <button className="app-icon-button" type="button" aria-label="Notifications">
              ⊙
            </button>
            <button className="app-icon-button" type="button" aria-label="Settings">
              ◌
            </button>
            <div className="app-avatar" aria-label="Current user">
              SS
            </div>
          </div>
        </header>

        <main className="app-content">{children}</main>
      </div>
    </div>
  )
}
