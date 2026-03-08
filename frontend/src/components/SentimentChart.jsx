import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip, Legend } from "recharts"
import { useEffect, useState } from "react"
import api from "../services/api"
import { SkeletonChart } from "./Skeleton"

const COLORS = ["#1DB954", "#E50914"]

export default function SentimentChart({ limitMonths = 0 }) {
  const [data, setData] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    setLoading(true)
    api.get("/dashboard/sentiment", { params: { limit_months: limitMonths } })
      .then(res => {
        setData([
          { name: "Positive", value: res.data.positive },
          { name: "Negative", value: res.data.negative }
        ])
      })
      .catch(() => setData([]))
      .finally(() => setLoading(false))
  }, [limitMonths])

  if (loading) return <SkeletonChart height={300} />

  const total = data.reduce((s, d) => s + d.value, 0)

  return (
    <PieChart width={380} height={300}>
      <Pie
        data={data}
        dataKey="value"
        nameKey="name"
        outerRadius={110}
        innerRadius={55}
        paddingAngle={3}
        label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
        labelLine={false}
      >
        {data.map((_, i) => (
          <Cell key={i} fill={COLORS[i]} />
        ))}
      </Pie>
      <Tooltip
        formatter={(value) => [`${value.toLocaleString()} reviews`, ""]}
        contentStyle={{ background: "rgba(18,18,18,0.95)", border: "1px solid #333", borderRadius: 8, color: "#fff" }}
      />
      <Legend wrapperStyle={{ color: "#ccc", fontSize: 13 }} />
    </PieChart>
  )
}