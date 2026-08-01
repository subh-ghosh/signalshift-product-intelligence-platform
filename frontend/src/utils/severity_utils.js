/**
 * Shared severity/status utility — single source of truth across ALL dashboard components.
 * Using ONE consistent set of labels everywhere prevents confusion.
 */

/** Problem severity based on a score from 0–5 (higher = worse) */
export function getSeverityMeta(score) {
  const s = Number(score) || 0;
  if (s >= 4.0) return { label: "Critical",  color: "#ea5b57", background: "rgba(234, 91, 87, 0.12)" };
  if (s >= 3.0) return { label: "High",      color: "#eca74c", background: "rgba(236, 167, 76, 0.14)" };
  if (s >= 2.5) return { label: "Medium",    color: "#4b78b4", background: "rgba(75, 120, 180, 0.12)" };
  return         { label: "Low",       color: "#31b57e", background: "rgba(49, 181, 126, 0.12)" };
}

/** Velocity direction for topics/issues */
export function getVelocityMeta(direction, label) {
  if (direction === "up")   return { label: `Rising ${label || ""}`.trim(),  color: "#ea5b57", background: "rgba(234, 91, 87, 0.12)" };
  if (direction === "down") return { label: `Falling ${label || ""}`.trim(), color: "#31b57e", background: "rgba(49, 181, 126, 0.12)" };
  if (direction === "new")  return { label: "New",    color: "#4b78b4", background: "rgba(75, 120, 180, 0.12)" };
  return                           { label: "Stable", color: "#72788c", background: "rgba(114, 120, 140, 0.12)" };
}

/** Momentum direction for aspects (positive momentum_pct = getting worse) */
export function getMomentumMeta(momentumPct) {
  const p = Number(momentumPct) || 0;
  if (p > 5)  return { label: `Getting worse ${Math.abs(p)}%`, color: "#ea5b57", background: "rgba(234, 91, 87, 0.12)" };
  if (p < -5) return { label: `Improving ${Math.abs(p)}%`,     color: "#31b57e", background: "rgba(49, 181, 126, 0.12)" };
  return              { label: "Holding steady",                color: "#72788c", background: "rgba(114, 120, 140, 0.12)" };
}

/** Signal state for volume-based emerging cluster panels */
export function getClusterSignalState(volume, momentum) {
  const v = Number(volume) || 0;
  const m = Number(momentum) || 0;
  if (v >= 150 || m >= 75) return { label: "Critical", tone: "critical" };
  if (v >= 80  || m >= 30) return { label: "Active",   tone: "active" };
  return                          { label: "Watch",    tone: "watch" };
}

/** Semantic drift state for language-shift panels */
export function getDriftState(score) {
  const s = Number(score) || 0;
  if (s > 0.18) return { label: "New issue likely",    tone: "critical", helper: "Complaint language is shifting fast enough to suggest a new problem inside this category." };
  if (s > 0.14) return { label: "Meaning is shifting", tone: "active",   helper: "Customers are describing this category differently than before." };
  return               { label: "Watch wording",       tone: "watch",    helper: "The category is evolving, but the shift is still moderate." };
}
