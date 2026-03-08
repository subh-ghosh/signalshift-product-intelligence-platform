import { useState, useEffect } from "react"
import api from "../services/api"

import SentimentChart from "../components/SentimentChart"
import TopIssuesChart from "../components/TopIssuesChart"
import AspectRadarChart from "../components/AspectRadarChart"
import TrendingChart from "../components/TrendingChart"
import AiSummaryCard from "../components/AiSummaryCard"
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
            background: "rgba(255,255,255,0.04)",
            border: "1px solid rgba(255,255,255,0.1)",
            borderRadius: "30px",
            padding: "6px 10px"
        }}>
            <span style={{ fontSize: "11px", color: "#666", fontWeight: 700, letterSpacing: "0.05em", marginRight: 4 }}>
                WINDOW
            </span>
            {["3M", "6M", "12M", "ALL"].map(r => (
                <button
                    key={r}
                    onClick={() => setRange(r)}
                    style={{
                        background: range === r ? "#E50914" : "transparent",
                        color: range === r ? "#fff" : "#aaa",
                        border: "none",
                        padding: "4px 14px",
                        borderRadius: "20px",
                        fontSize: "12px",
                        cursor: "pointer",
                        fontWeight: "bold",
                        transition: "all 0.2s",
                        boxShadow: range === r ? "0 0 8px rgba(229,9,20,0.4)" : "none"
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
    const [alerts, setAlerts] = useState([])
    
    // ── GLOBAL RANGE STATE ──────────────────────────────────────────
    const [range, setRange] = useState("ALL")
    const limitMonths = rangeToMonths(range)
    // ───────────────────────────────────────────────────────────────

    const fetchData = async () => {
        try {
            const [syncRes, alertRes] = await Promise.all([
                api.get("/sync/status"),
                api.get("/dashboard/alerts")
            ])
            setSyncStatus(syncRes.data)
            setAlerts(alertRes.data.alerts || [])
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
                        reject(new Error("AI analysis failed"))
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
            setStatus("Connecting to Kaggle...")
            const res = await api.post("/sync/kaggle")
            setStatus(res.data.message || "Sync started!")
            fetchData()
            await startPolling()
        } catch (err) {
            console.error(err)
            setStatus("Kaggle Sync failed")
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
        } catch (err) {
            console.error(err)
            setReviews([])
            setIssueKeywords("")
        } finally {
            setChartsLoading(false)
        }
    }

    // Clear selected issue when range changes
    useEffect(() => {
        setReviews([])
        setIssue("")
    }, [range])

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
        <div style={{ padding: "40px", maxWidth: "1400px", margin: "auto" }}>

            {/* Critical Alert Bar */}
            {alerts.length > 0 && (
                <div className="glass-card" style={{
                    marginBottom: "20px",
                    borderLeft: "4px solid #E50914",
                    background: "rgba(229, 9, 20, 0.1)",
                    display: "flex", alignItems: "center", gap: "15px"
                }}>
                    <span style={{ fontSize: "24px" }}>🚨</span>
                    <div>
                        <h3 style={{ margin: 0, color: "#E50914", fontSize: "16px" }}>CRITICAL SYSTEM ALERT</h3>
                        {alerts.map(a => (
                            <p key={a.id} style={{ margin: "5px 0 0", fontSize: "14px", color: "#fff" }}>{a.message}</p>
                        ))}
                    </div>
                </div>
            )}

            {/* ── HEADER with global selector ────────────────────────────── */}
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "30px", flexWrap: "wrap", gap: "16px" }}>
                <div>
                    <h1 style={{ margin: 0 }}>SignalShift Intelligence</h1>
                    <p style={{ margin: "4px 0 0", fontSize: "13px", color: "#666" }}>
                        Showing data for:&nbsp;
                        <span style={{ color: "#E50914", fontWeight: 700 }}>
                            {range === "ALL" ? "All Available Time" : `Last ${range}`}
                        </span>
                    </p>
                </div>
                <div style={{ display: "flex", gap: "12px", alignItems: "center", flexWrap: "wrap" }}>
                    {/* 🌐 GLOBAL TIMELINE SELECTOR */}
                    <TimelineSelector range={range} setRange={setRange} />
                    <button className="btn-primary" onClick={downloadExecutiveReport}>
                        📄 Export Report ({range})
                    </button>
                </div>
            </div>

            {/* Upload Section */}
            <div className="glass-card" style={{ marginBottom: "40px" }}>
                <h2 style={{ marginTop: 0 }}>Data Acquisition</h2>
                <div style={{ display: "flex", alignItems: "center", gap: "20px", flexWrap: "wrap" }}>
                    <input type="file" onChange={(e) => setFile(e.target.files[0])} />
                    <button className="btn-primary" onClick={handleUpload} disabled={uploadLoading}>
                        {uploadLoading ? "⏳ Analyzing..." : "Upload & Analyze"}
                    </button>
                    <span style={{ color: "#666" }}>OR</span>
                    <button
                        onClick={handleKaggleSync}
                        disabled={uploadLoading}
                        style={{ backgroundColor: "transparent", color: "#E50914", border: "1px solid #E50914" }}
                    >
                        🔄 Sync Kaggle Dataset
                    </button>
                </div>
                {syncStatus?.last_sync && (
                    <div style={{ fontSize: "12px", color: "#666", marginTop: "15px" }}>
                        Active Database Version: <strong>{new Date(syncStatus.last_sync).toLocaleDateString()}</strong>
                    </div>
                )}
                {status && (
                    <p style={{ marginTop: "10px", fontSize: "14px", color: status.includes("failed") ? "#E50914" : "#2E7D32" }}>
                        {status}
                    </p>
                )}
            </div>

            {/* Progress Bar */}
            {uploadLoading && progress.total > 0 && (
                <div className="glass-card" style={{ marginBottom: "40px", borderColor: "#E50914" }}>
                    <div style={{ width: "100%", height: "8px", backgroundColor: "rgba(255,255,255,0.1)", borderRadius: "4px", overflow: "hidden", marginBottom: "15px" }}>
                        <div style={{
                            width: `${(progress.processed / progress.total) * 100}%`,
                            height: "100%", backgroundColor: "#E50914",
                            transition: "width 0.3s ease", boxShadow: "0 0 10px #E50914"
                        }} />
                    </div>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                        <span style={{ fontSize: "14px", fontWeight: "bold" }}>
                            {progress.status.toUpperCase()}:{" "}
                            {progress.status === "downloading" || progress.status === "unzipping"
                                ? `${progress.processed}%`
                                : `${progress.processed.toLocaleString()} / ${progress.total.toLocaleString()} reviews (${Math.round((progress.processed / progress.total) * 100)}%)`}
                        </span>
                        {progress.eta_seconds > 0 && (
                            <span style={{ fontSize: "12px", color: "#E50914", fontWeight: "bold" }}>
                                ETA: {progress.eta_seconds > 60
                                    ? `${Math.floor(progress.eta_seconds / 60)}m ${progress.eta_seconds % 60}s`
                                    : `${progress.eta_seconds}s`} remaining
                            </span>
                        )}
                    </div>
                    <button onClick={handleStop} style={{ fontSize: "10px", marginTop: "10px", color: "#888" }}>Stop Early</button>
                </div>
            )}

            {/* Trending Issues */}
            <div className="glass-card" style={{ marginBottom: "40px" }}>
                <h2 style={{ marginTop: 0 }}>Trending Issues (Time-Series)</h2>
                <TrendingChart key={`trending-${refreshKey}`} range={range} setRange={setRange} />
            </div>

            {/* AI Summary */}
            {!uploadLoading && !chartsLoading && (
                <AiSummaryCard key={`ai-${refreshKey}-${range}`} range={range} />
            )}

            {/* Sentiment + ABSA */}
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "30px", marginBottom: "40px" }}>
                <div className="glass-card">
                    <h2 style={{ marginTop: 0 }}>Sentiment Overview</h2>
                    <div style={{ display: "flex", justifyContent: "center" }}>
                        <SentimentChart key={`sent-${refreshKey}-${range}`} limitMonths={limitMonths} />
                    </div>
                </div>
                <div className="glass-card">
                    <h2 style={{ marginTop: 0 }}>Business Intelligence (ABSA)</h2>
                    <p style={{ fontSize: "13px", color: "#888", marginBottom: "20px" }}>
                        Root causes of churn — scaled to selected time window.
                    </p>
                    <AspectRadarChart key={`radar-${refreshKey}-${range}`} limitMonths={limitMonths} />
                </div>
            </div>

            {/* Top Issues */}
            <div className="glass-card" style={{ marginBottom: "40px" }}>
                <h2 style={{ marginTop: 0 }}>Frequency of Top Issues</h2>
                <TopIssuesChart key={`issues-${refreshKey}-${range}`} onIssueClick={handleIssueClick} limitMonths={limitMonths} />
            </div>

            {/* Evidence Reviews */}
            {reviews.length > 0 && (
                <div className="glass-card">
                    <h2 style={{ marginTop: 0 }}>High-Signal Evidence: {issue}</h2>
                    <p style={{ fontSize: "13px", color: "#888", marginBottom: "15px" }}>
                        Curated feedback filtered for detail, uniqueness, and business impact.
                    </p>
                    <div style={{ maxHeight: "400px", overflowY: "auto", display: "flex", flexDirection: "column", gap: "12px" }}>
                        {reviews.map((r, i) => (
                            <div key={i} style={{
                                padding: "15px",
                                background: "rgba(255,255,255,0.03)",
                                borderRadius: "8px",
                                fontSize: "14px",
                                borderLeft: "3px solid #E50914"
                            }}>
                                "{highlightEntities(r, issueKeywords)}"
                            </div>
                        ))}
                    </div>
                </div>
            )}
        </div>
    )
}