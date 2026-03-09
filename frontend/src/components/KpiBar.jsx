import { useEffect, useState } from "react"
import api from "../services/api"
import { SkeletonKpiBar } from "./Skeleton"

// Clean Light Theme Delta text (Pill style)
function DeltaText({ delta, isPercent = true }) {
    if (delta === null || delta === undefined) return null
    const up = delta > 0
    // Emerald Green for positive, Rose Red for negative
    const color = up ? "#10B981" : "#EF4444"
    const bgColor = up ? "#ECFDF5" : "#FEF2F2"
    const sign = up ? "↑" : "↓"
    const displayDelta = Math.abs(delta)

    return (
        <span title="Growth Rate (Change from previous period)" style={{
            fontSize: "12px",
            fontWeight: 700,
            color: color,
            backgroundColor: bgColor,
            padding: "4px 8px",
            borderRadius: "6px",
            display: "inline-flex",
            alignItems: "center",
            gap: "2px"
        }}>
            <span>{sign}</span> {isPercent ? Math.round(displayDelta) : displayDelta}{isPercent ? "%" : ""}
        </span>
    )
}

// Clean Light Theme KPI Card
function KpiCard({ label, value, sub, icon, delta, deltaIsPercent = true, tooltip }) {
    return (
        <div className="glass-card" title={tooltip} style={{
            display: "flex",
            flexDirection: "column",
            padding: "24px",
            gap: "12px"
        }}>
            {/* Top Row: Label and Icon */}
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <div style={{ fontSize: "14px", fontWeight: 600, color: "#64748B" }}>
                    {label}
                </div>
                <div style={{
                    width: "36px",
                    height: "36px",
                    background: "#EFF6FF", // Soft blue background
                    color: "#3B82F6", // Primary blue
                    borderRadius: "10px",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    fontSize: "18px"
                }}>
                    {icon}
                </div>
            </div>

            {/* Middle Row: Primary Value */}
            <div style={{ fontSize: "32px", fontWeight: 800, color: "#0F172A", lineHeight: "1", marginTop: "4px" }}>
                {value ?? "—"}
            </div>

            {/* Bottom Row: Delta & Subtext */}
            <div style={{ display: "flex", alignItems: "center", gap: "10px", marginTop: "4px" }}>
                <DeltaText delta={delta} isPercent={deltaIsPercent} />
                {sub && <span style={{ fontSize: "12px", color: "#94A3B8", fontWeight: 500 }}>{sub}</span>}
            </div>
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

    if (loading) return <SkeletonKpiBar />
    if (!kpis) return null

    const d = kpis.deltas || {}

    return (
        <div style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))",
            gap: "24px",
            marginBottom: "32px",
            width: "100%"
        }}>
            <KpiCard
                icon="📊"
                label="Total Feedback"
                value={kpis.total_reviews.toLocaleString()}
                sub={kpis.window}
                delta={d.reviews}
                deltaIsPercent={true}
                tooltip="Total volume of customer feedback reviewed."
            />
            <KpiCard
                icon="⭐"
                label="Avg Rating"
                value={kpis.avg_rating ? `${kpis.avg_rating}/5.0` : "N/A"}
                delta={d.rating}
                deltaIsPercent={false}
                tooltip="Average star rating across all reviews."
            />
            <KpiCard
                icon="😊"
                label="Customer Happiness"
                value={`${kpis.positive_pct}%`}
                delta={d.positive_pct}
                deltaIsPercent={false}
                tooltip="Percentage of reviews expressing positive emotional tone."
            />
            <KpiCard
                icon="⚠️"
                label="Total Issues Found"
                value={kpis.active_issues}
                delta={d.active_issues}
                deltaIsPercent={false}
                tooltip="Number of distinct problem areas currently identified."
            />
        </div>
    )
}