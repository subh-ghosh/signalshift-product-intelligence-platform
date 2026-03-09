export default function IssueReviews({ issue, reviews }) {

  if (!issue) {
    return (
      <div className="glass-card" style={{ textAlign: "center", padding: "40px 20px", marginTop: "24px" }}>
        <p style={{ color: "#64748B", fontSize: "14px", margin: 0, fontWeight: "500" }}>
          Select an issue to see related customer verbatim.
        </p>
      </div>
    );
  }

  return (
    <div className="glass-card" style={{ marginTop: "24px" }}>
      <div style={{ marginBottom: "20px", borderBottom: "1px solid #E2E8F0", paddingBottom: "12px" }}>
        <h3 style={{ margin: 0, fontSize: "18px", color: "#0F172A", fontWeight: "700" }}>
          Customer Verbatim: <span style={{ color: "#3B82F6" }}>{issue}</span>
        </h3>
      </div>

      <ul style={{
        listStyleType: "none",
        padding: 0,
        margin: 0,
        display: "flex",
        flexDirection: "column",
        gap: "12px",
        maxHeight: "500px",
        overflowY: "auto",
        paddingRight: "8px"
      }}>
        {reviews.map((r, i) => (
          <li key={i} style={{
            background: "#F8FAFC",
            border: "1px solid #E2E8F0",
            borderRadius: "10px",
            padding: "16px",
            fontSize: "14px",
            color: "#334155",
            lineHeight: "1.6",
            borderLeft: "3px solid #CBD5E1"
          }}>
            "{r}"
          </li>
        ))}
      </ul>
    </div>
  )
}