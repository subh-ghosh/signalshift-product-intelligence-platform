import { useEffect, useState, useRef } from "react"

// Animated shimmer skeleton for loading states
// Usage: <Skeleton width="100%" height={20} />  or  <Skeleton lines={3} />

function SkeletonBlock({ width = "100%", height = 16, borderRadius = 6, style = {} }) {
    return (
        <div style={{
            width,
            height,
            borderRadius,
            background: "linear-gradient(90deg, rgba(255,255,255,0.04) 25%, rgba(255,255,255,0.10) 50%, rgba(255,255,255,0.04) 75%)",
            backgroundSize: "200% 100%",
            animation: "shimmer 1.6s infinite",
            ...style
        }} />
    )
}

// Multi-line text skeleton
export function SkeletonText({ lines = 3, lastLineWidth = "70%" }) {
    return (
        <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
            {Array.from({ length: lines }).map((_, i) => (
                <SkeletonBlock key={i} width={i === lines - 1 ? lastLineWidth : "100%"} height={14} />
            ))}
        </div>
    )
}

// KPI bar skeleton (4 cards)
export function SkeletonKpiBar() {
    return (
        <div style={{ display: "flex", gap: "16px", flexWrap: "wrap", marginBottom: "32px" }}>
            {[1, 2, 3, 4].map(i => (
                <div key={i} style={{
                    flex: 1, minWidth: "140px",
                    background: "rgba(255,255,255,0.03)",
                    border: "1px solid rgba(255,255,255,0.06)",
                    borderRadius: "12px", padding: "20px 24px",
                    display: "flex", flexDirection: "column", gap: "10px"
                }}>
                    <SkeletonBlock width={32} height={32} borderRadius={8} />
                    <SkeletonBlock width="60%" height={28} />
                    <SkeletonBlock width="80%" height={13} />
                    <SkeletonBlock width="50%" height={11} />
                </div>
            ))}
        </div>
    )
}

// Chart card skeleton
export function SkeletonChart({ height = 300 }) {
    return (
        <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
            <SkeletonBlock width="40%" height={20} />
            <SkeletonBlock width="100%" height={height} borderRadius={8} />
        </div>
    )
}

// Card with lines skeleton
export function SkeletonCard({ lines = 4 }) {
    return (
        <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
            <SkeletonBlock width="50%" height={20} />
            <SkeletonText lines={lines} />
        </div>
    )
}

// Inject shimmer keyframes once
const styleEl = document.createElement("style")
styleEl.textContent = `
@keyframes shimmer {
  0%   { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}
`
document.head.appendChild(styleEl)
