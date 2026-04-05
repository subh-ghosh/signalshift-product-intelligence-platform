import { useState, useEffect, useRef, useCallback } from "react"
import api from "../services/api"

import TopIssuesChart from "../components/TopIssuesChart"
import KpiBar from "../components/KpiBar"
import DiagnosticDrawer from "../components/DiagnosticDrawer"
import AppShell from "../components/AppShell"

function getProgressStage(status) {
  if (!status) return "Working"

  if (status === "downloading") return "Downloading dataset"
  if (status === "unzipping") return "Preparing files"
  if (status === "download_complete") return "Download complete"
  if (status === "sentiment") return "Running sentiment model"
  if (status === "stopping") return "Stopping early"
  if (status === "complete") return "Analysis complete"
  if (status === "error") return "Analysis failed"
  if (status.startsWith("Analyzing topics")) return "Finding issue categories"
  if (status === "analyzing") return "Finding issue categories"

  return status
}

export default function Dashboard() {
  const [file, setFile] = useState(null)
  const [status, setStatus] = useState("")
  const [issueKeywords, setIssueKeywords] = useState("")
  const [uploadLoading, setUploadLoading] = useState(false)
  const [chartsLoading, setChartsLoading] = useState(false)
  const [refreshKey, setRefreshKey] = useState(0)
  const [progress, setProgress] = useState({ processed: 0, total: 0, status: "idle", eta_seconds: 0 })

  const [drawer, setDrawer] = useState({
    open: false,
    aspect: null,
    month: null,
    topic: null,
    items: null,
    title: "",
    subtitle: "",
    keywords: "",
  })
  const openDrawer = (opts) => setDrawer({ open: true, ...opts })
  const closeDrawer = () => setDrawer((current) => ({
    ...current,
    open: false,
    items: null,
    title: "",
    subtitle: "",
    keywords: "",
  }))

  const progressInterval = useRef(null)
  useEffect(() => () => {
    if (progressInterval.current) clearInterval(progressInterval.current)
  }, [])

  const onAnalysisComplete = useCallback((finalStatus = "Success! Analysis complete.") => {
    setUploadLoading(false)
    setRefreshKey((prev) => prev + 1)
    setStatus(finalStatus)
    setTimeout(() => {
      setStatus("")
      setProgress({ processed: 0, total: 0, status: "idle", eta_seconds: 0 })
    }, 3000)
  }, [])

  const startPolling = useCallback(async () => {
    if (progressInterval.current) clearInterval(progressInterval.current)
    return new Promise((resolve, reject) => {
      let failCount = 0
      progressInterval.current = setInterval(async () => {
        try {
          const res = await api.get("/upload-progress")
          setProgress(res.data)
          failCount = 0

          if (res.data.status === "complete") {
            clearInterval(progressInterval.current)
            onAnalysisComplete("Analysis complete!")
            resolve()
          } else if (res.data.status === "idle" && !uploadLoading) {
             // Stay idle if we haven't started anything
             clearInterval(progressInterval.current)
             resolve()
          }

          if (res.data.status === "error") {
            clearInterval(progressInterval.current)
            setUploadLoading(false)
            setStatus("Analysis failed")
            reject(new Error("Analysis failed"))
          }
        } catch {
          failCount += 1
          if (failCount > 5) {
            clearInterval(progressInterval.current)
            setUploadLoading(false)
            setStatus("Connection lost")
            reject(new Error("Connection lost"))
          }
        }
      }, 1500)
    })
  }, [onAnalysisComplete])

  useEffect(() => {
    const checkInitialStatus = async () => {
      try {
        const res = await api.get("/upload-progress")
        if (["sentiment", "processing", "topic", "downloading", "unzipping", "download_complete"].includes(res.data.status)) {
          setProgress(res.data)
          setUploadLoading(true)
          startPolling()
        } else if (res.data.status === "complete") {
          setUploadLoading(false)
          setRefreshKey((prev) => prev + 1)
          setStatus("Analysis complete!")
          setTimeout(() => setProgress({ processed: 0, total: 0, status: "idle", eta_seconds: 0 }), 2000)
        }
      } catch (error) {
        console.error("Initial status check failed", error)
      }
    }

    checkInitialStatus()
  }, [startPolling])

  const handleStop = async () => {
    try {
      setStatus("Stopping analysis early...")
      await api.post("/stop-upload")
    } catch (error) {
      console.error("Failed to stop analysis", error)
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
      setProgress({ processed: 0, total: 0, status: "sentiment", eta_seconds: 0 })
      await api.post("/upload-reviews", formData)
      setStatus("Upload received! Analyzing in background...")
      await startPolling()
    } catch (error) {
      console.error(error)
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
      await startPolling()
    } catch (error) {
      console.error(error)
      setStatus("Data Sync failed")
      setUploadLoading(false)
    }
  }

  const handleIssueClick = async (keywords) => {
    try {
      setChartsLoading(true)
      const res = await api.get("/dashboard/issue-reviews", {
        params: { issue: keywords },
      })
      const nextReviews = res.data.reviews || []
      const nextKeywords = res.data.keywords || ""
      const nextWindow = res.data.window || ""
      const nextTotal = res.data.total_in_window || 0
      setIssueKeywords(nextKeywords)
      setDrawer({
        open: true,
        aspect: null,
        month: null,
        topic: null,
        items: nextReviews,
        title: keywords,
        subtitle: nextWindow || `${nextTotal.toLocaleString()} comments`,
        keywords: nextKeywords,
      })
    } catch (error) {
      console.error(error)
      setIssueKeywords("")
    } finally {
      setChartsLoading(false)
    }
  }

  const handleAlertClick = async (alert) => {
    if (!alert) return

    if (alert.link?.linked_to) {
      await handleIssueClick(alert.link.linked_to)
      return
    }

    if (alert.type === "ASPECT_DOMINANCE") {
      openDrawer({
        aspect: alert.category,
        title: alert.category,
        subtitle: "Highlighted product area",
      })
      return
    }

    await handleIssueClick(alert.category)
  }

  const downloadCsv = async () => {
    try {
      setStatus("Exporting CSV (All Time)...")
      const res = await api.get("/dashboard/export-csv", {
        responseType: "blob",
      })
      const url = window.URL.createObjectURL(new Blob([res.data]))
      const link = document.createElement("a")
      link.href = url
      link.setAttribute("download", `SignalShift_Reviews_AllTime_${new Date().toISOString().split("T")[0]}.csv`)
      document.body.appendChild(link)
      link.click()
      link.remove()
      setTimeout(() => window.URL.revokeObjectURL(url), 100)
      setStatus("CSV downloaded!")
      setTimeout(() => setStatus(""), 3000)
    } catch (error) {
      console.error("Failed to download CSV", error)
      setStatus("CSV export failed")
    }
  }

  const downloadExecutiveReport = async () => {
    try {
      setStatus("Generating PDF (All Time)...")
      const res = await api.get("/dashboard/export-pdf", {
        responseType: "blob",
      })
      const url = window.URL.createObjectURL(new Blob([res.data]))
      const link = document.createElement("a")
      link.href = url
      link.setAttribute("download", `SignalShift_Report_AllTime_${new Date().toISOString().split("T")[0]}.pdf`)
      document.body.appendChild(link)
      link.click()
      link.remove()
      setTimeout(() => window.URL.revokeObjectURL(url), 100)
      setStatus("Report downloaded!")
      setTimeout(() => setStatus(""), 3000)
    } catch (error) {
      console.error("Failed to download PDF", error)
      setStatus("PDF Generation failed")
    }
  }

  const progressPct = progress.total > 0 ? Math.round((progress.processed / progress.total) * 100) : 0
  const progressStage = getProgressStage(progress.status)

  return (
    <AppShell
      activePath="/dashboard"
      title="SignalShift Insights"
      subtitle=""
      searchPlaceholder="Search issues, categories, or evidence..."
      shellClassName="app-shell--dashboard"
    >
      <div className="dashboard-workspace">


        <section className="route-frame dashboard-overview">
          <div className="dashboard-hero-card">
              <div className="dashboard-stage__intro">
                <span className="eyebrow">Issue Intelligence</span>
                <h1>SignalShift Discovery</h1>
                <div className="dashboard-stage__meta">
                  <span className="tag">Bug Discovery Center</span>
                  {status && (
                    <span className={`status-text ${status.toLowerCase().includes("fail") ? "is-error" : "is-success"}`}>
                      {status}
                    </span>
                  )}
                </div>
                {uploadLoading && progress.total > 0 && (
                  <div className="discovery-progress">
                    <div className="discovery-progress__bar">
                      <div 
                        className="discovery-progress__fill" 
                        style={{ width: `${(progress.processed / progress.total) * 100}%` }}
                      ></div>
                    </div>
                    <div className="discovery-progress__meta">
                      <span>{progressStage}</span>
                      <span>{progressPct}%</span>
                    </div>
                  </div>
                )}
              </div>

              <div className="dashboard-hero-gridfill" aria-hidden="true">
                <div className="dashboard-hero-gridfill__rail dashboard-hero-gridfill__rail--tall" />
                <div className="dashboard-hero-gridfill__rail dashboard-hero-gridfill__rail--mid" />
                <div className="dashboard-hero-gridfill__rail dashboard-hero-gridfill__rail--short" />
                <div className="dashboard-hero-gridfill__rail dashboard-hero-gridfill__rail--wide" />
              </div>
            </div>

            <div className="dashboard-side-stack">
            <div className="dashboard-actions-card">
              <div className="dashboard-actions__header">
                <div>
                  <h3>Workspace Actions</h3>
                </div>
                <span className="tag tag--warm">Live Controls</span>
              </div>

              <div className="workspace-actions">
                <section className="workspace-actions__group">
                  <div className="workspace-actions__group-head">
                    <div>
                      <h4>Issue Intelligence</h4>
                      <p>Holistic discovery across all historical review data.</p>
                    </div>
                  </div>
                </section>



                <section className="workspace-actions__group workspace-actions__group--ingestion">
                  <div className="workspace-actions__group-head">
                    <div>
                      <h4>Data Ingestion</h4>
                      <p>Pick a fresh review file or refresh the latest dataset from source.</p>
                    </div>
                    {uploadLoading && (
                      <span className="workspace-actions__badge workspace-actions__badge--live">In progress</span>
                    )}
                  </div>

                  <div className="workspace-upload-block">
                    <label className="dashboard-file-input workspace-upload-block__picker">
                      <span className="workspace-upload-block__picker-label">Review file</span>
                      <strong>{file ? file.name : "Choose file"}</strong>
                      <input type="file" onChange={(e) => setFile(e.target.files[0])} />
                    </label>

                    <div className="workspace-upload-block__actions">
                      <button className="btn-primary" onClick={handleUpload} disabled={uploadLoading}>
                        {uploadLoading ? "Analyzing..." : "Upload"}
                      </button>
                      <button className="btn-tertiary" onClick={handleKaggleSync} disabled={uploadLoading}>
                        Sync latest
                      </button>
                      {uploadLoading && (
                        <button className="btn-secondary" onClick={handleStop}>
                          Stop
                        </button>
                      )}
                    </div>

                    <div className="workspace-upload-block__status">
                      {file ? `Selected: ${file.name}` : "No local review file selected yet."}
                    </div>
                  </div>
                </section>
              </div>

            </div>
          </div>
        </section>

        <section className="route-frame dashboard-section dashboard-section--problem">
          <div className="glass-card dashboard-panel dashboard-panel--wide">
            <div className="card-header">
              <div className="card-heading">
                <h2>Top Negative Issues</h2>
              </div>
            </div>
            <div className="dashboard-problem-layout">
                <TopIssuesChart key={`issues-${refreshKey}`} onIssueClick={handleIssueClick} />
            </div>
          </div>
        </section>

        <DiagnosticDrawer
          isOpen={drawer.open}
          onClose={closeDrawer}
          aspect={drawer.aspect}
          month={drawer.month}
          topic={drawer.topic}
          items={drawer.items}
          title={drawer.title}
          subtitle={drawer.subtitle}
          keywordsString={drawer.keywords || issueKeywords}
        />
      </div>
    </AppShell>
  )
}
