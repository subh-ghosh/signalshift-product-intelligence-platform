import { useState, useEffect } from "react"
import ReactMarkdown from "react-markdown"
import api from "../services/api"

export default function ExecutiveSummary({ range }) {
  const [summary, setSummary] = useState("")
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchSummary()
  }, [range])

  const fetchSummary = async () => {
    try {
      setLoading(true)
      let limit = 0
      if (range === "3M") limit = 3
      else if (range === "6M") limit = 6
      else if (range === "12M") limit = 12

      const res = await api.get("/dashboard/ai-summary", {
        params: { limit_months: limit },
      })
      setSummary(res.data.summary)
    } catch (error) {
      console.error(error)
      setSummary("> **System Offline:** Could not fetch insights from the analysis engine.")
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="mini-item">
        <div className="mini-item__icon">✦</div>
        <div>
          <p className="mini-item__title">Preparing summary</p>
          <p className="mini-item__description">Putting together the latest insight narrative for this window.</p>
        </div>
      </div>
    )
  }

  return (
    <div className="page-grid">
      <div className="panel__header" style={{ marginBottom: 0 }}>
        <div>
          <div className="panel__eyebrow">Executive narrative</div>
          <h3 className="panel__title panel__title--section">AI-generated summary</h3>
        </div>
        <div className="status-badge">Analysis overview</div>
      </div>

      <div className="markdown-body" style={{ lineHeight: 1.85, fontSize: "0.95rem" }}>
        <ReactMarkdown
          components={{
            h3: ({ node, ...props }) => (
              <h3
                style={{
                  color: "var(--text-strong)",
                  borderBottom: "1px solid rgba(173, 183, 204, 0.22)",
                  paddingBottom: "10px",
                }}
                {...props}
              />
            ),
            p: ({ node, ...props }) => <p style={{ color: "var(--text-body)" }} {...props} />,
            ul: ({ node, ...props }) => <ul style={{ color: "var(--text-body)" }} {...props} />,
            strong: ({ node, ...props }) => <strong style={{ color: "var(--text-strong)" }} {...props} />,
            blockquote: ({ node, ...props }) => (
              <blockquote
                style={{
                  margin: 0,
                  padding: "16px 18px",
                  borderRadius: "18px",
                  background: "rgba(239, 244, 252, 0.88)",
                  border: "1px solid rgba(171, 181, 203, 0.18)",
                  color: "var(--text-strong)",
                }}
                {...props}
              />
            ),
          }}
        >
          {summary}
        </ReactMarkdown>
      </div>
    </div>
  )
}
