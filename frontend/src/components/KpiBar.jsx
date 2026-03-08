import { useEffect, useState } from "react"
import api from "../services/api"

// Single KPI metric card
function KpiCard({ label, value, sub, color = "#fff", icon }) {
    return (
        <div style={{
            flex: 1,
            minWidth: "140px",
            background: "rgba(255,255,255,0.04)",
            border: "1px solid rgba(255,255,255,0.08)",
            borderRadius: "12px",
            padding: "20px 24px",
            display: "flex",
            flexDirection: "column",
            gap: "6px"
        }}>
            <div style={{ fontSize: "22px" }}>{icon}</div>
            <div style={{ fontSize: "28px", fontWeight: 800, color, letterSpacing: "-0.5px" }}>
                {value ?? "—"}
            </div>
            <div style={{ fontSize: "13px", fontWeight: 600, color: "#ccc" }}>{label}</div>
            {sub && <div style={{ fontSize: "11px", color: "#555" }}>{sub}</div>}
        </div>
    )
}

export default function KpiBar({ limitMonths = 0 }) {
    const [kpis, setKpis] = useState(null)
    const [loading, setLoading] = useState(true)

    useEffect(() => {
        setLoading(true)
        api.get("/dashboard/kpis", { params: { limit_months: limitMonths } })
            .then(res => setKpis(res.data))
            .catch(() => setKpis(null))
            .finally(() => setLoading(false))
    }, [limitMonths])

    if (loading || !kpis) return null

    const sentimentColor = kpis.positive_pct >= 60 ? "#1DB954" : kpis.positive_pct >= 40 ? "#FFB347" : "#E50914"
    const ratingColor = kpis.avg_rating >= 3.5 ? "#1DB954" : kpis.avg_rating >= 2.5 ? "#FFB347" : "#E50914"

    return (
        <div style={{ display: "flex", gap: "16px", flexWrap: "wrap", marginBottom: "32px" }}>
            <KpiCard
                icon="📊"
                label="Total Reviews"
                value={kpis.total_reviews.toLocaleString()}
                sub={kpis.window}
                color="#fff"
            />
            <KpiCard
                icon="⭐"
                label="Avg Rating"
                value={kpis.avg_rating ? `${kpis.avg_rating}/5.0` : "N/A"}
                sub="from review scores"
                color={ratingColor}
            />
            <KpiCard
                icon="😊"
                label="Positive Sentiment"
                value={`${kpis.positive_pct}%`}
                sub={`${(100 - kpis.positive_pct).toFixed(1)}% negative`}
                color={sentimentColor}
            />
            <KpiCard
                icon="🔴"
                label="Active Issue Types"
                value={kpis.active_issues}
                sub="canonical categories"
                color={kpis.active_issues > 8 ? "#E50914" : "#FFB347"}
            />
        </div>
    )
}
