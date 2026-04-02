import { useState, useEffect } from "react"
import api from "../services/api"
import { highlightEntities } from "../utils/highlight_utils.jsx"

export default function DiagnosticDrawer({ isOpen, onClose, aspect, month, topic }) {
  const [evidence, setEvidence] = useState([])
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (isOpen) fetchEvidence()
  }, [isOpen, aspect, month, topic])

  const fetchEvidence = async () => {
    try {
      setLoading(true)
      const res = await api.get("/dashboard/diagnostic-evidence", {
        params: { aspect, month, topic },
      })
      setEvidence(res.data || [])
    } catch (error) {
      console.error("Evidence fetch error:", error)
    } finally {
      setLoading(false)
    }
  }

  if (!isOpen) return null

  return (
    <>
      <div className="drawer-overlay" onClick={onClose} />
      <aside className="drawer-panel panel" aria-label="Diagnostic evidence drawer">
        <div className="page-grid" style={{ height: "100%" }}>
          <div className="panel__header">
            <div>
              <div className="panel__eyebrow">Diagnostic evidence</div>
              <h2 className="panel__title panel__title--section">Customer comments</h2>
              <p className="panel__text">
                {month ? `Period: ${month}` : "Current selection"}
                {topic ? ` · Focus: ${topic}` : ""}
                {aspect ? ` · Aspect: ${aspect}` : ""}
              </p>
            </div>
            <button className="app-icon-button" onClick={onClose} type="button" aria-label="Close drawer">
              ×
            </button>
          </div>

          <div style={{ overflowY: "auto", minHeight: 0 }} className="review-grid">
            {loading ? (
              <div className="auth-note">Loading reviews...</div>
            ) : evidence.length > 0 ? (
              evidence.map((review, index) => {
                const isEnterprise = review.user_tier === "Enterprise" || (review.value_weight && review.value_weight >= 4)
                const isPremium = review.user_tier === "Premium" || (review.value_weight && review.value_weight >= 2)

                return (
                  <article className="review-card" key={index}>
                    <div className="review-card__meta">
                      <div style={{ display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap" }}>
                        {isEnterprise ? <span className="status-badge is-critical">Enterprise</span> : null}
                        {!isEnterprise && isPremium ? <span className="status-badge is-warning">Premium</span> : null}
                        <span className="status-badge">{"★".repeat(parseInt(review.score, 10) || 0)}{"☆".repeat(5 - (parseInt(review.score, 10) || 0))}</span>
                        {review.upvotes > 0 ? <span className="status-badge">{review.upvotes} upvotes</span> : null}
                      </div>
                      <div style={{ textAlign: "right" }}>
                        <div className="muted" style={{ fontSize: "0.82rem", fontWeight: 700 }}>
                          {review.at ? review.at.split("T")[0] : "Recent"}
                        </div>
                        {review.app_version && review.app_version !== "N/A" && review.app_version !== "Build N/A" ? (
                          <div className="faint" style={{ fontSize: "0.76rem", fontWeight: 700 }}>
                            Ver {review.app_version.replace("Build ", "")}
                          </div>
                        ) : null}
                      </div>
                    </div>

                    <p
                      className="review-card__quote"
                      style={{ fontStyle: parseInt(review.score, 10) <= 2 ? "italic" : "normal" }}
                    >
                      "
                      {highlightEntities(
                        review.text || "",
                        "slow, crash, bug, error, login, payment, expensive, price, quality, feature",
                      )}
                      "
                    </p>

                    {review.value_weight > 1 ? (
                      <div style={{ display: "flex", justifyContent: "flex-end" }}>
                        <span className="status-badge is-critical">
                          {review.value_weight.toFixed(1)}x business importance
                        </span>
                      </div>
                    ) : null}
                  </article>
                )
              })
            ) : (
              <div className="auth-note">No specific evidence found for this cross-section.</div>
            )}
          </div>
        </div>
      </aside>
    </>
  )
}
