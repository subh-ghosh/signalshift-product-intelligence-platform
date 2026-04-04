import { useEffect, useState } from "react"
import api from "../services/api"
import { SkeletonChart } from "./Skeleton"

function getSeverityMeta(severity) {
  if (severity >= 4.0) return { label: "Critical", color: "#ea5b57", bg: "rgba(234, 91, 87, 0.12)" }
  if (severity >= 3.0) return { label: "High", color: "#eca74c", bg: "rgba(236, 167, 76, 0.14)" }
  if (severity >= 2.5) return { label: "Medium", color: "#4b78b4", bg: "rgba(75, 120, 180, 0.12)" }
  return { label: "Low", color: "#31b57e", bg: "rgba(49, 181, 126, 0.12)" }
}

function getVelocityMeta(direction, label) {
  if (direction === "up") return { label: `Rising ${label || ""}`.trim(), color: "#ea5b57", bg: "rgba(234, 91, 87, 0.12)" }
  if (direction === "down") return { label: `Falling ${label || ""}`.trim(), color: "#31b57e", bg: "rgba(49, 181, 126, 0.12)" }
  if (direction === "new") return { label: "New", color: "#4b78b4", bg: "rgba(75, 120, 180, 0.12)" }
  return { label: "Stable", color: "#72788c", bg: "rgba(114, 120, 140, 0.12)" }
}

function formatPrimaryValue(issue, useImpact) {
  if (useImpact && issue.revenue_risk !== null && issue.revenue_risk !== undefined) {
    return `$${issue.revenue_risk.toFixed(2)}`
  }

  if (useImpact) {
    return `${Number(issue.sort_metric || 0).toFixed(1)}`
  }

  return issue.mentions.toLocaleString()
}

export default function TopIssuesChart({ onIssueClick, limitMonths = 0 }) {
  const [data, setData] = useState([])
  const [loading, setLoading] = useState(true)
  const [sortByRevenue, setSortByRevenue] = useState(true)

  useEffect(() => {
    const fetchIssues = async () => {
      setLoading(true)
      try {
        const res = await api.get("/dashboard/top-issues", { params: { limit_months: limitMonths } })
        const filtered = (res.data || []).filter((item) => item.issue !== "General App Feedback")
        setData(filtered)
      } catch (err) {
        console.error("Failed to load issues", err)
        setData([])
      } finally {
        setLoading(false)
      }
    }

    fetchIssues()
  }, [limitMonths])

  if (loading) {
    return <SkeletonChart height={420} />
  }

  const canRankByRevenue = data.some((item) => item.revenue_risk !== null && item.revenue_risk !== undefined)
  const useImpact = sortByRevenue && canRankByRevenue

  const sortedData = [...data].sort((a, b) => {
    if (useImpact) {
      return (b.revenue_risk || 0) - (a.revenue_risk || 0)
    }

    if (sortByRevenue) {
      return (b.sort_metric || 0) - (a.sort_metric || 0)
    }

    return b.mentions - a.mentions
  })

  const activeKey = useImpact ? "revenue_risk" : sortByRevenue ? "sort_metric" : "mentions"
  const maxValue = Math.max(...sortedData.map((item) => Number(item[activeKey]) || 0), 1)
  const visibleData = sortedData
    .filter((item) => (Number(item[activeKey]) || 0) >= maxValue * 0.02)
    .slice(0, 10)

  if (!visibleData.length) {
    return <p style={{ color: "#72788c", padding: "20px 0", fontWeight: 500 }}>No specific high-signal issues detected in this window.</p>
  }

  return (
    <div className="complaints-list">
      <div className="complaints-list__topbar">
        <div>
          <div className="complaints-list__hint">
            Click any issue row to inspect supporting review evidence.
          </div>
        </div>

        <div className="complaints-toggle" role="tablist" aria-label="Complaints ranking mode">
          <button
            className={`complaints-toggle__button ${sortByRevenue ? "is-active" : ""}`.trim()}
            title="Rank issues by business impact"
            onClick={() => setSortByRevenue(true)}
          >
            Impact
          </button>
          <button
            className={`complaints-toggle__button ${!sortByRevenue ? "is-active" : ""}`.trim()}
            title="Rank issues by complaint volume"
            onClick={() => setSortByRevenue(false)}
          >
            Volume
          </button>
        </div>
      </div>

      <div className="complaints-list__helper">
        {sortByRevenue
          ? (useImpact ? "Sorted by estimated business impact." : "Sorted by issue intensity because revenue impact is unavailable in this view.")
          : "Sorted by total complaints in the selected time window."}
      </div>

      <div className="complaints-list__rows">
        {visibleData.map((issue, index) => {
          const severity = getSeverityMeta(issue.avg_severity || 0)
          const velocity = getVelocityMeta(issue.velocity_dir, issue.velocity_label)
          const barWidth = `${Math.max(12, Math.round(((Number(issue[activeKey]) || 0) / maxValue) * 100))}%`

          return (
            <button
              key={`${issue.issue}-${index}`}
              type="button"
              className="complaints-row"
              onClick={() => onIssueClick && onIssueClick(issue.issue)}
            >
              <div className="complaints-row__rank">{String(index + 1).padStart(2, "0")}</div>

              <div className="complaints-row__body">
                <div className="complaints-row__header">
                  <div className="complaints-row__titleblock">
                    <div className="complaints-row__title">{issue.issue}</div>
                    <div className="complaints-row__meta">
                      <span className="complaints-chip" style={{ color: severity.color, background: severity.bg }}>
                        {severity.label}
                      </span>
                      <span className="complaints-chip" style={{ color: velocity.color, background: velocity.bg }}>
                        {velocity.label}
                      </span>
                    </div>
                  </div>

                  <div className="complaints-row__metrics">
                    <div className="complaints-row__metric">
                      <span>{sortByRevenue ? "Primary metric" : "Complaints"}</span>
                      <strong>{formatPrimaryValue(issue, useImpact)}</strong>
                    </div>
                    <div className="complaints-row__metric">
                      <span>Complaint count</span>
                      <strong>{issue.mentions.toLocaleString()}</strong>
                    </div>
                    <div className="complaints-row__cta">View evidence</div>
                  </div>
                </div>

                <div className="complaints-row__rail">
                  <div className="complaints-row__fill" style={{ width: barWidth, background: severity.color }} />
                </div>
              </div>
            </button>
          )
        })}
      </div>
    </div>
  )
}
