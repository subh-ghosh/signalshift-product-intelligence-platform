import React, { useState, useEffect } from "react";
import api from "../services/api";
import { SkeletonChart } from "./Skeleton";

function getSeverityMeta(score) {
    if (score >= 4.0) return { label: "Critical", color: "#ea5b57", background: "rgba(234, 91, 87, 0.12)" };
    if (score >= 3.0) return { label: "High", color: "#eca74c", background: "rgba(236, 167, 76, 0.14)" };
    if (score >= 2.5) return { label: "Watch", color: "#4b78b4", background: "rgba(75, 120, 180, 0.12)" };
    return { label: "Stable", color: "#31b57e", background: "rgba(49, 181, 126, 0.12)" };
}

function getMomentumMeta(momentumPct) {
    if (momentumPct > 5) return { label: `Getting worse ${Math.abs(momentumPct)}%`, color: "#ea5b57", background: "rgba(234, 91, 87, 0.12)" };
    if (momentumPct < -5) return { label: `Improving ${Math.abs(momentumPct)}%`, color: "#31b57e", background: "rgba(49, 181, 126, 0.12)" };
    return { label: "Holding steady", color: "#72788c", background: "rgba(114, 120, 140, 0.12)" };
}

const VanguardAspectMap = ({ range, onAspectClick }) => {
    const [data, setData] = useState([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        let ignore = false;

        const fetchAspects = async () => {
            try {
                const limitMonths = range === "3M" ? 3 : range === "6M" ? 6 : range === "12M" ? 12 : 0;
                const res = await api.get("/dashboard/aspects", { params: { limit_months: limitMonths } });
                if (!ignore) {
                    setData(res.data || []);
                }
            } catch (err) {
                console.error("Vanguard Map Error:", err);
                if (!ignore) {
                    setData([]);
                }
            } finally {
                if (!ignore) {
                    setLoading(false);
                }
            }
        };

        fetchAspects();
        return () => {
            ignore = true;
        };
    }, [range]);

    if (loading && data.length === 0) return <SkeletonChart height={300} />;
    if (data.length === 0) return <div className="dashboard-empty">No aspect data available in this window.</div>;

    const maxMentions = Math.max(...data.map((item) => item.mentions || 0), 1);

    return (
        <div className="aspect-scorecard">
            <div className="aspect-scorecard__hint">Click an area to inspect the strongest supporting issue evidence.</div>
            <div className="aspect-scorecard__rows">
                {data.map((item, index) => {
                    const severity = getSeverityMeta(item.sentiment_score || 0);
                    const momentum = getMomentumMeta(item.momentum_pct || 0);
                    const barWidth = `${Math.max(14, Math.round(((item.mentions || 0) / maxMentions) * 100))}%`;

                    return (
                        <button
                            key={item.aspect}
                            type="button"
                            className="aspect-row"
                            onClick={() => onAspectClick && onAspectClick(item.top_topic || item.aspect)}
                        >
                            <div className="aspect-row__rank">{String(index + 1).padStart(2, "0")}</div>

                            <div className="aspect-row__body">
                                <div className="aspect-row__header">
                                    <div className="aspect-row__titleblock">
                                        <div className="aspect-row__title">{item.aspect}</div>
                                        <div className="aspect-row__meta">
                                            <span className="aspect-chip" style={{ color: severity.color, background: severity.background }}>
                                                {severity.label}
                                            </span>
                                            <span className="aspect-chip" style={{ color: momentum.color, background: momentum.background }}>
                                                {momentum.label}
                                            </span>
                                        </div>
                                    </div>

                                    <div className="aspect-row__metrics">
                                        <div className="aspect-row__metric">
                                            <span>Complaint volume</span>
                                            <strong>{item.mentions.toLocaleString()}</strong>
                                        </div>
                                        <div className="aspect-row__metric">
                                            <span>Severity score</span>
                                            <strong>{item.sentiment_score}/5.0</strong>
                                        </div>
                                        <div className="aspect-row__cta">View evidence</div>
                                    </div>
                                </div>

                                <div className="aspect-row__subline">
                                    <span className="aspect-row__issue-label">Top issue</span>
                                    <span className="aspect-row__issue-value">{item.top_topic}</span>
                                </div>

                                <div className="aspect-row__rail">
                                    <div className="aspect-row__fill" style={{ width: barWidth, background: severity.color }} />
                                </div>
                            </div>
                        </button>
                    );
                })}
            </div>
        </div>
    );
};

export default VanguardAspectMap;
