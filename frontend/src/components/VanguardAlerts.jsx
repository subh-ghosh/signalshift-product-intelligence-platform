import { useState, useEffect } from "react"
import api from "../services/api"

export default function VanguardAlerts({ range }) {
  const [alerts, setAlerts] = useState([])
  const [loading, setLoading] = useState(true)

  const fetchAlerts = async () => {
    setLoading(true)
    try {
      const limitMonths = range === "3M" ? 3 : range === "6M" ? 6 : range === "12M" ? 12 : 0
      const res = await api.get("/dashboard/intelligence-alerts", { params: { limit_months: limitMonths } })
      setAlerts(res.data.alerts || [])
    } catch (error) {
      console.error("Signal Center Error:", error)
      setAlerts([])
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchAlerts()
    const interval = setInterval(fetchAlerts, 60000)
    return () => clearInterval(interval)
  }, [range])

  if (loading && alerts.length === 0) {
    return <p className="muted">Pulling the latest alert narrative...</p>
  }

  if (alerts.length === 0) {
    return <p className="muted">No elevated anomalies in this window. Monitoring remains active.</p>
  }

  return (
    <div className="mini-list">
      {alerts.map((alert) => {
        const tone = alert.severity === "CRITICAL" ? "is-critical" : alert.severity === "HIGH" ? "is-warning" : ""

        return (
          <article key={alert.id} className="mini-item">
            <div className="mini-item__icon">{alert.is_anomaly ? "!" : "•"}</div>
            <div style={{ width: "100%" }}>
              <div style={{ display: "flex", justifyContent: "space-between", gap: 12, flexWrap: "wrap" }}>
                <p className="mini-item__title">{alert.category}</p>
                <span className={`status-badge ${tone}`}>{alert.severity}</span>
              </div>

              <p className="mini-item__description">
                {(alert.message || "")
                  .replace(/Statistically out-of-control \(Limit: [\d.]+\)/g, "Unusually high number of mentions")
                  .replace(/MoM spike of \+([\d.]+)%/g, (match, value) => `Increased by ${Math.round(parseFloat(value))}% since last month`)
                  .replace(/Dominant Volume: Accounting for ([\d.]+)% of all feedback\./g, (match, value) => `Top topic: accounts for ${Math.round(parseFloat(value))}% of all reviews.`)}
              </p>

              {alert.link ? (
                <div className="auth-note" style={{ marginTop: 12 }}>
                  Related issue: <strong>{alert.link.linked_to}</strong> ({Math.floor((alert.link.score || 0) * 100)}% connection)
                </div>
              ) : null}
            </div>
          </article>
        )
      })}
    </div>
  )
}
