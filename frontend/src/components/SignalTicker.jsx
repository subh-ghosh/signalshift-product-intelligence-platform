import { useState, useEffect } from "react"
import api from "../services/api"

export default function SignalTicker() {
  const [messages, setMessages] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const fetchTicker = async () => {
      try {
        const res = await api.get("/dashboard/live-ticker")
        setMessages(res.data || [])
      } catch (error) {
        console.error("Ticker fetch error:", error)
      } finally {
        setLoading(false)
      }
    }

    fetchTicker()
    const interval = setInterval(fetchTicker, 60000)
    return () => clearInterval(interval)
  }, [])

  if (loading || messages.length === 0) return null

  const duplicated = [...messages, ...messages]

  return (
    <div className="ticker-shell">
      <div className="ticker-shell__label status-badge">Live review feed</div>
      <div className="ticker-shell__track">
        <div className="ticker-shell__items">
          {duplicated.map((message, index) => {
            const tone =
              message.sentiment === "positive"
                ? "is-positive"
                : message.sentiment === "negative"
                  ? "is-critical"
                  : "is-warning"

            return (
              <div className="ticker-chip" key={`${message.at}-${index}`}>
                <span className={`status-badge ${tone}`}>
                  {message.sentiment === "positive"
                    ? "Positive"
                    : message.sentiment === "negative"
                      ? "Critical"
                      : "Watch"}
                </span>
                <span className="faint">
                  {new Date(message.at).toLocaleDateString([], { month: "short", day: "numeric" })}
                </span>
                <span className="muted">"{message.text}..."</span>
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}
