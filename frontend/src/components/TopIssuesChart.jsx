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

// Severity → color scale (green → amber → red)
function severityColor(sev) {
  if (sev >= 4.0) return "#E50914"  // critical — brand red
  if (sev >= 3.0) return "#FF6B35"  // high — orange
  if (sev >= 2.5) return "#FFB347"  // medium — amber
  return "#4CAF50"                   // low — green
}

function CustomTooltip({ active, payload }) {
  if (!active || !payload || !payload.length) return null
  const d = payload[0].payload
  const velColor = d.velocity_dir === "up" ? "#1DB954" : d.velocity_dir === "down" ? "#E50914" : d.velocity_dir === "new" ? "#00B4D8" : "#888"
  return (
    <div style={{
      background: "rgba(18,18,18,0.95)",
      border: "1px solid #333",
      borderRadius: "8px",
      padding: "12px 16px",
      fontSize: "13px",
      color: "#fff",
      maxWidth: "260px"
    }}>
      <div style={{ fontWeight: 700, marginBottom: 6 }}>{d.issue}</div>
      <div style={{ color: "#aaa" }}>
        Score (Severity-Weighted): <span style={{ color: "#fff", fontWeight: 600 }}>{d.sort_metric ? d.sort_metric.toFixed(1) : d.mentions.toLocaleString()}</span>
      </div>
      {d.velocity_label && (
        <div style={{ color: velColor, fontWeight: 700, marginTop: 4, fontSize: "12px" }}>
          {d.velocity_dir === "up" ? "↑" : d.velocity_dir === "down" ? "↓" : "★"}{" "}
          {d.velocity_label} vs. prev period
        </div>
      )}
      {d.avg_severity > 0 && (
        <div style={{ color: "#aaa", marginTop: 4 }}>
          Avg Severity:&nbsp;
          <span style={{ color: severityColor(d.avg_severity), fontWeight: 700 }}>
            {d.avg_severity.toFixed(1)} / 5.0
          </span>
          &nbsp;{"●".repeat(Math.round(d.avg_severity))}
        </div>
      )}
    </div>
  )
}

// Custom Y-axis tick that renders the issue label + velocity arrow
function VelocityTick({ x, y, payload, data }) {
  const issue = data.find(d => d.issue === payload.value)
  const dir = issue?.velocity_dir
  const lbl = issue?.velocity_label
  const arrow = dir === "up" ? "↑" : dir === "down" ? "↓" : dir === "new" ? "★" : ""
  const arrowColor = dir === "up" ? "#1DB954" : dir === "down" ? "#E50914" : dir === "new" ? "#00B4D8" : "transparent"
  const shortName = payload.value.length > 22 ? payload.value.slice(0, 21) + "…" : payload.value
  return (
    <g transform={`translate(${x},${y})`}>
      <text x={-8} y={0} dy={4} textAnchor="end" fill="#ccc" fontSize={12}>{shortName}</text>
      {arrow && (
        <text x={-8 + (shortName.length * 7 * -1) - 6} y={0} dy={4} textAnchor="end" fill={arrowColor} fontSize={11} fontWeight={800}>
          {arrow}
        </text>
      )}
    </g>
  )
}


export default function TopIssuesChart({ onIssueClick, limitMonths = 0 }) {
  const [data, setData] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const fetchIssues = async () => {
      setLoading(true)
      try {
        const res = await api.get("/dashboard/top-issues", { params: { limit_months: limitMonths } })
        setData(res.data || [])
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

  if (!data.length) {
    return <p style={{ color: "#888" }}>No issue data yet. Run a Kaggle sync to generate insights.</p>
  }

  return (
    <div style={{ width: "100%", height: 420 }}>
      <ResponsiveContainer>
        <BarChart
          data={data}
          layout="vertical"
          margin={{ top: 10, right: 50, left: 20, bottom: 10 }}
        >
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
          <XAxis
            type="number"
            tick={{ fill: "#888", fontSize: 12 }}
            axisLine={false}
            tickLine={false}
          />
          <YAxis
            type="category"
            dataKey="issue"
            width={240}
            tick={<VelocityTick data={data} />}
            axisLine={false}
            tickLine={false}
          />
          <Tooltip content={<CustomTooltip />} cursor={{ fill: "rgba(255,255,255,0.03)" }} />
          <Bar
            dataKey="mentions"
            radius={[0, 6, 6, 0]}
            onClick={(entry) => handleClick(entry)}
            cursor="pointer"
          >
            {data.map((entry, index) => (
              <Cell
                key={`cell-${index}`}
                fill={severityColor(entry.avg_severity || 0)}
                fillOpacity={0.85}
              />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>

      {/* Severity legend */}
      <div style={{ display: "flex", gap: "20px", justifyContent: "center", marginTop: "12px", fontSize: "12px", color: "#888" }}>
        {[
          { label: "Low (< 2.5)", color: "#4CAF50" },
          { label: "Medium (2.5–3.0)", color: "#FFB347" },
          { label: "High (3.0–4.0)", color: "#FF6B35" },
          { label: "Critical (≥ 4.0)", color: "#E50914" },
        ].map(({ label, color }) => (
          <span key={label} style={{ display: "flex", alignItems: "center", gap: "6px" }}>
            <span style={{ width: 10, height: 10, borderRadius: 2, background: color, display: "inline-block" }} />
            {label}
          </span>
        ))}
      </div>
    </div>
  )
}