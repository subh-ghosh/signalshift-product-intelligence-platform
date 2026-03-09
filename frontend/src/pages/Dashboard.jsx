import { useState, useEffect } from "react"
import api from "../services/api"

import SentimentChart from "../components/SentimentChart"
import TopIssuesChart from "../components/TopIssuesChart"
import VanguardAspectMap from "../components/VanguardAspectMap"
import SentimentStabilityChart from "../components/SentimentStabilityChart"
import TrendingChart from "../components/TrendingChart"
import ExecutiveSummary from "../components/AiSummaryCard"
import KpiBar from "../components/KpiBar"
import SignalTicker from "../components/SignalTicker"
import DiagnosticDrawer from "../components/DiagnosticDrawer"
import VanguardAlerts from "../components/VanguardAlerts"
import EmergingIssuesPanel from "../components/EmergingIssuesPanel"
import SemanticDriftPanel from "../components/SemanticDriftPanel"
import { SkeletonKpiBar, SkeletonChart, SkeletonCard } from "../components/Skeleton"
import { highlightEntities } from "../utils/highlight_utils.jsx"

// Convert "3M" → 3, "6M" → 6, "12M" → 12, "ALL" → 0
function rangeToMonths(r) {
    const map = { "3M": 3, "6M": 6, "12M": 12, "ALL": 0 }
    return map[r] ?? 0
}

// Global Timeline Selector component (pill style)
function TimelineSelector({ range, setRange }) {
    return (
        <div style={{
            display: "flex",
            alignItems: "center",
            gap: "8px",
            background: "#FFFFFF",
            border: "1px solid #E2E8F0",
            borderRadius: "30px",
            padding: "6px 10px"
        }}>
            <span style={{ fontSize: "11px", color: "#64748B", fontWeight: 700, letterSpacing: "0.05em", marginRight: 4 }}>
                TIME PERIOD
            </span>
            {["3M", "6M", "12M", "ALL"].map(r => (
                <button
                    key={r}
                    onClick={() => setRange(r)}
                    style={{
                        background: range === r ? "#EFF6FF" : "transparent",
                        color: range === r ? "#2563EB" : "#475569",
                        border: "none",
                        padding: "4px 14px",
                        borderRadius: "20px",
                        fontSize: "12px",
                        cursor: "pointer",
                        fontWeight: "bold",
                        transition: "all 0.2s",
                        boxShadow: "none" // Removed neon shadow
                    }}
                >
                    {r}
                </button>
            ))}
        </div>
    )
}

export default function Dashboard() {
    const [file, setFile] = useState(null)
    const [status, setStatus] = useState("")
    const [reviews, setReviews] = useState([])
    const [issue, setIssue] = useState("")
    const [issueKeywords, setIssueKeywords] = useState("")
    const [uploadLoading, setUploadLoading] = useState(false)
    const [chartsLoading, setChartsLoading] = useState(false)
    const [refreshKey, setRefreshKey] = useState(0)
    const [progress, setProgress] = useState({ processed: 0, total: 0, status: "idle", eta_seconds: 0 })
    const [syncStatus, setSyncStatus] = useState(null)
    const [reviewWindow, setReviewWindow] = useState("")
    const [totalInWindow, setTotalInWindow] = useState(0)
    const [kpiLoading, setKpiLoading] = useState(true)

    // ── GLOBAL RANGE STATE ──────────────────────────────────────────
    const [range, setRange] = useState("ALL")
    const limitMonths = rangeToMonths(range)

    // ── DRAWER STATE ──────────────────────────────────────────────
    const [drawer, setDrawer] = useState({ open: false, aspect: null, month: null, topic: null })
    const openDrawer = (opts) => setDrawer({ open: true, ...opts })
    const closeDrawer = () => setDrawer({ ...drawer, open: false })

    const fetchData = async () => {
        try {
            const syncRes = await api.get("/sync/status")
            setSyncStatus(syncRes.data)
        } catch (e) {
            console.error("Failed to fetch dashboard data", e)
        }
    }

    useEffect(() => {
        fetchData()
        const checkInitialStatus = async () => {
            try {
                const res = await api.get("/upload-progress")
                if (["sentiment", "processing", "topic"].includes(res.data.status)) {
                    setProgress(res.data)
                    setUploadLoading(true)
                    startPolling()
                } else if (res.data.status === "complete") {
                    setUploadLoading(false)
                    setRefreshKey(prev => prev + 1)
                    fetchData()
                    setStatus("Analysis complete!")
                    setTimeout(() => setProgress({ processed: 0, total: 0, status: "idle", eta_seconds: 0 }), 2000)
                }
            } catch (e) { console.error("Initial status check failed", e) }
        }
        checkInitialStatus()
    }, [])

    let progressInterval

    const onAnalysisComplete = (finalStatus = "Success! Analysis complete.") => {
        setUploadLoading(false)
        setRefreshKey(prev => prev + 1)
        fetchData()
        setStatus(finalStatus)
        setTimeout(() => {
            setStatus("")
            setProgress({ processed: 0, total: 0, status: "idle", eta_seconds: 0 })
        }, 3000)
    }

    const startPolling = async () => {
        if (progressInterval) clearInterval(progressInterval)
        return new Promise((resolve, reject) => {
            let failCount = 0
            progressInterval = setInterval(async () => {
                try {
                    const res = await api.get("/upload-progress")
                    setProgress(res.data)
                    failCount = 0
                    if (res.data.status === "complete" || res.data.status === "idle") {
                        clearInterval(progressInterval)
                        onAnalysisComplete(res.data.status === "complete" ? "Analysis complete!" : "")
                        resolve()
                    }
                    if (res.data.status === "error") {
                        clearInterval(progressInterval)
                        setUploadLoading(false)
                        setStatus("Analysis failed")
                        reject(new Error("Analysis failed"))
                    }
                } catch (e) {
                    failCount++
                    if (failCount > 5) {
                        clearInterval(progressInterval)
                        setUploadLoading(false)
                        setStatus("Connection lost")
                        reject(new Error("Connection lost"))
                    }
                }
            }, 1500)
        })
    }

    const handleStop = async () => {
        try {
            setStatus("Stopping analysis early...")
            await api.post("/stop-upload")
        } catch (e) { console.error("Failed to stop analysis", e) }
    }

    const handleUpload = async () => {
        if (!file) { setStatus("Please select a file"); return }
        const formData = new FormData()
        formData.append("file", file)
        try {
            setUploadLoading(true)
            setStatus("Initiating upload...")
            setIssue(""); setReviews([])
            setProgress({ processed: 0, total: 0, status: "sentiment", eta_seconds: 0 })
            await api.post("/upload-reviews", formData)
            setStatus("Upload received! Analyzing in background...")
            await startPolling()
        } catch (err) {
            console.error(err)
            setStatus("Analysis failed or connection interrupted")
            setUploadLoading(false)
        }
    }

    const handleKaggleSync = async () => {
        try {
            setUploadLoading(true)
            setStatus("Syncing Latest App Data...")
            const res = await api.post("/sync/kaggle")
            setStatus(res.data.message || "Sync started!")
            fetchData()
            await startPolling()
        } catch (err) {
            console.error(err)
            setStatus("Data Sync failed")
            setUploadLoading(false)
        }
    }

    const handleIssueClick = async (keywords) => {
        try {
            setChartsLoading(true)
            setIssue(keywords)
            const res = await api.get("/dashboard/issue-reviews", {
                params: { issue: keywords, limit_months: limitMonths }
            })
            setReviews(res.data.reviews || [])
            setIssueKeywords(res.data.keywords || "")
            setReviewWindow(res.data.window || "")
            setTotalInWindow(res.data.total_in_window || 0)
        } catch (err) {
            console.error(err)
            setReviews([])
            setIssueKeywords("")
            setReviewWindow("")
            setTotalInWindow(0)
        } finally {
            setChartsLoading(false)
        }
    }

    // Clear selected issue when range changes
    useEffect(() => {
        setReviews([])
        setIssue("")
    }, [range])

    const downloadCsv = async () => {
        try {
            setStatus(`Exporting CSV (${range === "ALL" ? "All Time" : `Last ${range}`})...`)
            const res = await api.get("/dashboard/export-csv", {
                responseType: "blob",
                params: { limit_months: limitMonths }
            })
            const url = window.URL.createObjectURL(new Blob([res.data]))
            const link = document.createElement("a")
            link.href = url
            const windowStr = range === "ALL" ? "AllTime" : range
            link.setAttribute("download", `SignalShift_Reviews_${windowStr}_${new Date().toISOString().split("T")[0]}.csv`)
            document.body.appendChild(link)
            link.click()
            link.remove()
            setStatus("CSV downloaded!")
            setTimeout(() => setStatus(""), 3000)
        } catch (e) {
            console.error("Failed to download CSV", e)
            setStatus("CSV export failed")
        }
    }

    const downloadExecutiveReport = async () => {
        try {
            setStatus(`Generating PDF (${range === "ALL" ? "All Time" : `Last ${range}`})...`)
            const res = await api.get("/dashboard/export-pdf", {
                responseType: "blob",
                params: { limit_months: limitMonths }
            })
            const url = window.URL.createObjectURL(new Blob([res.data]))
            const link = document.createElement("a")
            link.href = url
            const windowStr = range === "ALL" ? "AllTime" : range
            link.setAttribute("download", `SignalShift_Report_${windowStr}_${new Date().toISOString().split("T")[0]}.pdf`)
            document.body.appendChild(link)
            link.click()
            link.remove()
            setStatus("Report downloaded!")
            setTimeout(() => setStatus(""), 3000)
        } catch (e) {
            console.error("Failed to download PDF", e)
            setStatus("PDF Generation failed")
        }
    }

    return (
        <div style={{ minHeight: "100vh", background: "#F4F7FE", color: "#0F172A" }}>
            <SignalTicker />
            <div style={{ padding: "40px", maxWidth: "1400px", margin: "auto" }}>

                {/* ── GLOBAL TIMELINE SELECTOR & HEADER ── */}
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "24px", flexWrap: "wrap", gap: "16px" }}>
                    <div>
                        <h1 style={{ margin: 0, color: "#0F172A" }}>SignalShift Insights</h1>
                        <p style={{ margin: "4px 0 0", fontSize: "13px", color: "#64748B" }}>
                            Showing data for:&nbsp;
                            <span style={{ color: "#E50914", fontWeight: 700 }}>
                                {range === "ALL" ? "All Available Time" : `Last ${range}`}
                            </span>
                        </p>
                    </div>
                    <div style={{ display: "flex", gap: "12px", alignItems: "center", flexWrap: "wrap" }}>
                        <TimelineSelector range={range} setRange={setRange} />
                        <button className="btn-secondary" onClick={downloadCsv} style={{ height: "36px" }}>
                            📊 CSV Export ({range})
                        </button>
                        <button className="btn-primary" onClick={downloadExecutiveReport} style={{ height: "36px" }}>
                            📄 Export Report ({range})
                        </button>
                    </div>
                </div>

                {/* ── 1. TOP-LEVEL HEALTH ── */}
                <KpiBar key={`kpi-${refreshKey}-${range}`} limitMonths={limitMonths} />
                {!uploadLoading && !chartsLoading && (
                    <ExecutiveSummary key={`ai-${refreshKey}-${range}`} range={range} />
                )}

                {/* ── 2. CRITICAL ALERTS & TRENDS ── */}
                <VanguardAlerts range={range} />
                
                <div className="glass-card" style={{ marginBottom: "40px" }}>
                    <h2 style={{ marginTop: 0, color: "#0F172A" }}>Trending Topics Over Time</h2>
                    <TrendingChart key={`trending-${refreshKey}`} range={range} setRange={setRange} />
                </div>

                {/* ── 3. DEEP DIVE ANALYSIS ── */}
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "30px", marginBottom: "40px" }}>
                    <div className="glass-card">
                        <h2 style={{ marginTop: 0, color: "#0F172A" }}>Overall Customer Happiness</h2>
                        <div style={{ display: "flex", justifyContent: "center" }}>
                            <SentimentChart
                                key={`sent-${refreshKey}-${range}`}
                                limitMonths={limitMonths}
                                onSentimentClick={(s) => openDrawer({ topic: s })}
                            />
                        </div>
                    </div>
                    <div className="glass-card">
                        <h2 style={{ marginTop: 0, color: "#0F172A" }}>Top Problem Areas</h2>
                        <p style={{ fontSize: "13px", color: "#64748B", marginBottom: "20px" }}>
                            Breakdown of common complaints and where they are happening.
                        </p>
                        <VanguardAspectMap
                            range={range}
                            onAspectClick={(a) => openDrawer({ aspect: a })}
                        />
                    </div>
                </div>

                <div className="glass-card" style={{ marginBottom: "40px" }}>
                    <h2 style={{ marginTop: 0, color: "#0F172A" }}>Main Customer Complaints</h2>
                    <TopIssuesChart key={`issues-${refreshKey}-${range}`} onIssueClick={handleIssueClick} limitMonths={limitMonths} />
                </div>

                {/* ── 4. ADVANCED ANALYTICS (The Hidden Details) ── */}
                <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(350px, 1fr))", gap: "20px", marginTop: "30px", marginBottom: "40px" }}>
                    <div className="glass-card">
                        <h2 style={{ marginTop: 0, color: "#0F172A" }}>🛡️ Overall Happiness Trend</h2>
                        <p style={{ fontSize: "13px", color: "#64748B", marginBottom: "20px" }}>
                            Tracking app-wide sentiment fluctuations over time.
                        </p>
                        <SentimentStabilityChart
                            key={`stability-${refreshKey}-${range}`}
                            limitMonths={limitMonths}
                            onStabilityClick={(m) => openDrawer({ month: m })}
                        />
                    </div>
                    <div className="glass-card">
                        <h2 style={{ marginTop: 0, color: "#0F172A" }}>⚠️ Trending Topics</h2>
                        <EmergingIssuesPanel key={`emerge-${refreshKey}-${range}`} limitMonths={limitMonths} />
                    </div>
                    <div className="glass-card">
                        <h2 style={{ marginTop: 0, color: "#0F172A" }}>📈 New Issues Hiding in Old Topics</h2>
                        <SemanticDriftPanel key={`drift-${refreshKey}-${range}`} limitMonths={limitMonths} />
                    </div>
                </div>

                {/* ── 5. RAW EVIDENCE (The Proof) ── */}
                {reviews.length > 0 && (
                    <div className="glass-card" style={{ marginBottom: "40px", borderLeft: "4px solid #E50914" }}>
                        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "12px" }}>
                            <div>
                                <h2 style={{ marginTop: 0, marginBottom: "4px", color: "#0F172A" }}>What Customers are Saying</h2>
                                <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                                    <span style={{ fontSize: "12px", color: "#E50914", fontWeight: 700 }}>{issue.toUpperCase()}</span>
                                    <span style={{ width: "4px", height: "4px", borderRadius: "50%", background: "#CBD5E1" }} />
                                    <span style={{ fontSize: "12px", color: "#64748B" }}>Most relevant feedback first</span>
                                </div>
                            </div>
                            {reviewWindow && (
                                <div style={{ textAlign: "right" }}>
                                    <span style={{
                                        fontSize: "11px", fontWeight: 700, padding: "4px 12px",
                                        borderRadius: "20px", background: "#FEF2F2",
                                        border: "1px solid #FECACA", color: "#DC2626",
                                        whiteSpace: "nowrap", display: "inline-block", marginBottom: "4px"
                                    }}>
                                        🕐 {reviewWindow}
                                    </span>
                                    <div style={{ fontSize: "10px", color: "#94A3B8", fontWeight: 600 }}>UNIQUE COMMENTS ONLY</div>
                                </div>
                            )}
                        </div>

                        <div style={{ maxHeight: "800px", overflowY: "auto", display: "flex", flexDirection: "column", gap: "16px", paddingRight: "8px" }}>
                            {reviews.map((r, i) => {
                                const isEnterprise = r.user_tier === "Enterprise" || (r.value_weight && r.value_weight >= 4);
                                const isPremium = r.user_tier === "Premium" || (r.value_weight && r.value_weight >= 2);

                                return (
                                    <div key={i} style={{
                                        padding: "20px",
                                        background: "#F8FAFC",
                                        borderRadius: "12px",
                                        fontSize: "15px",
                                        lineHeight: "1.6",
                                        border: "1px solid #E2E8F0",
                                        position: "relative",
                                        transition: "transform 0.2s, background 0.2s",
                                        cursor: "default"
                                    }}
                                        onMouseEnter={(e) => e.currentTarget.style.background = "#FFFFFF"}
                                        onMouseLeave={(e) => e.currentTarget.style.background = "#F8FAFC"}
                                    >
                                        <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "12px", alignItems: "center" }}>
                                            <div style={{ display: "flex", gap: "8px", alignItems: "center" }}>
                                                {isEnterprise && (
                                                    <span style={{
                                                        fontSize: "9px", fontWeight: 900, background: "#EF4444", color: "#fff",
                                                        padding: "2px 6px", borderRadius: "4px", letterSpacing: "0.5px"
                                                    }}>ENTERPRISE</span>
                                                )}
                                                {isPremium && !isEnterprise && (
                                                    <span style={{
                                                        fontSize: "9px", fontWeight: 900, background: "#F59E0B", color: "#fff",
                                                        padding: "2px 6px", borderRadius: "4px", letterSpacing: "0.5px"
                                                    }}>PREMIUM</span>
                                                )}
                                                <span style={{ color: "#F59E0B", fontSize: "12px", fontWeight: 700 }}>
                                                    {"★".repeat(parseInt(r.score) || 0)}{"☆".repeat(5 - (parseInt(parseInt(r.score)) || 0))}
                                                </span>
                                                {r.upvotes > 0 && (
                                                    <span style={{ fontSize: "10px", color: "#64748B", fontWeight: 700, marginLeft: "4px" }}>
                                                        👍 {r.upvotes}
                                                    </span>
                                                )}
                                            </div>
                                            <div style={{ textAlign: "right" }}>
                                                <div style={{ fontSize: "11px", color: "#64748B", fontWeight: 600 }}>
                                                    {r.at ? r.at.split("T")[0] : "RECENT"}
                                                </div>
                                                {r.app_version && r.app_version !== "N/A" && (
                                                    <div style={{ fontSize: "9px", color: "#94A3B8", fontWeight: 800, marginTop: "2px" }}>
                                                        VER {r.app_version.replace("Build ", "")}
                                                    </div>
                                                )}
                                            </div>
                                        </div>

                                        <div style={{ color: "#334155", fontStyle: parseInt(r.score) <= 2 ? "italic" : "normal" }}>
                                            "{highlightEntities(r.text || "", `${issueKeywords}, slow, fast, expensive, price, crash, bug, error, login, payment, quality`)}"
                                        </div>

                                        {r.value_weight > 1 && (
                                            <div style={{
                                                marginTop: "12px", paddingTop: "12px", borderTop: "1px solid #E2E8F0",
                                                display: "flex", justifyContent: "flex-end"
                                            }}>
                                                <span style={{ fontSize: "10px", color: "#64748B", fontWeight: 700, letterSpacing: "0.5px" }}>
                                                    BUSINESS IMPORTANCE: <span style={{ color: "#DC2626" }}>{r.value_weight.toFixed(1)}x</span>
                                                </span>
                                            </div>
                                        )}
                                    </div>
                                );
                            })}
                        </div>
                    </div>
                )}

                {/* ── 6. DATA MANAGEMENT (The Admin) ── */}
                <div style={{ 
                    borderTop: "1px solid #E2E8F0", 
                    paddingTop: "40px", 
                    marginTop: "40px",
                    opacity: 0.8 // Slightly dim to indicate admin nature
                }}>
                    <div className="glass-card" style={{ marginBottom: "20px" }}>
                        <h2 style={{ marginTop: 0, color: "#0F172A" }}>Data Acquisition</h2>
                        <p style={{ fontSize: "13px", color: "#64748B", marginBottom: "20px" }}>
                            Upload new customer feedback files or sync from configured data sources.
                        </p>
                        <div style={{ display: "flex", alignItems: "center", gap: "20px", flexWrap: "wrap" }}>
                            <input type="file" onChange={(e) => setFile(e.target.files[0])} style={{ color: "#475569" }} />
                            <button className="btn-primary" onClick={handleUpload} disabled={uploadLoading}>
                                {uploadLoading ? "⏳ Analyzing..." : "Upload & Analyze"}
                            </button>
                            <span style={{ color: "#64748B" }}>OR</span>
                            <button
                                onClick={handleKaggleSync}
                                disabled={uploadLoading}
                                style={{ backgroundColor: "transparent", color: "#3B82F6", border: "1px solid #3B82F6" }}
                            >
                                🔄 Sync Latest App Data
                            </button>
                        </div>
                        {syncStatus?.last_sync && (
                            <div style={{ fontSize: "12px", color: "#64748B", marginTop: "15px" }}>
                                Last Data Refresh: <strong style={{ color: "#0F172A" }}>{new Date(syncStatus.last_sync).toLocaleDateString()}</strong>
                            </div>
                        )}
                        {status && (
                            <p style={{ marginTop: "10px", fontSize: "14px", fontWeight: "600", color: status.includes("failed") ? "#EF4444" : "#10B981" }}>
                                {status}
                            </p>
                        )}
                    </div>

                    {/* Progress Bar */}
                    {uploadLoading && progress.total > 0 && (
                        <div className="glass-card" style={{ marginBottom: "20px", border: "1px solid #E2E8F0" }}>
                            <div style={{ width: "100%", height: "8px", backgroundColor: "#E2E8F0", borderRadius: "4px", overflow: "hidden", marginBottom: "15px" }}>
                                <div style={{
                                    width: `${(progress.processed / progress.total) * 100}%`,
                                    height: "100%", backgroundColor: "#3B82F6",
                                    transition: "width 0.3s ease", boxShadow: "none"
                                }} />
                            </div>
                            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                                <span style={{ fontSize: "14px", fontWeight: "bold", color: "#0F172A" }}>
                                    {progress.status.toUpperCase()}:{" "}
                                    {progress.status === "downloading" || progress.status === "unzipping"
                                        ? `${progress.processed}%`
                                        : `${progress.processed.toLocaleString()} / ${progress.total.toLocaleString()} reviews (${Math.round((progress.processed / progress.total) * 100)}%)`}
                                </span>
                                {progress.eta_seconds > 0 && (
                                    <span style={{ fontSize: "12px", color: "#3B82F6", fontWeight: "bold" }}>
                                        ETA: {progress.eta_seconds > 60
                                            ? `${Math.floor(progress.eta_seconds / 60)}m ${progress.eta_seconds % 60}s`
                                            : `${progress.eta_seconds}s`} remaining
                                    </span>
                                )}
                            </div>
                            <button onClick={handleStop} style={{ fontSize: "10px", marginTop: "10px", color: "#64748B", background: "none", border: "none", cursor: "pointer" }}>Stop Early</button>
                        </div>
                    )}
                </div>

                <DiagnosticDrawer
                    isOpen={drawer.open}
                    onClose={closeDrawer}
                    aspect={drawer.aspect}
                    month={drawer.month}
                    topic={drawer.topic}
                />
            </div>
        </div>
    )
}