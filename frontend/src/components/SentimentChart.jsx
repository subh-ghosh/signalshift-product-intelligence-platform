import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip } from "recharts"
import { useEffect, useState } from "react"
import api from "../services/api"
import { SkeletonChart } from "./Skeleton"

const COLORS = ["#31b57e", "#ea5b57"]

function getMomentumMeta(momentum) {
  if (momentum > 1) return { label: `Improving ${Math.abs(momentum)} pts`, color: "#31b57e", background: "rgba(49, 181, 126, 0.12)" }
  if (momentum < -1) return { label: `Declining ${Math.abs(momentum)} pts`, color: "#ea5b57", background: "rgba(234, 91, 87, 0.12)" }
  return { label: "Holding steady", color: "#72788c", background: "rgba(114, 120, 140, 0.12)" }
}

export default function SentimentChart({ limitMonths = 0, onSentimentClick }) {
  const [data, setData] = useState([])
  const [momentum, setMomentum] = useState(0)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api.get("/dashboard/sentiment", { params: { limit_months: limitMonths } })
      .then((res) => {
        setData([
          { name: "Positive", value: res.data.positive },
          { name: "Negative", value: res.data.negative },
        ])
        setMomentum(res.data.momentum || 0)
      })
      .catch(() => setData([]))
      .finally(() => setLoading(false))
  }, [limitMonths])

  if (loading) return <SkeletonChart height={300} />

  const total = data.reduce((sum, item) => sum + item.value, 0)

  if (total === 0) {
    return (
      <div style={{ textAlign: "center", padding: "40px 20px" }}>
        <div style={{ fontSize: "28px", marginBottom: "12px", opacity: 0.8 }}>📊</div>
        <p style={{ color: "#72788c", fontSize: "14px", margin: 0 }}>No sentiment data available for this time period.</p>
      </div>
    )
  }

  const positive = data[0].value
  const negative = data[1].value
  const positivePct = Math.round((positive / total) * 100)
  const negativePct = 100 - positivePct
  const momentumMeta = getMomentumMeta(momentum)

  return (
    <div className="sentiment-scorecard">
      <div className="sentiment-scorecard__topline">
        <div>
          <div className="sentiment-scorecard__eyebrow">Current health</div>
          <div className="sentiment-scorecard__headline">{positivePct}% positive sentiment</div>
          <div className="sentiment-scorecard__copy">Negative sentiment accounts for {negativePct}% of the active review window.</div>
        </div>
        <span className="sentiment-scorecard__momentum" style={{ color: momentumMeta.color, background: momentumMeta.background }}>
          {momentumMeta.label}
        </span>
      </div>

      <div className="sentiment-scorecard__body">
        <div className="sentiment-scorecard__chart">
          <ResponsiveContainer width="100%" height={240}>
            <PieChart>
              <Pie
                data={data}
                dataKey="value"
                nameKey="name"
                outerRadius={84}
                innerRadius={62}
                paddingAngle={2}
                stroke="none"
              >
                {data.map((entry, index) => (
                  <Cell key={entry.name} fill={COLORS[index]} />
                ))}
              </Pie>
              <Tooltip
                formatter={(value) => [`${value.toLocaleString()} reviews`, "Count"]}
                contentStyle={{
                  background: "#FFFFFF",
                  border: "1px solid rgba(91, 100, 121, 0.12)",
                  borderRadius: "12px",
                  color: "#262c3f",
                  boxShadow: "0 8px 18px rgba(49, 57, 77, 0.08)",
                  fontSize: "13px",
                  fontWeight: 600,
                }}
                itemStyle={{ color: "#262c3f", fontWeight: "700" }}
              />
            </PieChart>
          </ResponsiveContainer>

          <div className="sentiment-scorecard__center">
            <strong>{positivePct}%</strong>
            <span>Positive</span>
          </div>
        </div>

        <div className="sentiment-scorecard__side">
          <div className="sentiment-scorecard__stats">
            <div className="sentiment-stat">
              <span className="sentiment-stat__label">Positive reviews</span>
              <strong>{positive.toLocaleString()}</strong>
            </div>
            <div className="sentiment-stat">
              <span className="sentiment-stat__label">Negative reviews</span>
              <strong>{negative.toLocaleString()}</strong>
            </div>
          </div>

          <div className="sentiment-scorecard__actions">
            <button type="button" className="sentiment-action sentiment-action--positive" onClick={() => onSentimentClick && onSentimentClick("positive")}>
              View Positive Feedback
            </button>
            <button type="button" className="sentiment-action sentiment-action--negative" onClick={() => onSentimentClick && onSentimentClick("negative")}>
              View Negative Feedback
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
