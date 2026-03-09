import { useEffect, useState } from "react"
import api from "../services/api"
import { SkeletonCard } from "./Skeleton"

// Clean Light Theme Progress Bar
function DriftBar({ score }) {
    const pct = Math.min(score * 500, 100)  // 0.20 drift → 100%
    // Flat, professional colors: Red for Rapid, Amber for Drifting, Blue for Evolving
    const color = score > 0.18 ? "#EF4444" : score > 0.14 ? "#F59E0B" : "#3B82F6"
    return (
        <div style={{ flex: 1, height: "8px", background: "#E2E8F0", borderRadius: "4px", overflow: "hidden" }}>
            <div style={{
                width: `${pct}%`, height: "100%", background: color,
                borderRadius: "4px", transition: "width 0.6s ease"
                // Note: Neon glow removed for the clean light theme
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
        <div style={{ padding: "20px 0" }}>
            <p style={{ color: "#64748B", fontSize: "14px", lineHeight: "1.6", fontWeight: "500" }}>
                No major changes in how customers are describing their issues lately. Language patterns are stable.
            </p>
        </div>
    )

    return (
        <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
            <p title="Measures how the words users use to describe this topic are changing over time" style={{ fontSize: "13px", color: "#64748B", margin: "0 0 8px", lineHeight: "1.6" }}>
                The <strong style={{ color: "#F59E0B", fontWeight: 700 }}>reason for complaints</strong> is changing here. 
                Even if total volume is steady, these are signs of <strong style={{ color: "#EF4444", fontWeight: 700 }}>new bugs or frustrations</strong> replacing old ones.
            </p>

            {data.map((row, i) => {
                const driftColor = row.avg_drift > 0.18 ? "#EF4444" : row.avg_drift > 0.14 ? "#F59E0B" : "#3B82F6"
                const label = row.avg_drift > 0.18 ? "NEW PROBLEM EMERGING" : row.avg_drift > 0.14 ? "REPORT PATTERNS SHIFTING" : "REASONING IS CONSISTENT"

                return (
                    <div key={i} style={{
                        display: "flex",
                        alignItems: "center",
                        gap: "16px",
                        background: "#FFFFFF",
                        borderRadius: "12px",
                        padding: "16px 20px",
                        border: "1px solid #E2E8F0",
                        transition: "all 0.2s ease",
                        cursor: "default",
                        boxShadow: "0 2px 4px rgba(0,0,0,0.02)"
                    }}
                        onMouseEnter={(e) => {
                            e.currentTarget.style.background = "#F8FAFC";
                        }}
                        onMouseLeave={(e) => {
                            e.currentTarget.style.background = "#FFFFFF";
                        }}
                    >
                        <div style={{ width: "220px", flexShrink: 0 }}>
                            <div style={{ fontSize: "14px", fontWeight: 700, color: "#0F172A", letterSpacing: "0.02em" }}>
                                {row.category}
                            </div>
                            <div style={{ fontSize: "11px", color: "#64748B", marginTop: "6px", display: "flex", flexDirection: "column", gap: "4px" }}>
                                <span>{row.n_months} months sampled</span>
                                {row.shifting_terms && row.shifting_terms !== "stable" && (
                                    <span style={{ color: "#334155", fontSize: "12px", lineHeight: "1.4" }}>
                                        <span style={{ color: "#F59E0B", fontWeight: 700 }}>✨ What they're saying now:</span> {row.shifting_terms}
                                    </span>
                                )}
                            </div>
                        </div>

                        <DriftBar score={row.avg_drift} />

                        <div style={{ width: "90px", textAlign: "right", flexShrink: 0 }}>
                            <div style={{
                                fontSize: "10px", fontWeight: 800,
                                color: driftColor, marginTop: "4px",
                                letterSpacing: "0.5px"
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