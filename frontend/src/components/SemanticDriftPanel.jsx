import { useEffect, useState } from "react"
import api from "../services/api"
import { SkeletonCard } from "./Skeleton"

function DriftBar({ score }) {
    const pct = Math.min(score * 500, 100)  // 0.20 drift → 100%
    const color = score > 0.18 ? "#E50914" : score > 0.14 ? "#FF6B35" : "#FFB347"
    return (
        <div style={{ flex: 1, height: "6px", background: "rgba(255,255,255,0.08)", borderRadius: "3px", overflow: "hidden" }}>
            <div style={{
                width: `${pct}%`, height: "100%", background: color,
                borderRadius: "3px", transition: "width 0.6s ease",
                boxShadow: `0 0 6px ${color}88`
            }} />
        </div>
    )
}

export default function SemanticDriftPanel({ limitMonths = 0 }) {
    const [data, setData] = useState([])
    const [loading, setLoading] = useState(true)

    useEffect(() => {
        setLoading(true)
        api.get("/dashboard/semantic-drift", { params: { limit_months: limitMonths } })
            .then(res => setData(res.data || []))
            .catch(() => setData([]))
            .finally(() => setLoading(false))
    }, [limitMonths])

    if (loading) return <SkeletonCard lines={5} />
    if (!data.length) return (
        <p style={{ color: "#666", fontSize: "13px" }}>
            No significant semantic drift detected in the selected window. Language is stable.
        </p>
    )

    return (
        <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
            <p style={{ fontSize: "13px", color: "#888", margin: "0 0 8px" }}>
                Categories where complaint <strong style={{ color: "#FFB347" }}>language is shifting</strong> month-over-month — 
                indicating evolving user pain points even if volume stays constant.
            </p>

            {data.map((row, i) => {
                const driftColor = row.avg_drift > 0.18 ? "#E50914" : row.avg_drift > 0.14 ? "#FF6B35" : "#FFB347"
                const label = row.avg_drift > 0.18 ? "RAPID SHIFT" : row.avg_drift > 0.14 ? "DRIFTING" : "EVOLVING"

                return (
                    <div key={i} style={{
                        display: "flex",
                        alignItems: "center",
                        gap: "14px",
                        background: "rgba(255,255,255,0.02)",
                        borderRadius: "8px",
                        padding: "12px 16px",
                        border: "1px solid rgba(255,255,255,0.06)"
                    }}>
                        <div style={{ width: "180px", flexShrink: 0 }}>
                            <div style={{ fontSize: "13px", fontWeight: 600, color: "#ddd" }}>{row.category}</div>
                            <div style={{ fontSize: "11px", color: "#555", marginTop: "2px" }}>
                                {row.n_months} months sampled
                            </div>
                        </div>

                        <DriftBar score={row.avg_drift} />

                        <div style={{ width: "90px", textAlign: "right", flexShrink: 0 }}>
                            <div style={{ fontSize: "13px", fontWeight: 700, color: driftColor }}>
                                {(row.avg_drift * 100).toFixed(1)}%
                            </div>
                            <div style={{
                                fontSize: "10px", fontWeight: 800,
                                color: driftColor, marginTop: "2px"
                            }}>
                                {label}
                            </div>
                        </div>
                    </div>
                )
            })}
        </div>
    )
}
