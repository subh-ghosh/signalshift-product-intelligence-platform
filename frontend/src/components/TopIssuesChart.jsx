import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  Cell,
  ResponsiveContainer
} from "recharts"

import { useEffect, useState } from "react"
import api from "../services/api"
import { SkeletonChart } from "./Skeleton"

// Clean Light Theme Severity → color scale
function severityColor(sev) {
  if (sev >= 4.0) return "#EF4444"  // Critical — Rose Red
  if (sev >= 3.0) return "#F59E0B"  // High — Amber
  if (sev >= 2.5) return "#3B82F6"  // Medium — Primary Blue
  return "#10B981"                  // Low — Emerald Green
}

function CustomTooltip({ active, payload }) {
  if (!active || !payload || !payload.length) return null
  const d = payload[0].payload
  const velColor = d.velocity_dir === "up" ? "#10B981" : d.velocity_dir === "down" ? "#EF4444" : d.velocity_dir === "new" ? "#3B82F6" : "#64748B"

  return (
    <div style={{
      background: "#FFFFFF",
      border: "1px solid #E2E8F0",
      borderRadius: "12px",
      padding: "16px",
      fontSize: "13px",
      color: "#0F172A",
      maxWidth: "260px",
      boxShadow: "0 10px 15px -3px rgba(0, 0, 0, 0.08), 0 4px 6px -2px rgba(0, 0, 0, 0.04)"
    }}>
      <div style={{ fontWeight: 700, marginBottom: 8, fontSize: "14px", borderBottom: "1px solid #E2E8F0", paddingBottom: "8px" }}>
        {d.issue}
      </div>
      <div style={{ marginBottom: "12px" }}>
        <div style={{ color: "#0F172A", fontWeight: 800, fontSize: "16px" }}>
          {d.revenue_risk ? `$${d.revenue_risk.toFixed(2)} Risk` : `${d.sort_metric.toFixed(1)} Level`}
        </div>
      </div>
      <div style={{ color: "#475569" }}>
        Complaints Found: <span style={{ color: "#0F172A", fontWeight: 700 }}>{d.mentions.toLocaleString()}</span>
      </div>
      {d.velocity_label && (
        <div style={{ color: velColor, fontWeight: 700, marginTop: 8, fontSize: "12px", background: `${velColor}15`, display: 'inline-block', padding: '2px 8px', borderRadius: '6px' }}>
          {d.velocity_dir === "up" ? "↑" : d.velocity_dir === "down" ? "↓" : "★"}{" "}
          {d.velocity_label} Trend
        </div>
      )}
      {d.avg_severity > 0 && (
        <div style={{ color: "#64748B", marginTop: 10, fontSize: "12px", fontWeight: 500 }}>
          Priority:&nbsp;
          <span style={{ color: severityColor(d.avg_severity) }}>{"●".repeat(Math.round(d.avg_severity))}</span>
        </div>
      )}
    </div>
  )
}

// Custom Y-axis tick that renders the issue label + velocity arrow
function VelocityTick({ x, y, payload, data }) {
  const issue = data.find(d => d.issue === payload.value)
  const dir = issue?.velocity_dir
  const arrow = dir === "up" ? "↑" : dir === "down" ? "↓" : dir === "new" ? "★" : ""
  const arrowColor = dir === "up" ? "#10B981" : dir === "down" ? "#EF4444" : dir === "new" ? "#3B82F6" : "transparent"
  const shortName = payload.value.length > 22 ? payload.value.slice(0, 21) + "…" : payload.value

  return (
    <g transform={`translate(${x},${y})`}>
      <text x={-8} y={0} dy={4} textAnchor="end" fill="#475569" fontSize={12} fontWeight={600}>{shortName}</text>
      {arrow && (
        <text x={-8 + (shortName.length * 7 * -1) - 6} y={0} dy={4} textAnchor="end" fill={arrowColor} fontSize={12} fontWeight={800}>
          {arrow}
        </text>
      )}
    </g>
  )
}


export default function TopIssuesChart({ onIssueClick, limitMonths = 0 }) {
  const [data, setData] = useState([])
  const [loading, setLoading] = useState(true)
  const [sortByRevenue, setSortByRevenue] = useState(true)

  useEffect(() => {
    const fetchIssues = async () => {
      setLoading(true)
      try {
        const res = await api.get("/dashboard/top-issues", { params: { limit_months: limitMonths } })
        const filtered = (res.data || []).filter(item => item.issue !== "General App Feedback")
        setData(filtered)
      } catch (err) {
        console.error("Failed to load issues", err)
      } finally {
        setLoading(false)
      }
    }
    fetchIssues()
  }, [limitMonths])

  const handleClick = (entry) => {
    if (!entry || !entry.issue) return
    if (onIssueClick) onIssueClick(entry.issue)
  }

  if (loading) {
    return <SkeletonChart height={420} />
  }

  const sortedData = [...data].sort((a, b) => {
    if (sortByRevenue && a.revenue_risk !== undefined) {
      return (b.revenue_risk || 0) - (a.revenue_risk || 0)
    }
    return b.mentions - a.mentions
  })

  if (!data.length) {
    return <p style={{ color: "#64748B", padding: "20px 0", fontWeight: 500 }}>No specific high-signal issues detected in this window.</p>
  }

  return (
    <div style={{ width: "100%", height: 460 }}>
      {/* Precision Toggle - Clean Light Theme */}
      <div style={{ display: "flex", justifyContent: "flex-end", marginBottom: "20px" }}>
        <div style={{
          display: "flex",
          background: "#F1F5F9",
          borderRadius: "10px",
          padding: "4px",
          border: "1px solid #E2E8F0"
        }}>
          <button
            title="Estimated financial risk based on impact and severity"
            onClick={() => setSortByRevenue(true)}
            style={{
              padding: "6px 14px",
              borderRadius: "8px",
              border: "none",
              fontSize: "12px",
              fontWeight: 700,
              cursor: "pointer",
              transition: "all 0.2s ease",
              background: sortByRevenue ? "#FFFFFF" : "transparent",
              color: sortByRevenue ? "#3B82F6" : "#64748B",
              boxShadow: sortByRevenue ? "0 1px 3px rgba(0,0,0,0.1)" : "none"
            }}
          >
            Financial Impact
          </button>
          <button
            title="Total number of times this issue was found"
            onClick={() => setSortByRevenue(false)}
            style={{
              padding: "6px 14px",
              borderRadius: "8px",
              border: "none",
              fontSize: "12px",
              fontWeight: 700,
              cursor: "pointer",
              transition: "all 0.2s ease",
              background: !sortByRevenue ? "#FFFFFF" : "transparent",
              color: !sortByRevenue ? "#3B82F6" : "#64748B",
              boxShadow: !sortByRevenue ? "0 1px 3px rgba(0,0,0,0.1)" : "none"
            }}
          >
            Number of Complaints
          </button>
        </div>
      </div>

      <ResponsiveContainer height={380}>
        <BarChart
          data={sortedData}
          layout="vertical"
          margin={{ top: 10, right: 30, left: 20, bottom: 10 }}
        >
          <CartesianGrid strokeDasharray="3 3" stroke="#E2E8F0" vertical={false} />
          <XAxis
            type="number"
            tick={false}
            axisLine={false}
            tickLine={false}
            domain={[0, 'dataMax + 5']}
          />
          <YAxis
            type="category"
            dataKey="issue"
            width={220}
            tick={<VelocityTick data={sortedData} />}
            axisLine={false}
            tickLine={false}
          />
          <Tooltip content={<CustomTooltip />} cursor={{ fill: "#F8FAFC" }} />
          <Bar
            dataKey={sortByRevenue && sortedData.some(d => d.revenue_risk !== null && d.revenue_risk !== undefined) ? "revenue_risk" : "mentions"}
            radius={[0, 6, 6, 0]} /* Rounded edges for premium feel */
            onClick={(entry) => handleClick(entry)}
            cursor="pointer"
            barSize={20}
          >
            {sortedData.map((entry, index) => (
              <Cell
                key={`cell-${index}`}
                fill={severityColor(entry.avg_severity || 0)}
                fillOpacity={0.9}
                style={{ transition: 'all 0.2s ease' }}
              />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>

      {/* Urgency legend - Flat Light Theme Colors */}
      <div style={{ display: "flex", gap: "24px", justifyContent: "center", marginTop: "16px", fontSize: "12px", color: "#475569", fontWeight: 600 }}>
        {[
          { label: "Low", color: "#10B981" },
          { label: "Medium", color: "#3B82F6" },
          { label: "High", color: "#F59E0B" },
          { label: "Critical", color: "#EF4444" },
        ].map(({ label, color }) => (
          <span key={label} style={{ display: "flex", alignItems: "center", gap: "8px" }}>
            <span style={{ width: 12, height: 12, borderRadius: 3, background: color, display: "inline-block" }} />
            {label}
          </span>
        ))}
      </div>
    </div>
  )
}