import { useEffect, useState } from "react"
import api from "../services/api"
import { SkeletonCard } from "./Skeleton"

export default function EmergingIssuesPanel({ limitMonths = 0 }) {
    const [clusters, setClusters] = useState([])
    const [loading, setLoading] = useState(true)
    const [expanded, setExpanded] = useState(null)

    useEffect(() => {
        setLoading(true)
        api.get("/dashboard/emerging-issues", { params: { limit_months: limitMonths } })
            .then(res => setClusters(res.data || []))
            .catch(() => setClusters([]))
            .finally(() => setLoading(false))
    }, [limitMonths])

    if (loading) return <SkeletonCard lines={6} />

    if (!clusters.length) return (
        <div style={{ textAlign: "center", padding: "40px 20px" }}>
            <div style={{ fontSize: "28px", marginBottom: "16px", opacity: 0.8 }}>📡</div>
            <p style={{ color: "#64748B", fontSize: "14px", maxWidth: "260px", margin: "0 auto", lineHeight: "1.6" }}>
                Scanning for new topics... No actionable emerging trends detected in this window.
            </p>
        </div>
    )

    return (
        <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
            <p title="Topics that are starting to show up in feedback but don't fit into our regular categories yet" style={{ fontSize: "13px", color: "#64748B", margin: "0 0 8px", lineHeight: "1.6" }}>
                We're finding new patterns in customer feedback that don't fit our usual categories yet. 
                These could be <strong style={{ color: "#F59E0B", fontWeight: 700 }}>new types of issues</strong> or suggestions to watch.
            </p>

            {clusters.map((cluster, i) => {
                const isOpen = expanded === i
                // Clean Light Theme Urgency Scale
                const urgency = cluster.estimated_volume >= 150 ? "CRITICAL" : cluster.estimated_volume >= 80 ? "ACTIVE" : "MONITOR"
                const urgencyColor = urgency === "CRITICAL" ? "#E50914" : urgency === "ACTIVE" ? "#F59E0B" : "#3B82F6"

                return (
                    <div key={i} style={{
                        background: isOpen ? "#F8FAFC" : "#FFFFFF",
                        border: `1px solid ${isOpen ? `${urgencyColor}44` : "#E2E8F0"}`,
                        borderLeft: `4px solid ${urgencyColor}`,
                        borderRadius: "12px",
                        padding: "16px 20px",
                        cursor: "pointer",
                        transition: "all 0.2s ease",
                        boxShadow: isOpen ? `0 4px 12px rgba(0,0,0,0.03)` : "none"
                    }}
                        onClick={() => setExpanded(isOpen ? null : i)}
                        onMouseEnter={(e) => {
                            if (!isOpen) e.currentTarget.style.background = "#F8FAFC"
                        }}
                        onMouseLeave={(e) => {
                            if (!isOpen) e.currentTarget.style.background = "#FFFFFF"
                        }}
                    >
                        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "12px" }}>

                            {/* Left Side: Badge + Label */}
                            <div style={{ display: "flex", alignItems: "center", gap: "14px" }}>
                                <span style={{
                                    fontSize: "10px", fontWeight: 800, padding: "4px 10px",
                                    borderRadius: "6px", background: `${urgencyColor}15`, color: urgencyColor,
                                    letterSpacing: "0.5px"
                                }}>
                                    {urgency}
                                </span>
                                <span style={{ fontWeight: 700, fontSize: "15px", color: "#0F172A", letterSpacing: "0.02em" }}>
                                    {String(cluster.label).replace(/\s*\(Proto\)/gi, '')}
                                </span>
                            </div>

                            {/* Right Side: Meta Data + Badges */}
                            <div style={{ display: "flex", alignItems: "center", gap: "12px", flexWrap: "wrap" }}>
                                <span style={{ fontSize: "12px", color: "#64748B", display: "flex", alignItems: "center", gap: "6px" }}>
                                    <span style={{ fontSize: "11px", opacity: 0.8 }}>🔍</span> {cluster.keywords}
                                </span>

                                <div style={{ width: "1px", height: "14px", background: "#E2E8F0" }} />

                                <span style={{ fontSize: "13px", color: "#334155", fontWeight: 600 }}>
                                    {cluster.estimated_volume.toLocaleString()} reviews
                                </span>

                                {cluster.momentum_pct > 0 && (
                                    <span style={{
                                        fontSize: "10px", fontWeight: 800, padding: "3px 8px",
                                        borderRadius: "6px", background: "#FEF2F2", color: "#DC2626",
                                        border: "1px solid #FECACA"
                                    }}>
                                        RISING ▲ {cluster.momentum_pct}%
                                    </span>
                                )}

                                <span title="A previously unseen topic making an appearance" style={{
                                    fontSize: "10px", fontWeight: 800, background: "#EFF6FF", color: "#2563EB",
                                    padding: "3px 8px", borderRadius: "6px", border: "1px solid #BFDBFE",
                                    letterSpacing: "0.5px"
                                }}>
                                    NEW
                                </span>

                                <span style={{ color: "#94A3B8", fontSize: "10px", marginLeft: "4px" }}>
                                    {isOpen ? "▲" : "▼"}
                                </span>
                            </div>
                        </div>

                        {/* Expanded Content */}
                        {isOpen && (
                            <div style={{ marginTop: "16px", display: "flex", flexDirection: "column", gap: "10px", paddingTop: "16px", borderTop: "1px solid #E2E8F0" }}>
                                <div style={{ fontSize: "11px", fontWeight: 700, color: "#64748B", textTransform: "uppercase", letterSpacing: "0.5px" }}>
                                    What customers are saying
                                </div>
                                {cluster.sample_reviews.map((r, j) => (
                                    <div key={j} style={{
                                        background: "#FFFFFF",
                                        borderRadius: "8px",
                                        padding: "12px 16px",
                                        fontSize: "13px",
                                        color: "#334155",
                                        fontStyle: "italic",
                                        lineHeight: "1.6",
                                        border: "1px solid #E2E8F0",
                                        borderLeft: "2px solid #CBD5E1"
                                    }}>
                                        "{r}..."
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>
                )
            })}
        </div>
    )
}