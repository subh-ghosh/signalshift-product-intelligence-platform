import { useState } from "react"
import api from "../services/api"

import SentimentChart from "../components/SentimentChart"
import TopIssuesChart from "../components/TopIssuesChart"

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

    // Fetch sync status on load
    const fetchSyncStatus = async () => {
        try {
            const res = await api.get("/sync/status")
            setSyncStatus(res.data)
        } catch (e) {
            console.error("Failed to fetch sync status", e)
        }
    }

    // Check for active jobs on load
    useState(() => {
        const checkInitialStatus = async () => {
            fetchSyncStatus()
            try {
                const res = await api.get("/upload-progress")
                if (res.data.status === "sentiment" || res.data.status === "processing") {
                    setProgress(res.data)
                    setUploadLoading(true)
                    startPolling()
                } else if (res.data.status === "complete") {
                    // If a job was completed while the user was away, update state
                    setUploadLoading(false)
                    setRefreshKey(prev => prev + 1)
                    fetchSyncStatus()
                    setStatus("Analysis complete!")
                    // Clear progress after short delay
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
        fetchSyncStatus()
        setStatus(finalStatus)
        // Clear status and progress after a while
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
            fetchSyncStatus()
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


    return (

        <div style={{ padding: "40px", maxWidth: "1200px", margin: "auto" }}>

            <h1>Netflix Dashboard</h1>

            {/* Upload Section */}

            <h2>Upload Latest Reviews</h2>

            <input
                type="file"
                onChange={(e) => setFile(e.target.files[0])}
            />

            <button
                onClick={handleUpload}
                disabled={uploadLoading}
                style={{
                    marginLeft: "10px",
                    padding: "8px 16px",
                    backgroundColor: uploadLoading ? "#ccc" : "#E50914",
                    color: "white",
                    border: "none",
                    borderRadius: "4px",
                    cursor: uploadLoading ? "not-allowed" : "pointer",
                    fontWeight: "bold"
                }}
            >
                {uploadLoading ? "⏳ Analyzing & Extracting Issues..." : "Upload & Analyze"}
            </button>

            <span style={{ margin: "0 15px", color: "#666" }}>OR</span>

            <button
                onClick={handleKaggleSync}
                disabled={uploadLoading}
                style={{
                    padding: "8px 16px",
                    backgroundColor: "transparent",
                    color: uploadLoading ? "#666" : "#E50914",
                    border: `1px solid ${uploadLoading ? "#ccc" : "#E50914"}`,
                    borderRadius: "4px",
                    cursor: uploadLoading ? "not-allowed" : "pointer",
                    fontWeight: "bold"
                }}
            >
                🔄 Sync Latest from Kaggle
            </button>

            {syncStatus?.last_sync && (
                <div style={{ fontSize: "12px", color: "#666", marginTop: "10px" }}>
                    Last Kaggle Sync: <strong>{new Date(syncStatus.last_sync).toLocaleString()}</strong>
                </div>
            )}

            {uploadLoading && progress.total > 0 && (
                <div style={{ marginTop: "20px", width: "100%", maxWidth: "500px" }}>
                    <div style={{
                        width: "100%",
                        height: "20px",
                        backgroundColor: "#eee",
                        borderRadius: "10px",
                        overflow: "hidden",
                        border: "1px solid #ddd"
                    }}>
                        <div style={{
                            width: `${(progress.processed / progress.total) * 100}%`,
                            height: "100%",
                            backgroundColor: "#E50914",
                            transition: "width 0.3s ease"
                        }} />
                    </div>
                    <p style={{ fontSize: "14px", marginTop: "5px", color: "#666", display: "flex", justifyContent: "space-between" }}>
                        <span>
                            <strong>
                                {progress.status === "downloading" ? "Step 0/3: Downloading Dataset" :
                                    progress.status === "unzipping" ? "Step 0/3: Unzipping Dataset" :
                                        progress.status === "sentiment" ? "Step 1/2: Sentiment Analysis" :
                                            "Step 2/2: Extracting Issues"}
                            </strong>:
                            {' '}{progress.status === "downloading" || progress.status === "unzipping"
                                ? `${progress.processed}%`
                                : `${progress.processed.toLocaleString()} / ${progress.total.toLocaleString()} ${progress.status === "sentiment" ? "reviews" : "negative reviews"}`}
                            ({Math.round((progress.processed / progress.total) * 100)}%)
                        </span>
                        {uploadLoading && progress.eta_seconds > 0 && (
                            <span style={{ fontWeight: "bold", color: "#E50914" }}>
                                ETA: {progress.eta_seconds > 60
                                    ? `${Math.floor(progress.eta_seconds / 60)}m ${progress.eta_seconds % 60}s`
                                    : `${progress.eta_seconds}s`} remaining
                            </span>
                        )}
                    </p>
                    <div style={{ display: "flex", gap: "10px", alignItems: "center", marginTop: "10px" }}>
                        <button
                            onClick={handleStop}
                            style={{
                                padding: "4px 12px",
                                backgroundColor: "transparent",
                                color: "#E50914",
                                border: "1px solid #E50914",
                                borderRadius: "4px",
                                cursor: "pointer",
                                fontSize: "12px",
                                fontWeight: "bold"
                            }}
                        >
                            🛑 Stop Early
                        </button>
                        <span style={{ fontSize: "12px", color: "#999" }}>
                            (Dashboard will show results processed so far)
                        </span>
                    </div>
                </div>
            )}

            {status && (
                <p style={{
                    marginTop: "10px",
                    fontWeight: "500",
                    color: status.includes("failed") ? "red" : "#2E7D32"
                }}>
                    {status}
                </p>
            )}

            <hr />

            {/* Sentiment Chart */}

            <h2>Sentiment Distribution</h2>

            <SentimentChart key={`sent-${refreshKey}`} />

            <hr />

            {/* Top Issues */}

            <h2>Top Issues</h2>

            <TopIssuesChart key={`issues-${refreshKey}`} onIssueClick={handleIssueClick} />

            <hr />

            {/* Reviews */}

            {chartsLoading && <p>Loading reviews...</p>}

            {reviews.length > 0 && (

                <div>

                    <h3>Reviews for: {issue}</h3>

                    <ul style={{
                        maxHeight: "300px",
                        overflowY: "auto",
                        border: "1px solid #ddd",
                        padding: "10px"
                    }}>

                        {reviews.map((r, i) => (
                            <li key={i} style={{ marginBottom: "10px" }}>
                                {r}
                            </li>
                        ))}

                    </ul>

                </div>

            )}

        </div>

    )
}