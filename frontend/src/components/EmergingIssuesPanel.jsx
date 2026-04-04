import { useEffect, useState } from "react"
import api from "../services/api"
import { SkeletonCard } from "./Skeleton"

function getSignalState(volume, momentum) {
  if (volume >= 150 || momentum >= 75) return { label: "Critical", tone: "critical" }
  if (volume >= 80 || momentum >= 30) return { label: "Active", tone: "active" }
  return { label: "Watch", tone: "watch" }
}

export default function EmergingIssuesPanel({ limitMonths = 0 }) {
  const [clusters, setClusters] = useState([])
  const [loading, setLoading] = useState(false)
  const [expanded, setExpanded] = useState(null)

  useEffect(() => {
    let ignore = false
    api.get("/dashboard/emerging-issues", { params: { limit_months: limitMonths } })
      .then((res) => {
        if (!ignore) {
          setClusters(res.data || [])
          setLoading(false)
        }
      })
      .catch(() => {
        if (!ignore) {
          setClusters([])
          setLoading(false)
        }
      })

    return () => {
      ignore = true
    }
  }, [limitMonths])

  if (loading) return <SkeletonCard lines={5} />

  if (!clusters.length) {
    return (
      <div className="insight-list-empty">
        <p>No newly surfacing complaint clusters were strong enough to flag in this window.</p>
      </div>
    )
  }

  return (
    <div className="insight-list">
      {clusters.map((cluster, index) => {
        const isOpen = expanded === index
        const state = getSignalState(cluster.estimated_volume, cluster.momentum_pct)
        const preview = cluster.sample_reviews?.[0] || "No representative evidence snippet was available."

        return (
          <article
            key={cluster.cluster_id ?? index}
            className={`insight-list__item insight-list__item--${state.tone} ${isOpen ? "is-open" : ""}`.trim()}
          >
            <button
              type="button"
              className="insight-list__trigger"
              onClick={() => setExpanded(isOpen ? null : index)}
            >
              <div className="insight-list__header">
                <div className="insight-list__rank">{String(index + 1).padStart(2, "0")}</div>
                <div className="insight-list__body">
                  <div className="insight-list__topline">
                    <span className={`insight-list__state insight-list__state--${state.tone}`}>{state.label}</span>
                    <span className="insight-list__volume">{cluster.estimated_volume.toLocaleString()} reviews</span>
                    {cluster.momentum_pct > 0 && (
                      <span className="insight-list__momentum">Rising {Math.round(cluster.momentum_pct)}%</span>
                    )}
                  </div>
                  <h3>{String(cluster.label).replace(/\s*\(Proto\)/gi, "")}</h3>
                  <p className="insight-list__summary">
                    {cluster.keywords
                      ? `New complaints are clustering around ${cluster.keywords}.`
                      : "A new complaint cluster is gaining enough volume to watch closely."}
                  </p>
                  {cluster.keywords && (
                    <div className="insight-list__meta">Signals: {cluster.keywords}</div>
                  )}
                </div>
                <div className="insight-list__chevron">{isOpen ? "Hide evidence" : "View evidence"}</div>
              </div>
            </button>

            <div className="insight-list__preview">
              <span>Preview:</span> {preview}
            </div>

            {isOpen && (
              <div className="insight-list__evidence">
                <div className="insight-list__evidence-title">What customers are saying</div>
                {cluster.sample_reviews?.map((review, reviewIndex) => (
                  <blockquote key={`${cluster.cluster_id ?? index}-${reviewIndex}`} className="insight-list__quote">
                    "{review}..."
                  </blockquote>
                ))}
              </div>
            )}
          </article>
        )
      })}
    </div>
  )
}
