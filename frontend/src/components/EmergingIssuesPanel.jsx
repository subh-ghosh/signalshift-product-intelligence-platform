import { useEffect, useState } from "react"
import api from "../services/api"

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

    if (loading) return <p style={{ color: "#666", fontSize: "13px" }}>Scanning for emerging issues...</p>
    if (!clusters.length) return (
        <p style={{ color: "#666", fontSize: "13px" }}>
            No flagged emerging clusters detected. Run a Kaggle sync to generate this data.
        </p>
    )

    return (
        <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
            <p style={{ fontSize: "13px", color: "#888", margin: "0 0 8px" }}>
                These complaint clusters were detected among low-confidence, uncategorized reviews.
                They may represent <strong style={{ color: "#FFB347" }}>new issue types</strong> not yet in the taxonomy.
            </p>

            {clusters.map((cluster, i) => {
                const isOpen = expanded === i
                const urgency = cluster.estimated_volume >= 150 ? "CRITICAL" : cluster.estimated_volume >= 80 ? "HIGH" : "WATCH"
                const urgencyColor = urgency === "CRITICAL" ? "#E50914" : urgency === "HIGH" ? "#FF6B35" : "#FFB347"

                return (
                    <div key={i} style={{
                        background: "rgba(255,255,255,0.03)",
                        border: `1px solid ${urgencyColor}33`,
                        borderLeft: `3px solid ${urgencyColor}`,
                        borderRadius: "10px",
                        padding: "14px 18px",
                        cursor: "pointer"
                    }}
                        onClick={() => setExpanded(isOpen ? null : i)}
                    >
                        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                            <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
                                <span style={{
                                    fontSize: "11px", fontWeight: 800, padding: "2px 8px",
                                    borderRadius: "4px", background: `${urgencyColor}22`, color: urgencyColor
                                }}>
                                    {urgency}
                                </span>
                                <span style={{ fontWeight: 600, fontSize: "14px" }}>
                                    Cluster #{cluster.cluster_id + 1}
                                </span>
                            </div>
                            <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                                <span style={{ fontSize: "13px", color: "#888" }}>
                                    ~{cluster.estimated_volume.toLocaleString()} reviews
                                </span>
                                <span style={{ color: "#555", fontSize: "12px" }}>{isOpen ? "▲" : "▼"}</span>
                            </div>
                        </div>

                        {isOpen && (
                            <div style={{ marginTop: "14px", display: "flex", flexDirection: "column", gap: "8px" }}>
                                {cluster.sample_reviews.map((r, j) => (
                                    <div key={j} style={{
                                        background: "rgba(255,255,255,0.03)",
                                        borderRadius: "6px",
                                        padding: "10px 12px",
                                        fontSize: "13px",
                                        color: "#ccc",
                                        fontStyle: "italic"
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
