import { useEffect, useState } from "react"
import api from "../services/api"
import { SkeletonKpiBar } from "./Skeleton"

function DeltaText({ delta, isPercent = true }) {
  if (delta === null || delta === undefined) return null
  const up = delta > 0
  return (
    <span className={`metric-delta ${up ? "is-up" : "is-down"}`}>
      <span>{up ? "↑" : "↓"}</span>
      <span>
        {Math.abs(isPercent ? Math.round(delta) : delta)}
        {isPercent ? "%" : ""}
      </span>
    </span>
  )
}

function KpiCard({ label, value, sub, icon, delta, deltaIsPercent = true, tooltip }) {
  return (
    <article className="metric-card kpi-card" title={tooltip}>
      <div className="metric-card__top">
        <div className="metric-card__label">{label}</div>
        <div className="metric-card__icon">{icon}</div>
      </div>
      <div className="metric-card__value mono">{value ?? "—"}</div>
      <div className="metric-card__footer">
        <DeltaText delta={delta} isPercent={deltaIsPercent} />
        {sub ? <span className="muted">{sub}</span> : null}
      </div>
    </article>
  )
}

export default function KpiBar({ limitMonths = 0 }) {
  const [kpis, setKpis] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    setLoading(true)
    api
      .get("/dashboard/kpis", { params: { limit_months: limitMonths } })
      .then((res) => setKpis(res.data))
      .catch(() => setKpis(null))
      .finally(() => setLoading(false))
  }, [limitMonths])

  if (loading) return <SkeletonKpiBar />
  if (!kpis) return null

  const deltas = kpis.deltas || {}

  return (
    <div className="surface-grid surface-grid--auto">
      <KpiCard
        icon="◔"
        label="Total Feedback"
        value={kpis.total_reviews.toLocaleString()}
        sub={kpis.window}
        delta={deltas.reviews}
        tooltip="Total volume of customer feedback reviewed."
      />
      <KpiCard
        icon="★"
        label="Average Rating"
        value={kpis.avg_rating ? `${kpis.avg_rating}/5.0` : "N/A"}
        delta={deltas.rating}
        deltaIsPercent={false}
        tooltip="Average star rating across all reviews."
      />
      <KpiCard
        icon="◡"
        label="Customer Happiness"
        value={`${kpis.positive_pct}%`}
        delta={deltas.positive_pct}
        deltaIsPercent={false}
        tooltip="Percentage of reviews expressing positive tone."
      />
      <KpiCard
        icon="△"
        label="Issues Found"
        value={kpis.active_issues}
        delta={deltas.active_issues}
        deltaIsPercent={false}
        tooltip="Number of distinct problem areas currently identified."
      />
    </div>
  )
}
