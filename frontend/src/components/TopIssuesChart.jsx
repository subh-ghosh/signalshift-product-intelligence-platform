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
      <div style={{ fontWeight: 700, marginBottom: 6, color: "#fff" }}>{d.issue}</div>
      <div style={{ color: "#aaa" }}>
        Mentions: <span style={{ color: "#fff", fontWeight: 600 }}>{d.mentions.toLocaleString()}</span>
      </div>
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
    return <p style={{ color: "#888" }}>Loading issues...</p>
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
            width={230}
            tick={{ fill: "#ccc", fontSize: 12 }}
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