import React, { useState, useEffect } from "react";
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts";
import api from "../services/api";
import { SkeletonChart } from "./Skeleton";

const COLORS = ["#4b78b4", "#7b8ce0", "#31b57e"];

function formatMetricValue(value, metric) {
    const safeValue = Number(value || 0);
    if (metric === "revenue") return `$${safeValue.toFixed(0)}`;
    return `${Math.round(safeValue)}`;
}

function getTopicTrend(currentRow, prevRow, key) {
    const current = Number(currentRow?.[key] || 0);
    const previous = Number(prevRow?.[key] || 0);

    if (!previous && current > 0) return { label: "New", tone: "cool" };
    if (!previous && !current) return { label: "Stable", tone: "neutral" };

    const pct = ((current - previous) / Math.max(previous, 1)) * 100;
    if (pct > 10) return { label: "Rising", tone: "hot" };
    if (pct < -10) return { label: "Cooling", tone: "good" };
    return { label: "Stable", tone: "neutral" };
}

function toneStyles(tone) {
    if (tone === "hot") return { color: "#ea5b57", background: "rgba(234, 91, 87, 0.12)" };
    if (tone === "good") return { color: "#31b57e", background: "rgba(49, 181, 126, 0.12)" };
    if (tone === "cool") return { color: "#4b78b4", background: "rgba(75, 120, 180, 0.12)" };
    return { color: "#72788c", background: "rgba(114, 120, 140, 0.12)" };
}

function buildVisibleTopics(rows, keys) {
    if (!rows.length || !keys.length) return [];
    const lastActualIndex = rows.length - 1;
    const currentRow = rows[lastActualIndex];
    const prevRow = rows[Math.max(0, lastActualIndex - 1)];

    return keys
        .map((key) => ({
            key,
            currentValue: Number(currentRow?.[key] || 0),
            prevValue: Number(prevRow?.[key] || 0),
            trend: getTopicTrend(currentRow, prevRow, key),
        }))
        .sort((a, b) => b.currentValue - a.currentValue)
        .slice(0, 3);
}

export default function TrendingChart({ range }) {
    const [chartRows, setChartRows] = useState([]);
    const [visibleTopics, setVisibleTopics] = useState([]);
    const [loading, setLoading] = useState(true);
    const [activeMetric, setActiveMetric] = useState("severity");

    useEffect(() => {
        let ignore = false;

        const fetchTrendingData = async () => {
            try {
                const limitMonths = range === "3M" ? 3 : range === "6M" ? 6 : range === "12M" ? 12 : 0;
                const res = await api.get("/dashboard/trending-issues", {
                    params: { limit_months: limitMonths, metric: activeMetric }
                });

                if (ignore) return;

                const rawRows = Array.isArray(res.data) ? res.data.filter((row) => !row.is_forecast) : [];
                if (!rawRows.length) {
                    setChartRows([]);
                    setVisibleTopics([]);
                    return;
                }

                const allKeys = Object.keys(rawRows[0]).filter((key) =>
                    key !== "month" &&
                    !key.endsWith("_upper_bound") &&
                    !key.endsWith("_mom") &&
                    !key.endsWith("_correlated_with") &&
                    key !== "is_forecast"
                );

                const topTopics = buildVisibleTopics(rawRows, allKeys);
                const topTopicKeys = topTopics.map((topic) => topic.key);

                setVisibleTopics(topTopics);
                setChartRows(
                    rawRows.map((row) => {
                        const nextRow = { month: row.month };
                        topTopicKeys.forEach((key) => {
                            nextRow[key] = Number(row[key] || 0);
                        });
                        return nextRow;
                    })
                );
            } catch (err) {
                console.error("Error fetching trending data:", err);
                if (!ignore) {
                    setChartRows([]);
                    setVisibleTopics([]);
                }
            } finally {
                if (!ignore) {
                    setLoading(false);
                }
            }
        };

        fetchTrendingData();

        return () => {
            ignore = true;
        };
    }, [range, activeMetric]);

    if (loading) return <SkeletonChart height={360} />;

    if (!chartRows.length || !visibleTopics.length) {
        return (
            <div style={{ height: "300px", display: "flex", alignItems: "center", justifyContent: "center" }}>
                <p style={{ color: "#72788c", fontWeight: 500 }}>No trend data available for this window.</p>
            </div>
        );
    }

    const CustomTooltip = ({ active, payload, label }) => {
        if (!active || !payload || !payload.length) return null;

        return (
            <div
                style={{
                    background: "#FFFFFF",
                    border: "1px solid rgba(91, 100, 121, 0.12)",
                    padding: "14px",
                    borderRadius: "16px",
                    color: "#262c3f",
                    boxShadow: "0 10px 18px rgba(49, 57, 77, 0.08)"
                }}
            >
                <div style={{ margin: "0 0 10px 0", fontWeight: 700, borderBottom: "1px solid rgba(91, 100, 121, 0.12)", paddingBottom: "8px", fontSize: "13px" }}>
                    {label}
                </div>

                {payload
                    .slice()
                    .sort((a, b) => (b.value || 0) - (a.value || 0))
                    .map((entry) => {
                        const topic = visibleTopics.find((item) => item.key === entry.name);
                        const trend = topic?.trend || { label: "Stable", tone: "neutral" };
                        const tone = toneStyles(trend.tone);

                        return (
                            <div key={entry.name} style={{ display: "flex", flexDirection: "column", gap: "4px", marginBottom: "10px" }}>
                                <div style={{ display: "flex", alignItems: "center", gap: "8px", color: entry.color, fontSize: "12px", fontWeight: 700 }}>
                                    <span style={{ width: 8, height: 8, borderRadius: "50%", background: entry.color, display: "inline-block" }} />
                                    <span>{entry.name}</span>
                                </div>
                                <div style={{ color: "#262c3f", fontSize: "15px", fontWeight: 800 }}>
                                    {formatMetricValue(entry.value, activeMetric)}
                                </div>
                                <div style={{ display: "inline-flex", width: "fit-content", padding: "4px 8px", borderRadius: "999px", fontSize: "11px", fontWeight: 800, color: tone.color, background: tone.background }}>
                                    {trend.label}
                                </div>
                            </div>
                        );
                    })}
            </div>
        );
    };

    return (
        <div className="trending-panel">
            <div className="trending-panel__topbar">
                <div>
                    <div className="trending-panel__hint">Focus on the top 3 topics changing most in the current view.</div>
                    <div className="trending-panel__helper">
                        {activeMetric === "revenue"
                            ? "Business Impact shows estimated cost pressure over time."
                            : "Priority shows which issues are becoming more urgent over time."}
                    </div>
                </div>

                <div className="trending-toggle" role="tablist" aria-label="Trending metric mode">
                    <button
                        className={`trending-toggle__button ${activeMetric === "severity" ? "is-active" : ""}`.trim()}
                        onClick={() => setActiveMetric("severity")}
                    >
                        Priority
                    </button>
                    <button
                        className={`trending-toggle__button ${activeMetric === "revenue" ? "is-active" : ""}`.trim()}
                        onClick={() => setActiveMetric("revenue")}
                    >
                        Business Impact
                    </button>
                </div>
            </div>

            <div className="trending-summary">
                {visibleTopics.map((topic, index) => {
                    const tone = toneStyles(topic.trend.tone);
                    return (
                        <div key={topic.key} className="trending-summary__card">
                            <div className="trending-summary__row">
                                <span className="trending-summary__dot" style={{ background: COLORS[index % COLORS.length] }} />
                                <span className="trending-summary__name">{topic.key}</span>
                            </div>
                            <strong>{formatMetricValue(topic.currentValue, activeMetric)}</strong>
                            <span className="trending-summary__subtle">
                                Previous {formatMetricValue(topic.prevValue, activeMetric)}
                            </span>
                            <span className="trending-summary__status" style={{ color: tone.color, background: tone.background }}>
                                {topic.trend.label}
                            </span>
                        </div>
                    );
                })}
            </div>

            <div className="trending-chart-wrap">
                <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={chartRows} margin={{ top: 8, right: 12, left: -18, bottom: 16 }}>
                        <defs>
                            {visibleTopics.map((topic, index) => (
                                <linearGradient key={topic.key} id={`trend-fill-${index}`} x1="0" y1="0" x2="0" y2="1">
                                    <stop offset="5%" stopColor={COLORS[index % COLORS.length]} stopOpacity={0.26} />
                                    <stop offset="100%" stopColor={COLORS[index % COLORS.length]} stopOpacity={0.03} />
                                </linearGradient>
                            ))}
                        </defs>

                        <CartesianGrid strokeDasharray="3 3" stroke="rgba(91, 100, 121, 0.12)" vertical={false} />
                        <XAxis
                            dataKey="month"
                            axisLine={false}
                            tickLine={false}
                            tick={{ fill: "#72788c", fontSize: 12, fontWeight: 600 }}
                            dy={6}
                            height={34}
                        />
                        <YAxis
                            axisLine={false}
                            tickLine={false}
                            tick={{ fill: "#9aa0af", fontSize: 11, fontWeight: 600 }}
                            tickFormatter={(value) => (value === 0 ? "" : Math.round(value))}
                        />
                        <Tooltip content={<CustomTooltip />} cursor={{ stroke: "rgba(91, 100, 121, 0.22)", strokeDasharray: "4 4" }} />

                        {visibleTopics.map((topic, index) => (
                            <Area
                                key={topic.key}
                                type="monotone"
                                dataKey={topic.key}
                                stroke={COLORS[index % COLORS.length]}
                                strokeWidth={2.5}
                                fill={`url(#trend-fill-${index})`}
                                fillOpacity={1}
                                activeDot={{ r: 5, fill: "#ffffff", stroke: COLORS[index % COLORS.length], strokeWidth: 2 }}
                            />
                        ))}
                    </AreaChart>
                </ResponsiveContainer>
            </div>

        </div>
    );
}
