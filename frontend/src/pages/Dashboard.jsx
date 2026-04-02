import { useState, useEffect, useRef } from "react"
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
import { highlightEntities } from "../utils/highlight_utils.jsx"
import AppShell from "../components/AppShell"

function rangeToMonths(range) {
  const map = { "3M": 3, "6M": 6, "12M": 12, "ALL": 0 }
  return map[range] ?? 0
}

function TimelineSelector({ range, setRange }) {
  return (
    <div className="pill-group">
      <span className="pill-group__label">Range</span>
      {["3M", "6M", "12M", "ALL"].map((item) => (
        <button
          key={item}
          className={`pill-group__item${range === item ? " is-active" : ""}`}
          onClick={() => setRange(item)}
          type="button"
        >
          {item}
        </button>
      ))}
    </div>
  )
}

function formatEta(seconds) {
  if (!seconds || seconds <= 0) return null
  if (seconds > 60) return `${Math.floor(seconds / 60)}m ${seconds % 60}s remaining`
  return `${seconds}s remaining`
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
  const [range, setRange] = useState("ALL")
  const [drawer, setDrawer] = useState({ open: false, aspect: null, month: null, topic: null })
  const limitMonths = rangeToMonths(range)
  const progressInterval = useRef(null)

  const openDrawer = (opts) => setDrawer({ open: true, aspect: null, month: null, topic: null, ...opts })
  const closeDrawer = () => setDrawer((current) => ({ ...current, open: false }))

  const fetchData = async () => {
    try {
      const syncRes = await api.get("/sync/status")
      setSyncStatus(syncRes.data)
    } catch (error) {
      console.error("Failed to fetch dashboard data", error)
    }
  }

  useEffect(() => {
    fetchData()
    const checkInitialStatus = async () => {
      try {
        const res = await api.get("/upload-progress")
        if (["sentiment", "processing", "topic", "downloading", "unzipping"].includes(res.data.status)) {
          setProgress(res.data)
          setUploadLoading(true)
          startPolling()
        } else if (res.data.status === "complete") {
          setUploadLoading(false)
          setRefreshKey((prev) => prev + 1)
          fetchData()
          setStatus("Analysis complete!")
          setTimeout(() => setProgress({ processed: 0, total: 0, status: "idle", eta_seconds: 0 }), 2000)
        }
      } catch (error) {
        console.error("Initial status check failed", error)
      }
    }
    checkInitialStatus()
  }, [])

  useEffect(() => {
    return () => {
      if (progressInterval.current) clearInterval(progressInterval.current)
    }
  }, [])

  useEffect(() => {
    setReviews([])
    setIssue("")
  }, [range])

  const onAnalysisComplete = (finalStatus = "Success! Analysis complete.") => {
    setUploadLoading(false)
    setRefreshKey((prev) => prev + 1)
    fetchData()
    setStatus(finalStatus)
    setTimeout(() => {
      setStatus("")
      setProgress({ processed: 0, total: 0, status: "idle", eta_seconds: 0 })
    }, 3000)
  }

  const startPolling = async () => {
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
        } catch (error) {
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
  }

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
      setIssue("")
      setReviews([])
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
      setStatus("Syncing latest app data...")
      const res = await api.post("/sync/kaggle")
      setStatus(res.data.message || "Sync started!")
      fetchData()
      await startPolling()
    } catch (error) {
      console.error(error)
      setStatus("Data sync failed")
      setUploadLoading(false)
    }
  }

  const handleIssueClick = async (keywords) => {
    try {
      setChartsLoading(true)
      setIssue(keywords)
      const res = await api.get("/dashboard/issue-reviews", {
        params: { issue: keywords, limit_months: limitMonths },
      })
      setReviews(res.data.reviews || [])
      setIssueKeywords(res.data.keywords || "")
      setReviewWindow(res.data.window || "")
      setTotalInWindow(res.data.total_in_window || 0)
    } catch (error) {
      console.error(error)
      setReviews([])
      setIssueKeywords("")
      setReviewWindow("")
      setTotalInWindow(0)
    } finally {
      setChartsLoading(false)
    }
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
      setStatus("PDF generation failed")
    }
  }

  const workspaceItems = [
    {
      icon: "◔",
      title: "Recent exports",
      meta: range === "ALL" ? "All available time" : `Reporting window: ${range}`,
      description: "Generate CSV extracts and executive PDFs straight from the current filtered view.",
      badge: "Ready",
    },
    {
      icon: "◎",
      title: "Latest sync",
      meta: syncStatus?.last_sync ? new Date(syncStatus.last_sync).toLocaleDateString() : "Awaiting refresh",
      description: "Pull fresh marketplace reviews or upload a new file when you want the workspace updated.",
      badge: uploadLoading ? "Running" : "Idle",
    },
    {
      icon: "◌",
      title: "Evidence mode",
      meta: issue ? `Focused on ${issue}` : "No issue selected",
      description: "Click an issue bar or diagnostic chart to open customer comments and supporting evidence.",
      badge: reviews.length ? `${reviews.length} loaded` : "Explore",
    },
  ]

  return (
    <AppShell>
      <div className="page-grid">
        <div className="dashboard-layout">
          <div className="dashboard-stack">
            <section className="panel hero-chart-card">
              <div className="panel__header">
                <div>
                  <div className="panel__eyebrow">Insight Overview</div>
                  <h1 className="panel__title">Customer intelligence, reframed as a modern workspace.</h1>
                  <p className="panel__text">
                    Explore the current signal landscape, export filtered evidence, and monitor how
                    customer sentiment evolves over time without losing any of the original depth.
                  </p>
                </div>
                <div className="section-actions">
                  <TimelineSelector range={range} setRange={setRange} />
                  <button className="btn-secondary" onClick={downloadCsv} type="button">
                    CSV export
                  </button>
                  <button className="btn-primary" onClick={downloadExecutiveReport} type="button">
                    Executive report
                  </button>
                </div>
              </div>

              <KpiBar key={`kpi-${refreshKey}-${range}`} limitMonths={limitMonths} />
            </section>

            <section className="panel panel--tight">
              <SignalTicker />
            </section>

            {!uploadLoading && !chartsLoading ? (
              <section className="panel">
                <ExecutiveSummary key={`ai-${refreshKey}-${range}`} range={range} />
              </section>
            ) : null}

            <section className="panel">
              <div className="panel__header">
                <div>
                  <div className="panel__eyebrow">Movement</div>
                  <h2 className="panel__title panel__title--section">Trending topics over time</h2>
                  <p className="panel__text">
                    Use the timeline to understand which issues are intensifying, stabilizing, or
                    declining across the selected review window.
                  </p>
                </div>
              </div>
              <TrendingChart key={`trending-${refreshKey}-${range}`} range={range} setRange={setRange} />
            </section>
          </div>

          <aside className="dashboard-secondary">
            <section className="panel info-rail">
              <div className="panel__header">
                <div>
                  <div className="panel__eyebrow">Workspace Utilities</div>
                  <h2 className="panel__title panel__title--section">Recent operations</h2>
                </div>
                <a className="section-link" href="#admin-tools">
                  Data tools
                </a>
              </div>

              <div className="mini-list">
                {workspaceItems.map((item) => (
                  <article key={item.title} className="mini-item">
                    <div className="mini-item__icon">{item.icon}</div>
                    <div>
                      <div style={{ display: "flex", justifyContent: "space-between", gap: 12, flexWrap: "wrap" }}>
                        <p className="mini-item__title">{item.title}</p>
                        <span className={`status-badge${item.badge === "Running" ? " is-warning" : item.badge === "Ready" ? " is-positive" : ""}`}>
                          {item.badge}
                        </span>
                      </div>
                      <p className="mini-item__meta">{item.meta}</p>
                      <p className="mini-item__description">{item.description}</p>
                    </div>
                  </article>
                ))}
              </div>
            </section>

            <section className="panel feature-card feature-card--highlight">
              <div>
                <div className="panel__eyebrow">Upgrade the narrative</div>
                <h2 className="panel__title panel__title--section">A calmer shell for dense analytics.</h2>
                <p className="panel__text">
                  The experience now prioritizes clarity, premium spacing, and easier scanning
                  while preserving the full analytical depth underneath.
                </p>
              </div>
              <div className="feature-card__cta">
                <span className="muted">Active view</span>
                <strong>{range === "ALL" ? "All available time" : `Last ${range}`}</strong>
              </div>
            </section>

            <section className="panel">
              <div className="panel__header">
                <div>
                  <div className="panel__eyebrow">Live highlights</div>
                  <h2 className="panel__title panel__title--section">Signal center</h2>
                </div>
              </div>
              <VanguardAlerts range={range} />
            </section>
          </aside>
        </div>

        <div className="surface-grid surface-grid--2">
          <section className="panel">
            <div className="panel__header">
              <div>
                <div className="panel__eyebrow">Sentiment mix</div>
                <h2 className="panel__title panel__title--section">Overall customer happiness</h2>
                <p className="panel__text">Select a sentiment slice to inspect the supporting evidence.</p>
              </div>
            </div>
            <SentimentChart
              key={`sent-${refreshKey}-${range}`}
              limitMonths={limitMonths}
              onSentimentClick={(sentiment) => openDrawer({ topic: sentiment })}
            />
          </section>

          <section className="panel">
            <div className="panel__header">
              <div>
                <div className="panel__eyebrow">Problem map</div>
                <h2 className="panel__title panel__title--section">Top problem areas</h2>
                <p className="panel__text">
                  Product aspects with concentrated complaint volume and changing customer tone.
                </p>
              </div>
            </div>
            <VanguardAspectMap range={range} onAspectClick={(aspect) => openDrawer({ aspect })} />
          </section>
        </div>

        <section className="panel">
          <div className="panel__header">
            <div>
              <div className="panel__eyebrow">Issue prioritization</div>
              <h2 className="panel__title panel__title--section">Main customer complaints</h2>
              <p className="panel__text">
                Click any bar to move from ranked issue signal into direct customer evidence.
              </p>
            </div>
          </div>
          <TopIssuesChart key={`issues-${refreshKey}-${range}`} onIssueClick={handleIssueClick} limitMonths={limitMonths} />
        </section>

        {reviews.length > 0 ? (
          <section className="panel">
            <div className="panel__header">
              <div>
                <div className="panel__eyebrow">Evidence dossier</div>
                <h2 className="panel__title panel__title--section">What customers are saying</h2>
                <p className="panel__text">
                  Focused evidence for <strong>{issue}</strong> with deduplicated comments ranked by relevance.
                </p>
              </div>
              <div className="section-actions">
                {reviewWindow ? <span className="status-badge is-warning">{reviewWindow}</span> : null}
                <span className="status-badge">{totalInWindow.toLocaleString()} comments in view</span>
              </div>
            </div>

            <div className="review-grid">
              {reviews.map((review, index) => {
                const isEnterprise = review.user_tier === "Enterprise" || (review.value_weight && review.value_weight >= 4)
                const isPremium = review.user_tier === "Premium" || (review.value_weight && review.value_weight >= 2)

                return (
                  <article className="review-card" key={index}>
                    <div className="review-card__meta">
                      <div style={{ display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap" }}>
                        {isEnterprise ? <span className="status-badge is-critical">Enterprise</span> : null}
                        {!isEnterprise && isPremium ? <span className="status-badge is-warning">Premium</span> : null}
                        <span className="status-badge">{"★".repeat(parseInt(review.score, 10) || 0)}{"☆".repeat(5 - (parseInt(review.score, 10) || 0))}</span>
                        {review.upvotes > 0 ? <span className="status-badge">↑ {review.upvotes} upvotes</span> : null}
                      </div>

                      <div style={{ textAlign: "right" }}>
                        <div className="muted" style={{ fontSize: "0.82rem", fontWeight: 700 }}>
                          {review.at ? review.at.split("T")[0] : "Recent"}
                        </div>
                        {review.app_version && review.app_version !== "N/A" ? (
                          <div className="faint" style={{ fontSize: "0.76rem", fontWeight: 700 }}>
                            Ver {review.app_version.replace("Build ", "")}
                          </div>
                        ) : null}
                      </div>
                    </div>

                    <p
                      className="review-card__quote"
                      style={{ fontStyle: parseInt(review.score, 10) <= 2 ? "italic" : "normal" }}
                    >
                      "
                      {highlightEntities(
                        review.text || "",
                        `${issueKeywords}, slow, fast, expensive, price, crash, bug, error, login, payment, quality`,
                      )}
                      "
                    </p>

                    {review.value_weight > 1 ? (
                      <div style={{ display: "flex", justifyContent: "flex-end" }}>
                        <span className="status-badge is-critical">
                          {review.value_weight.toFixed(1)}x business importance
                        </span>
                      </div>
                    ) : null}
                  </article>
                )
              })}
            </div>
          </section>
        ) : null}

        <div className="surface-grid surface-grid--3">
          <section className="panel">
            <div className="panel__header">
              <div>
                <div className="panel__eyebrow">Stability</div>
                <h2 className="panel__title panel__title--section">Overall happiness trend</h2>
              </div>
            </div>
            <SentimentStabilityChart
              key={`stability-${refreshKey}-${range}`}
              limitMonths={limitMonths}
              onStabilityClick={(month) => openDrawer({ month })}
            />
          </section>

          <section className="panel">
            <div className="panel__header">
              <div>
                <div className="panel__eyebrow">New clusters</div>
                <h2 className="panel__title panel__title--section">Emerging issues</h2>
              </div>
            </div>
            <EmergingIssuesPanel key={`emerging-${refreshKey}-${range}`} limitMonths={limitMonths} />
          </section>

          <section className="panel">
            <div className="panel__header">
              <div>
                <div className="panel__eyebrow">Language shift</div>
                <h2 className="panel__title panel__title--section">Semantic drift</h2>
              </div>
            </div>
            <SemanticDriftPanel key={`drift-${refreshKey}-${range}`} limitMonths={limitMonths} />
          </section>
        </div>

        <section className="panel" id="admin-tools">
          <div className="panel__header">
            <div>
              <div className="panel__eyebrow">Operations</div>
              <h2 className="panel__title panel__title--section">Data acquisition and refresh</h2>
              <p className="panel__text">
                Bring in new review files, sync the latest external data, and monitor background processing.
              </p>
            </div>
          </div>

          <div className="dashboard-admin">
            <div className="upload-row">
              <label className="btn-secondary" style={{ position: "relative", overflow: "hidden" }}>
                Choose file
                <input
                  type="file"
                  onChange={(event) => setFile(event.target.files[0])}
                  style={{ position: "absolute", inset: 0, opacity: 0, cursor: "pointer" }}
                />
              </label>
              <button className="btn-primary" onClick={handleUpload} disabled={uploadLoading} type="button">
                {uploadLoading ? "Analyzing..." : "Upload and analyze"}
              </button>
              <button className="btn-secondary" onClick={handleKaggleSync} disabled={uploadLoading} type="button">
                Sync latest app data
              </button>
              <span className="muted" style={{ fontSize: "0.88rem" }}>
                {file ? `Selected: ${file.name}` : "Upload a review file or pull the latest synced dataset."}
              </span>
            </div>

            {syncStatus?.last_sync ? (
              <div className="auth-note">
                Last data refresh: <strong>{new Date(syncStatus.last_sync).toLocaleDateString()}</strong>
              </div>
            ) : null}

            {status ? (
              <div className={`auth-note${status.toLowerCase().includes("failed") ? " error-note" : ""}`}>{status}</div>
            ) : null}

            {uploadLoading && progress.total > 0 ? (
              <div className="progress-shell">
                <div className="progress-bar">
                  <div
                    className="progress-bar__value"
                    style={{ width: `${(progress.processed / progress.total) * 100}%` }}
                  />
                </div>
                <div style={{ display: "flex", justifyContent: "space-between", gap: 14, flexWrap: "wrap" }}>
                  <div>
                    <strong style={{ color: "var(--text-strong)" }}>{progress.status.toUpperCase()}</strong>
                    <div className="muted" style={{ marginTop: 4 }}>
                      {progress.status === "downloading" || progress.status === "unzipping"
                        ? `${progress.processed}%`
                        : `${progress.processed.toLocaleString()} / ${progress.total.toLocaleString()} reviews (${Math.round((progress.processed / progress.total) * 100)}%)`}
                    </div>
                  </div>
                  {formatEta(progress.eta_seconds) ? <span className="status-badge">{formatEta(progress.eta_seconds)}</span> : null}
                </div>
                <div>
                  <button className="text-button" onClick={handleStop} type="button">
                    Stop early
                  </button>
                </div>
              </div>
            ) : null}
          </div>
        </section>
      </div>

      <DiagnosticDrawer
        isOpen={drawer.open}
        onClose={closeDrawer}
        aspect={drawer.aspect}
        month={drawer.month}
        topic={drawer.topic}
      />
    </AppShell>
  )
}
