import { useState, useEffect } from "react"
import api from "../services/api"

import SentimentChart from "../components/SentimentChart"
import TopIssuesChart from "../components/TopIssuesChart"
import AspectRadarChart from "../components/AspectRadarChart"
import ResearchBenchmark from "../components/ResearchBenchmark"

export default function Dashboard() {

    const [file, setFile] = useState(null)
    const [status, setStatus] = useState("")
    const [reviews, setReviews] = useState([])
    const [issue, setIssue] = useState("")
    const [uploadLoading, setUploadLoading] = useState(false)
    const [chartsLoading, setChartsLoading] = useState(false)
    const [refreshKey, setRefreshKey] = useState(0)
    const [progress, setProgress] = useState({ processed: 0, total: 0, status: "idle", eta_seconds: 0 })
    const [syncStatus, setSyncStatus] = useState(null)
    const [alerts, setAlerts] = useState([])

    // Fetch sync status and alerts on load
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
                if (res.data.status === "sentiment" || res.data.status === "processing" || res.data.status === "topic") {
                    setProgress(res.data)
                    setUploadLoading(true)
                    startPolling()
                } else if (res.data.status === "complete") {
                    setUploadLoading(false)
                    setRefreshKey(prev => prev + 1)
                    fetchData()
                    setStatus("Analysis complete!")
                    setTimeout(() => {
                        setProgress({ processed: 0, total: 0, status: "idle", eta_seconds: 0 })
                    }, 2000)
                }
            } catch (e) {
                console.error("Initial status check failed", e)
            }
        }
        checkInitialStatus()
    }, [])

    let progressInterval;

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
        if (progressInterval) clearInterval(progressInterval);

        return new Promise((resolve, reject) => {
            let failCount = 0;
            progressInterval = setInterval(async () => {
                try {
                    const res = await api.get("/upload-progress")
                    setProgress(res.data)
                    failCount = 0;

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
                    failCount++;
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
        } catch (e) {
            console.error("Failed to stop analysis", e)
        }
    }

    const handleUpload = async () => {
        if (!file) {
            setStatus("Please select a file")
            return
        }

        const formData = new FormData()
        formData.append("file", file)

        try {
            setUploadLoading(true)
            setStatus("Initiating upload...")
            setIssue("")
            setReviews([])
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
                params: { issue: keywords }
            })
            setReviews(res.data.reviews || [])
        } catch (err) {
            console.error(err)
            setReviews([])
        } finally {
            setChartsLoading(false)
        }
    }

    const downloadExecutiveReport = async () => {
        try {
            setStatus("Generating PDF Report...")
            const res = await api.get("/dashboard/export-pdf", { responseType: 'blob' })
            const url = window.URL.createObjectURL(new Blob([res.data]))
            const link = document.createElement('a')
            link.href = url
            link.setAttribute('download', `SignalShift_Executive_Report_${new Date().toISOString().split('T')[0]}.pdf`)
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
                    marginBottom: '20px', 
                    borderLeft: '4px solid #E50914', 
                    background: 'rgba(229, 9, 20, 0.1)',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '15px'
                }}>
                    <span style={{ fontSize: '24px' }}>🚨</span>
                    <div>
                        <h3 style={{ margin: 0, color: '#E50914', fontSize: '16px' }}>CRITICAL SYSTEM ALERT</h3>
                        {alerts.map(a => (
                            <p key={a.id} style={{ margin: '5px 0 0', fontSize: '14px', color: '#fff' }}>
                                {a.message}
                            </p>
                        ))}
                    </div>
                </div>
            )}

            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '30px' }}>
                <h1>SignalShift Intelligence</h1>
                <button className="btn-primary" onClick={downloadExecutiveReport}>
                    📄 Export Global Report (PDF)
                </button>
            </div>

            {/* Research Impact Benchmark */}
            <ResearchBenchmark />

            {/* Upload Section */}
            <div className="glass-card" style={{ marginBottom: '40px' }}>
                <h2 style={{ marginTop: 0 }}>Data Acquisition</h2>
                <div style={{ display: 'flex', alignItems: 'center', gap: '20px', flexWrap: 'wrap' }}>
                    <input
                        type="file"
                        onChange={(e) => setFile(e.target.files[0])}
                    />
                    <button
                        className="btn-primary"
                        onClick={handleUpload}
                        disabled={uploadLoading}
                    >
                        {uploadLoading ? "⏳ Analyzing..." : "Upload & Analyze"}
                    </button>
                    <span style={{ color: "#666" }}>OR</span>
                    <button
                        onClick={handleKaggleSync}
                        disabled={uploadLoading}
                        style={{
                            backgroundColor: "transparent",
                            color: "#E50914",
                            border: "1px solid #E50914"
                        }}
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
                    <p style={{ marginTop: '10px', fontSize: '14px', color: status.includes('failed') ? '#E50914' : '#2E7D32' }}>
                        {status}
                    </p>
                )}
            </div>

            {uploadLoading && progress.total > 0 && (
                <div className="glass-card" style={{ marginBottom: '40px', borderColor: '#E50914' }}>
                    <div style={{
                        width: "100%",
                        height: "8px",
                        backgroundColor: "rgba(255,255,255,0.1)",
                        borderRadius: "4px",
                        overflow: "hidden",
                        marginBottom: '15px'
                    }}>
                        <div style={{
                            width: `${(progress.processed / progress.total) * 100}%`,
                            height: "100%",
                            backgroundColor: "#E50914",
                            transition: "width 0.3s ease",
                            boxShadow: "0 0 10px #E50914"
                        }} />
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <span style={{ fontSize: '14px', fontWeight: 'bold' }}>
                            {progress.status.toUpperCase()}: {progress.status === "downloading" || progress.status === "unzipping" 
                                ? `${progress.processed}%` 
                                : `${progress.processed.toLocaleString()} / ${progress.total.toLocaleString()} reviews (${Math.round((progress.processed / progress.total) * 100)}%)`}
                        </span>
                        {progress.eta_seconds > 0 && (
                            <span style={{ fontSize: '12px', color: '#E50914', fontWeight: 'bold' }}>
                                ETA: {progress.eta_seconds > 60 
                                    ? `${Math.floor(progress.eta_seconds / 60)}m ${progress.eta_seconds % 60}s` 
                                    : `${progress.eta_seconds}s`} remaining
                            </span>
                        )}
                    </div>
                    <button onClick={handleStop} style={{ fontSize: '10px', marginTop: '10px', color: '#888' }}>
                        Stop Early
                    </button>
                </div>
            )}

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '30px', marginBottom: '40px' }}>
                <div className="glass-card">
                    <h2 style={{ marginTop: 0 }}>Sentiment Overview</h2>
                    <div style={{ display: 'flex', justifyContent: 'center' }}>
                        <SentimentChart key={`sent-${refreshKey}`} />
                    </div>
                </div>

                <div className="glass-card">
                    <h2 style={{ marginTop: 0 }}>Business Intelligence (ABSA)</h2>
                    <p style={{ fontSize: '13px', color: '#888', marginBottom: '20px' }}>
                        SignalShiftBERT identifying root causes of churn.
                    </p>
                    <AspectRadarChart key={`radar-${refreshKey}`} />
                </div>
            </div>

            <div className="glass-card" style={{ marginBottom: '40px' }}>
                <h2 style={{ marginTop: 0 }}>Frequency of Top Issues</h2>
                <TopIssuesChart key={`issues-${refreshKey}`} onIssueClick={handleIssueClick} />
            </div>

            {reviews.length > 0 && (
                <div className="glass-card">
                    <h2 style={{ marginTop: 0 }}>High-Signal Evidence: {issue}</h2>
                    <p style={{ fontSize: '13px', color: '#888', marginBottom: '15px' }}>
                        Curated feedback filtered for detail, uniqueness, and business impact.
                    </p>
                    <div style={{
                        maxHeight: "400px",
                        overflowY: "auto",
                        display: 'flex',
                        flexDirection: 'column',
                        gap: '12px'
                    }}>
                        {reviews.map((r, i) => (
                            <div key={i} style={{ 
                                padding: '15px', 
                                background: 'rgba(255,255,255,0.03)', 
                                borderRadius: '8px',
                                fontSize: '14px',
                                borderLeft: '3px solid #E50914'
                            }}>
                                "{r}"
                            </div>
                        ))}
                    </div>
                </div>
            )}
        </div>
    )
}