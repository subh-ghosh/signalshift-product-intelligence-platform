import { Link } from "react-router-dom"

const NAV_ITEMS = [
  { label: "Home", to: "/" },
  { label: "Access", to: "/login" },
  { label: "Insights", to: "/dashboard" },
]

export default function AppShell({
  activePath,
  title = "SignalShift",
  subtitle = "Intelligence Workspace",
  searchPlaceholder = "Search workspace...",
  shellClassName = "",
  children,
}) {
  return (
    <div className="app-page">
      <div className={`app-shell ${shellClassName}`.trim()}>
        <header className="shell-topbar">
          <div className="shell-brand">
            <div className="shell-brand__mark">S</div>
            <div className="shell-brand__meta">
              <span className="shell-brand__title">{title}</span>
              {subtitle ? <span className="shell-brand__subtitle">{subtitle}</span> : null}
            </div>
          </div>

          <nav className="shell-nav" aria-label="Primary">
            {NAV_ITEMS.map((item) => (
              <Link
                key={item.to}
                to={item.to}
                className={`shell-nav__link ${activePath === item.to ? "is-active" : ""}`.trim()}
              >
                {item.label}
              </Link>
            ))}
          </nav>

          <div className="shell-actions">
            <div className="shell-search">
              <input type="text" placeholder={searchPlaceholder} aria-label="Search workspace" />
              <span className="shell-search__icon">⌕</span>
            </div>
            <div className="shell-quick-actions">
              <button className="shell-icon-button" aria-label="Workspace controls">
                ⊙
              </button>
              <button className="shell-icon-button" aria-label="Notifications">
                ◌
              </button>
              <div className="shell-profile">
                <div className="shell-profile__avatar">SS</div>
                <div className="shell-profile__meta">
                  <strong>Ops Lead</strong>
                  <span>SignalShift</span>
                </div>
              </div>
            </div>
          </div>
        </header>

        <main className="shell-body">{children}</main>
      </div>
    </div>
  )
}
