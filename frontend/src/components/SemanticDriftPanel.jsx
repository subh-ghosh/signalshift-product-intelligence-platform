import { useEffect, useState } from "react"
import api from "../services/api"
import { SkeletonCard } from "./Skeleton"

function getDriftState(score) {
  if (score > 0.18) return { label: "New issue likely", tone: "critical", helper: "Complaint language is shifting fast enough to suggest a new problem inside this category." }
  if (score > 0.14) return { label: "Meaning is shifting", tone: "active", helper: "Customers are describing this category differently than before." }
  return { label: "Watch wording", tone: "watch", helper: "The category is evolving, but the shift is still moderate." }
}

export default function SemanticDriftPanel({ limitMonths = 0, onCategoryClick }) {
  const [data, setData] = useState([])
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    let ignore = false
    api.get("/dashboard/semantic-drift", { params: { limit_months: limitMonths } })
      .then((res) => {
        if (!ignore) {
          setData(res.data || [])
          setLoading(false)
        }
      })
      .catch(() => {
        if (!ignore) {
          setData([])
          setLoading(false)
        }
      })

    return () => {
      ignore = true
    }
  }, [limitMonths])

  if (loading) return <SkeletonCard lines={5} />

  if (!data.length) {
    return (
      <div className="insight-list-empty">
        <p>Complaint language is stable right now, so no hidden issue shifts are standing out.</p>
      </div>
    )
  }

  return (
    <div className="insight-list insight-list--drift">
      {data.map((row, index) => {
        const state = getDriftState(row.avg_drift)
        const intensity = Math.min(Math.round(row.avg_drift * 420), 100)
        return (
          <button
            key={`${row.category}-${index}`}
            type="button"
            className={`insight-list__item insight-list__item--${state.tone} insight-list__item--button`.trim()}
            onClick={() => onCategoryClick?.(row)}
          >
            <div className="insight-list__header">
              <div className="insight-list__rank">{String(index + 1).padStart(2, "0")}</div>
              <div className="insight-list__body">
                <div className="insight-list__topline">
                  <span className={`insight-list__state insight-list__state--${state.tone}`}>{state.label}</span>
                  <span className="insight-list__volume">{row.n_months} months sampled</span>
                </div>
                <h3>{row.category}</h3>
                <p className="insight-list__summary">{state.helper}</p>
                {row.shifting_terms && row.shifting_terms !== "stable" && (
                  <div className="insight-list__meta">Now showing up as: {row.shifting_terms}</div>
                )}
                <div className="insight-list__bar-shell">
                  <div className="insight-list__bar">
                    <div className={`insight-list__bar-fill insight-list__bar-fill--${state.tone}`} style={{ width: `${intensity}%` }} />
                  </div>
                  <span className="insight-list__bar-label">Shift strength {row.avg_drift.toFixed(2)}</span>
                </div>
              </div>
              <div className="insight-list__chevron">Open evidence</div>
            </div>
          </button>
        )
      })}
    </div>
  )
}
