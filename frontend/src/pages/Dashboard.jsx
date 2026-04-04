import { useState, useEffect, useRef, useCallback } from "react"
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
import AppShell from "../components/AppShell"

function rangeToMonths(r) {
  const map = { "3M": 3, "6M": 6, "12M": 12, "ALL": 0 }
  return map[r] ?? 0
}

function TimelineSelector({ range, setRange }) {
  return (
    <div className="toolbar-group" role="group" aria-label="Time period">
      {["3M", "6M", "12M", "ALL"].map((option) => (
        <button
          key={option}
          className={`pill-button ${range === option ? "is-active" : ""}`.trim()}
          onClick={() => setRange(option)}
        >
          {option}
        </button>
      ))}
    </div>
  )
}

export default function Dashboard() {
  const [file, setFile] = useState(null)
  const [status, setStatus] = useState("")
  const [issueKeywords, setIssueKeywords] = useState("")
  const [uploadLoading, setUploadLoading] = useState(false)
  const [chartsLoading, setChartsLoading] = useState(false)
  const [refreshKey, setRefreshKey] = useState(0)
  const [progress, setProgress] = useState({ processed: 0, total: 0, status: "idle", eta_seconds: 0 })

  const [range, setRange] = useState("ALL")
  const limitMonths = rangeToMonths(range)

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

          if (res.data.status === "complete" || res.data.status === "idle") {
            clearInterval(progressInterval.current)
            onAnalysisComplete(res.data.status === "complete" ? "Analysis complete!" : "")
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
        if (["sentiment", "processing", "topic"].includes(res.data.status)) {
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
        params: { issue: keywords, limit_months: limitMonths },
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
      setStatus(`Exporting CSV (${range === "ALL" ? "All Time" : `Last ${range}`})...`)
      const res = await api.get("/dashboard/export-csv", {
        responseType: "blob",
        params: { limit_months: limitMonths },
      })
      const url = window.URL.createObjectURL(new Blob([res.data]))
      const link = document.createElement("a")
      link.href = url
      const windowStr = range === "ALL" ? "AllTime" : range
      link.setAttribute("download", `SignalShift_Reviews_${windowStr}_${new Date().toISOString().split("T")[0]}.csv`)
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
      setStatus(`Generating PDF (${range === "ALL" ? "All Time" : `Last ${range}`})...`)
      const res = await api.get("/dashboard/export-pdf", {
        responseType: "blob",
        params: { limit_months: limitMonths },
      })
      const url = window.URL.createObjectURL(new Blob([res.data]))
      const link = document.createElement("a")
      link.href = url
      const windowStr = range === "ALL" ? "AllTime" : range
      link.setAttribute("download", `SignalShift_Report_${windowStr}_${new Date().toISOString().split("T")[0]}.pdf`)
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

  return (
    <AppShell
      activePath="/dashboard"
      title="SignalShift Insights"
      subtitle=""
      searchPlaceholder="Search issues, categories, or evidence..."
      shellClassName="app-shell--dashboard"
    >
      <div className="dashboard-workspace">
        <div className="dashboard-ticker-card">
          <SignalTicker />
        </div>

        <section className="route-frame dashboard-overview">
          <div className="dashboard-hero-card">
            <div className="dashboard-hero-content">
              <div className="dashboard-stage__intro">
                <span className="eyebrow">Executive Workspace</span>
                <h1>SignalShift Insights</h1>
                <div className="dashboard-stage__meta">
                  <span className="tag">Analysis Center</span>
                  <span className="muted-note">{range === "ALL" ? "All-time review window" : `Active window: last ${range}`}</span>
                  {status && (
                    <span className={`status-text ${status.toLowerCase().includes("fail") ? "is-error" : "is-success"}`}>
                      {status}
                    </span>
                  )}
                </div>
              </div>

              {uploadLoading && progress.total > 0 && (
                <div className="glass-card dashboard-progress-card">
                  <div className="progress-shell">
                    <div className="progress-bar">
                      <div className="progress-bar__fill" style={{ width: `${progressPct}%` }} />
                    </div>
                    <div style={{ display: "flex", justifyContent: "space-between", gap: 12, flexWrap: "wrap" }}>
                      <span className="status-text">
                        {progress.status === "downloading" || progress.status === "unzipping"
                          ? `${progress.processed}%`
                          : `${progress.processed.toLocaleString()} / ${progress.total.toLocaleString()} reviews (${progressPct}%)`}
                      </span>
                      {progress.eta_seconds > 0 && (
                        <span className="muted-note">
                          ETA {progress.eta_seconds > 60
                            ? `${Math.floor(progress.eta_seconds / 60)}m ${progress.eta_seconds % 60}s`
                            : `${progress.eta_seconds}s`}
                        </span>
                      )}
                    </div>
                  </div>
                </div>
              )}

              <KpiBar key={`kpi-${refreshKey}-${range}`} limitMonths={limitMonths} />

              <div className="dashboard-hero-gridfill" aria-hidden="true">
                <div className="dashboard-hero-gridfill__rail dashboard-hero-gridfill__rail--tall" />
                <div className="dashboard-hero-gridfill__rail dashboard-hero-gridfill__rail--mid" />
                <div className="dashboard-hero-gridfill__rail dashboard-hero-gridfill__rail--short" />
                <div className="dashboard-hero-gridfill__rail dashboard-hero-gridfill__rail--wide" />
              </div>
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
                      <h4>Time Range</h4>
                      <p>Control the active analysis window for this workspace.</p>
                    </div>
                    <span className="workspace-actions__badge">{range === "ALL" ? "All Time" : `Last ${range}`}</span>
                  </div>
                  <div className="dashboard-toolbar dashboard-toolbar--premium">
                    <TimelineSelector range={range} setRange={setRange} />
                  </div>
                </section>

                <section className="workspace-actions__group workspace-actions__group--exports">
                  <div className="workspace-actions__group-head">
                    <div>
                      <h4>Exports</h4>
                      <p>Download the current review window as a CSV or board-ready report.</p>
                    </div>
                  </div>
                  <div className="dashboard-toolbar dashboard-toolbar--premium">
                    <button className="btn-secondary" onClick={downloadCsv}>CSV</button>
                    <button className="btn-primary" onClick={downloadExecutiveReport}>Report</button>
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
                <h2>Problem Landscape</h2>
              </div>
            </div>
            <div className="dashboard-problem-layout">
              <div className="dashboard-merge-grid dashboard-merge-grid--problem-top">
                <div className="dashboard-subpanel dashboard-subpanel--complaints">
                  <TopIssuesChart key={`issues-${refreshKey}-${range}`} onIssueClick={handleIssueClick} limitMonths={limitMonths} />
                </div>

                <div className="dashboard-subpanel dashboard-subpanel--briefing">
                  {!uploadLoading && !chartsLoading && (
                    <ExecutiveSummary key={`ai-${refreshKey}-${range}`} range={range} />
                  )}
                </div>
              </div>

              <div className="dashboard-merge-grid dashboard-merge-grid--problem-bottom">
                <div className="dashboard-subpanel dashboard-subpanel--alerts">
                  <VanguardAlerts range={range} onAlertClick={handleAlertClick} />
                </div>

                <div className="dashboard-subpanel dashboard-subpanel--aspects">
                  <VanguardAspectMap range={range} onAspectClick={(aspect) => openDrawer({ aspect })} />
                </div>
              </div>
            </div>
          </div>
        </section>

        <section className="route-frame dashboard-grid-half dashboard-section dashboard-section--core">
          <div className="glass-card dashboard-panel dashboard-panel--compact dashboard-panel--sentiment">
            <div className="card-header">
              <div className="card-heading">
                <h2>Sentiment Health</h2>
              </div>
            </div>
            <div className="dashboard-merge-stack">
              <div className="dashboard-subpanel dashboard-subpanel--sentiment">
                <div className="dashboard-subpanel-fill dashboard-subpanel-fill--centered">
                  <SentimentChart
                    key={`sent-${refreshKey}-${range}`}
                    limitMonths={limitMonths}
                    onSentimentClick={(sentiment) => openDrawer({ topic: sentiment })}
                  />
                </div>
              </div>
              <div className="dashboard-subpanel dashboard-subpanel--stability">
                <SentimentStabilityChart
                  key={`stability-${refreshKey}-${range}`}
                  limitMonths={limitMonths}
                  onStabilityClick={(month) => openDrawer({ month })}
                />
              </div>
            </div>
          </div>

          <div className="glass-card dashboard-panel dashboard-panel--compact dashboard-panel--signals">
            <div className="card-header">
              <div className="card-heading">
                <h2>Signals &amp; Shifts</h2>
              </div>
            </div>
            <div className="dashboard-merge-stack dashboard-merge-stack--signals">
              <div className="dashboard-subpanel dashboard-subpanel--timeline">
                <TrendingChart key={`trending-${refreshKey}-${range}`} range={range} />
              </div>
            </div>
          </div>
        </section>

        <section className="route-frame dashboard-section dashboard-section--signal-lists">
          <div className="glass-card dashboard-panel dashboard-panel--compact dashboard-panel--signal-lists-combined">
            <div className="dashboard-merge-grid dashboard-merge-grid--signals">
              <div className="dashboard-subpanel dashboard-subpanel--emerging">
                <div className="card-header card-header--subpanel">
                  <div className="card-heading">
                    <h2>Watch</h2>
                  </div>
                </div>
                <EmergingIssuesPanel key={`emerge-${refreshKey}-${range}`} limitMonths={limitMonths} />
              </div>
              <div className="dashboard-subpanel dashboard-subpanel--drift">
                <div className="card-header card-header--subpanel">
                  <div className="card-heading">
                    <h2>New Issues</h2>
                  </div>
                </div>
                <SemanticDriftPanel
                  key={`drift-${refreshKey}-${range}`}
                  limitMonths={limitMonths}
                  onCategoryClick={(row) => openDrawer({
                    aspect: row.category,
                    title: row.category,
                    subtitle: `${row.n_months} months sampled • Shift strength ${row.avg_drift.toFixed(2)}`,
                  })}
                />
              </div>
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
