import React, { useState, useEffect } from "react";
import api from "../services/api";

function severityRank(severity) {
    if (severity === "CRITICAL") return 0;
    if (severity === "HIGH") return 1;
    return 2;
}

function severityStyles(severity) {
    if (severity === "CRITICAL") return { color: "#f26a3d", background: "rgba(242, 106, 61, 0.12)", border: "rgba(242, 106, 61, 0.18)" };
    if (severity === "HIGH") return { color: "#eca74c", background: "rgba(236, 167, 76, 0.14)", border: "rgba(236, 167, 76, 0.18)" };
    return { color: "#4b78b4", background: "rgba(75, 120, 180, 0.12)", border: "rgba(75, 120, 180, 0.16)" };
}

function humanizeAlertMessage(alert) {
    const message = String(alert?.message || "");

    if (message.includes("Dominant Volume")) {
        const match = message.match(/Accounting for ([\d.]+)%/);
        return match ? `This area is dominating the conversation right now, representing about ${Math.round(parseFloat(match[1]))}% of all feedback.` : "This area is currently dominating the conversation volume.";
    }

    if (message.includes("Statistically out-of-control") && message.includes("MoM spike")) {
        const spikeMatch = message.match(/MoM spike of \+([\d.]+)%/);
        const pct = spikeMatch ? Math.round(parseFloat(spikeMatch[1])) : null;
        return pct ? `Alert volume is unusually high and has risen by about ${pct}% versus the previous window.` : "Alert volume is unusually high and rising sharply.";
    }

    if (message.includes("Statistically out-of-control")) {
        return "This topic is behaving well outside its usual baseline and deserves immediate review.";
    }

    if (message.includes("MoM spike")) {
        const spikeMatch = message.match(/MoM spike of \+([\d.]+)%/);
        const pct = spikeMatch ? Math.round(parseFloat(spikeMatch[1])) : null;
        return pct ? `Mentions increased by about ${pct}% compared with the previous period.` : "Mentions are rising quickly in the current window.";
    }

    return "A meaningful shift was detected in this topic during the current window.";
}

function nextStepLabel(alert) {
    if (alert?.link?.linked_to) return `Likely linked to ${alert.link.linked_to}`;
    if (alert?.is_anomaly) return "Review the latest comments for abnormal spikes";
    return "Review recent feedback volume for this topic";
}

const VanguardAlerts = ({ range, onAlertClick }) => {
    const [alerts, setAlerts] = useState([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        let ignore = false;

        const fetchAlerts = async () => {
            try {
                const limitMonths = range === "3M" ? 3 : range === "6M" ? 6 : range === "12M" ? 12 : 0;
                const res = await api.get("/dashboard/intelligence-alerts", { params: { limit_months: limitMonths } });
                if (!ignore) {
                    setAlerts(res.data.alerts || []);
                }
            } catch (err) {
                console.error("Signal Center Error:", err);
                if (!ignore) {
                    setAlerts([]);
                }
            } finally {
                if (!ignore) {
                    setLoading(false);
                }
            }
        };

        fetchAlerts();
        const interval = setInterval(fetchAlerts, 60000);
        return () => {
            ignore = true;
            clearInterval(interval);
        };
    }, [range]);

    if (loading && alerts.length === 0) {
        return <div className="dashboard-empty">Scanning for alert activity...</div>;
    }

    if (alerts.length === 0) {
        return <div className="dashboard-empty">No live anomalies in the current window.</div>;
    }

    const visibleAlerts = [...alerts]
        .sort((a, b) => {
            const severityDiff = severityRank(a.severity) - severityRank(b.severity);
            if (severityDiff !== 0) return severityDiff;
            return (b.velocity_pct || 0) - (a.velocity_pct || 0);
        })
        .slice(0, 4);

    return (
        <div className="alerts-briefing">
            <div className="alerts-briefing__intro">
                Recent critical changes detected in the current window, ordered by urgency.
            </div>

            <div className="alerts-briefing__stack">
                {visibleAlerts.map((alert) => {
                    const severity = severityStyles(alert.severity);
                    return (
                        <button
                            key={alert.id}
                            className="alerts-briefing__item"
                            type="button"
                            onClick={() => onAlertClick && onAlertClick(alert)}
                            style={{
                                borderColor: severity.border,
                                background: severity.background,
                            }}
                        >
                            <div className="alerts-briefing__header">
                                <div className="alerts-briefing__titleblock">
                                    <div className="alerts-briefing__chips">
                                        <span className="alerts-briefing__chip" style={{ color: severity.color, background: "#ffffff" }}>
                                            {alert.severity}
                                        </span>
                                        {alert?.is_anomaly && (
                                            <span className="alerts-briefing__chip alerts-briefing__chip--secondary">
                                                Anomaly
                                            </span>
                                        )}
                                    </div>
                                    <h4>{alert.category}</h4>
                                </div>
                            </div>

                            <p className="alerts-briefing__message">
                                {humanizeAlertMessage(alert)}
                            </p>

                            <div className="alerts-briefing__footer">
                                <div className="alerts-briefing__nextstep">
                                    <span>Next signal</span>
                                    <strong>{nextStepLabel(alert)}</strong>
                                </div>

                                <div className="alerts-briefing__cta">Open evidence</div>

                                {alert?.link && (
                                    <div className="alerts-briefing__context">
                                        Related issue: {alert.link.linked_to} ({Math.floor((alert.link.score || 0) * 100)}% correlation)
                                    </div>
                                )}
                            </div>
                        </button>
                    );
                })}
            </div>
        </div>
    );
};

export default VanguardAlerts;
