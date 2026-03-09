import { useEffect, useState, useRef } from "react"

// Clean Light Theme animated shimmer for loading states
function SkeletonBlock({ width = "100%", height = 16, borderRadius = 6, style = {} }) {
    return (
        <div style={{
            width,
            height,
            borderRadius,
            // Soft light-gray slate gradient
            background: "linear-gradient(90deg, #F1F5F9 25%, #E2E8F0 50%, #F1F5F9 75%)",
            backgroundSize: "200% 100%",
            animation: "shimmer 1.5s infinite linear",
            ...style
        }} />
    )
}

// Multi-line text skeleton
export function SkeletonText({ lines = 3, lastLineWidth = "70%" }) {
    return (
        <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
            {Array.from({ length: lines }).map((_, i) => (
                <SkeletonBlock key={i} width={i === lines - 1 ? lastLineWidth : "100%"} height={14} />
            ))}
        </div>
    )
}

// KPI bar skeleton (4 cards) updated to match the new vertical Light Theme layout
export function SkeletonKpiBar() {
    return (
        <div style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))",
            gap: "24px",
            marginBottom: "32px",
            width: "100%"
        }}>
            {[1, 2, 3, 4].map(i => (
                <div key={i} className="glass-card" style={{
                    display: "flex",
                    flexDirection: "column",
                    padding: "24px",
                    gap: "12px"
                }}>
                    {/* Top Row: Label and Icon */}
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                        <SkeletonBlock width="45%" height={16} />
                        <SkeletonBlock width={36} height={36} borderRadius={10} />
                    </div>

                    {/* Middle Row: Primary Value */}
                    <SkeletonBlock width="60%" height={32} style={{ marginTop: "4px" }} />

                    {/* Bottom Row: Delta & Subtext */}
                    <div style={{ display: "flex", alignItems: "center", gap: "10px", marginTop: "4px" }}>
                        <SkeletonBlock width="25%" height={24} borderRadius={6} />
                        <SkeletonBlock width="40%" height={12} />
                    </div>
                </div>
            ))}
        </div>
    )
}

// Chart card skeleton
export function SkeletonChart({ height = 300 }) {
    return (
        <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
            <SkeletonBlock width="35%" height={22} />
            <SkeletonBlock width="100%" height={height} borderRadius={12} />
        </div>
    )
}

// Card with lines skeleton
export function SkeletonCard({ lines = 4 }) {
    return (
        <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
            <SkeletonBlock width="40%" height={22} />
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