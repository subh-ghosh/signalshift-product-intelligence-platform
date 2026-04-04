import { useEffect, useState } from "react"
import api from "../services/api"
import { SkeletonKpiBar } from "./Skeleton"

function DeltaText({ delta, isPercent = true }) {
    if (delta === null || delta === undefined) return null
    const up = delta > 0
    const sign = up ? "↑" : "↓"
    const displayDelta = Math.abs(delta)

    return (
        <span title="Growth Rate" className={`kpi-card__delta ${up ? "is-up" : "is-down"}`}>
            <span>{sign}</span> {isPercent ? Math.round(displayDelta) : displayDelta}{isPercent ? "%" : ""}
        </span>
    )
}

function KpiCard({ label, value, sub, icon, delta, deltaIsPercent = true, tooltip }) {
    return (
        <div className="glass-card kpi-card" title={tooltip}>
            <div className="kpi-card__header">
                <span className="kpi-card__marker" aria-hidden="true">{icon}</span>
                <div className="kpi-card__label">{label}</div>
            </div>

            <div className="kpi-card__value">{value ?? "—"}</div>

            <div className="kpi-card__footer">
                {sub && <span className="kpi-card__sub">{sub}</span>}
                <DeltaText delta={delta} isPercent={deltaIsPercent} />
            </div>
        </div>
    )
}

export default function KpiBar({ limitMonths = 0 }) {
    const [kpis, setKpis] = useState(null)
    const [loading, setLoading] = useState(true)

    useEffect(() => {
        api.get("/dashboard/kpis", { params: { limit_months: limitMonths } })
            .then((res) => setKpis(res.data))
            .catch(() => setKpis(null))
            .finally(() => setLoading(false))
    }, [limitMonths])

    if (loading) return <SkeletonKpiBar />
    if (!kpis) return null

    const d = kpis.deltas || {}

    return (
        <div className="stats-grid dashboard-kpi-wrap">
            <KpiCard
                icon="◫"
                label="Total Feedback"
                value={kpis.total_reviews.toLocaleString()}
                sub={kpis.window}
                delta={d.reviews}
                deltaIsPercent={true}
                tooltip="Total volume of customer feedback reviewed."
            />
            <KpiCard
                icon="★"
                label="Avg Rating"
                value={kpis.avg_rating ? `${kpis.avg_rating}/5.0` : "N/A"}
                delta={d.rating}
                deltaIsPercent={false}
                tooltip="Average star rating across all reviews."
            />

        </div>
    )
}
