import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip, Legend } from "recharts"
import { useEffect, useState } from "react"
import api from "../services/api"
import { SkeletonChart } from "./Skeleton"

// Clean Light Theme Colors: Emerald for Positive, Rose for Negative
const COLORS = ["#10B981", "#EF4444"]

export default function SentimentChart({ limitMonths = 0, onSentimentClick }) {
  const [data, setData] = useState([])
  const [momentum, setMomentum] = useState(0)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    setLoading(true)
    api.get("/dashboard/sentiment", { params: { limit_months: limitMonths } })
      .then(res => {
        setData([
          { name: "Positive", value: res.data.positive },
          { name: "Negative", value: res.data.negative }
        ])
        setMomentum(res.data.momentum || 0)
      })
      .catch(() => setData([]))
      .finally(() => setLoading(false))
  }, [limitMonths])

  if (loading) return <SkeletonChart height={300} />

  const total = data.reduce((s, d) => s + d.value, 0)

  if (total === 0) return (
    <div style={{ textAlign: "center", padding: "40px 20px" }}>
      <div style={{ fontSize: "28px", marginBottom: "12px", opacity: 0.8 }}>📊</div>
      <p style={{ color: "#64748B", fontSize: "14px", margin: 0 }}>No sentiment data available for this time period.</p>
    </div>
  )

  const posPct = Math.round((data[0].value / total) * 100)

  return (
    <div style={{ position: "relative", width: "100%", height: "300px", display: "flex", justifyContent: "center" }}>
      <ResponsiveContainer width="100%" height="100%">
        <PieChart>
          <Pie
            data={data}
            dataKey="value"
            nameKey="name"
            outerRadius={100}
            innerRadius={75}
            paddingAngle={2} // Tighter padding for a cleaner look
            stroke="none"
            onClick={(data) => onSentimentClick && onSentimentClick(data.name.toLowerCase())}
            style={{ cursor: onSentimentClick ? 'pointer' : 'default', outline: 'none' }}
          >
            {data.map((entry, i) => (
              <Cell
                key={i}
                fill={COLORS[i]}
                style={{
                  transition: 'all 0.2s ease'
                  // Removed the heavy neon drop-shadow
                }}
              />
            ))}
          </Pie>
          <Tooltip
            formatter={(value) => [`${value.toLocaleString()} reviews`, "Count"]}
            contentStyle={{
              background: "#FFFFFF",
              border: "1px solid #E2E8F0",
              borderRadius: "8px",
              color: "#0F172A",
              boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.03)',
              fontSize: '13px',
              fontWeight: 600
            }}
            itemStyle={{ color: "#0F172A", fontWeight: "700" }}
          />
          <Legend
            verticalAlign="bottom"
            height={36}
            iconType="circle"
            wrapperStyle={{ color: "#475569", fontSize: "13px", fontWeight: "600" }}
          />
        </PieChart>
      </ResponsiveContainer>

      {/* Center Momentum & Percentage Indicator */}
      <div style={{
        position: "absolute",
        top: "45%",
        left: "50%",
        transform: "translate(-50%, -50%)",
        textAlign: "center",
        pointerEvents: "none"
      }}>
        <div style={{ fontSize: "36px", fontWeight: 800, color: "#0F172A", lineHeight: 1 }}>
          {posPct}%
        </div>
        <div style={{ fontSize: "11px", color: "#64748B", fontWeight: 600, textTransform: "uppercase", marginTop: "6px", letterSpacing: "0.05em" }}>
          Positive Feedback
        </div>

        {/* Clean Pill Momentum Badge */}
        <div title="Change in positive sentiment compared to the previous period" style={{
          marginTop: "8px",
          fontSize: "12px",
          fontWeight: 700,
          color: momentum >= 0 ? "#10B981" : "#EF4444",
          background: momentum >= 0 ? "#ECFDF5" : "#FEF2F2",
          padding: "4px 10px",
          borderRadius: "12px",
          display: "inline-block",
          pointerEvents: "auto"
        }}>
          {momentum >= 0 ? '↑' : '↓'} {Math.abs(momentum)}%
        </div>
      </div>
    </div>
  )
}