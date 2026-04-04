import React, { useState, useEffect } from "react";
import {
    LineChart,
    Line,
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
    ResponsiveContainer,
    Area,
    ComposedChart,
    Scatter
} from "recharts";
import api from "../services/api";
import { SkeletonChart } from "./Skeleton";

function getStabilityMeta(score) {
    if (score > 90) return { label: "Excellent", color: "#31b57e", background: "rgba(49, 181, 126, 0.12)" };
    if (score > 70) return { label: "Consistent", color: "#4b78b4", background: "rgba(75, 120, 180, 0.12)" };
    return { label: "Fluctuating", color: "#ea5b57", background: "rgba(234, 91, 87, 0.12)" };
}

const SentimentStabilityChart = ({ limitMonths = 0, onStabilityClick }) => {
    const [data, setData] = useState([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const fetchStability = async () => {
            setLoading(true);
            try {
                const res = await api.get("/dashboard/sentiment-stability", {
                    params: { limit_months: limitMonths }
                });
                setData(res.data || []);
            } catch (err) {
                console.error("Stability Chart Error:", err);
            } finally {
                setLoading(false);
            }
        };
        fetchStability();
    }, [limitMonths]);

    if (loading) return <SkeletonChart height={250} />;
    if (!data.length) return <p style={{ color: "#72788c", fontSize: "14px", padding: "20px 0" }}>No stability data available.</p>;

    const volatileMonths = data.filter((item) => item.is_volatile);
    const hasVolatileMonths = volatileMonths.length > 0;
    const stabilityScore = Math.max(0, 100 - (volatileMonths.length * 20));
    const stability = getStabilityMeta(stabilityScore);
    const latestMonth = data[data.length - 1];

    return (
        <div className="stability-card">
            <div className="stability-card__topline">
                <div>
                    <div className="stability-card__eyebrow">Stability summary</div>
                    <div className="stability-card__headline">{stabilityScore}% happiness stability</div>
                    <div className="stability-card__copy">
                        Latest month: {latestMonth.month} at a sentiment score of {latestMonth.score}.
                    </div>
                </div>
                <span className="stability-card__status" style={{ color: stability.color, background: stability.background }}>
                    {stability.label}
                </span>
            </div>

            <div className="stability-card__helper">
                Red markers indicate unusual months outside the normal range. Use the highlighted month chips below to open evidence.
            </div>

            {hasVolatileMonths ? (
                <div className="stability-card__months">
                    {volatileMonths.map((item) => (
                        <button
                            key={item.month}
                            type="button"
                            className="stability-month"
                            onClick={() => onStabilityClick && onStabilityClick(item.month)}
                        >
                            <span>{item.month}</span>
                            <strong>Open notable shift</strong>
                        </button>
                    ))}
                </div>
            ) : (
                <div className="stability-card__steady">No unusual months detected in the current window.</div>
            )}

            <div className="stability-card__chart">
                <ResponsiveContainer width="100%" height="100%">
                    <ComposedChart data={data} margin={{ top: 14, right: 16, left: -18, bottom: 16 }}>
                        <defs>
                            <linearGradient id="stabilityGradient" x1="0" y1="0" x2="0" y2="1">
                                <stop offset="5%" stopColor="#4b78b4" stopOpacity={0.14} />
                                <stop offset="95%" stopColor="#4b78b4" stopOpacity={0.01} />
                            </linearGradient>
                        </defs>
                        <CartesianGrid strokeDasharray="3 3" stroke="rgba(91, 100, 121, 0.12)" vertical={false} />
                        <XAxis
                            dataKey="month"
                            axisLine={false}
                            tickLine={false}
                            tick={{ fill: "#72788c", fontSize: 11, fontWeight: 600 }}
                            dy={6}
                            height={34}
                        />
                        <YAxis
                            hide
                            domain={["dataMin - 0.2", "dataMax + 0.2"]}
                        />
                        <Tooltip
                            content={({ active, payload }) => {
                                if (active && payload && payload.length) {
                                    const row = payload[0].payload;
                                    return (
                                        <div
                                            style={{
                                                background: "#FFFFFF",
                                                border: "1px solid rgba(91, 100, 121, 0.12)",
                                                padding: "14px",
                                                borderRadius: "16px",
                                                fontSize: "12px",
                                                boxShadow: "0 10px 18px rgba(49, 57, 77, 0.08)"
                                            }}
                                        >
                                            <div style={{ fontWeight: 700, color: "#262c3f", marginBottom: "8px", borderBottom: "1px solid rgba(91, 100, 121, 0.12)", paddingBottom: "6px" }}>
                                                {row.month}
                                            </div>
                                            <div style={{ color: "#72788c", marginBottom: "4px" }}>
                                                Happiness level: <strong style={{ color: "#262c3f", fontSize: "14px" }}>{row.score}</strong>
                                            </div>
                                            <div style={{ display: "inline-flex", marginTop: "8px", padding: "4px 8px", borderRadius: "999px", fontSize: "11px", fontWeight: 800, color: row.is_volatile ? "#ea5b57" : "#4b78b4", background: row.is_volatile ? "rgba(234, 91, 87, 0.12)" : "rgba(75, 120, 180, 0.12)" }}>
                                                {row.is_volatile ? "Notable shift" : "Within normal range"}
                                            </div>
                                        </div>
                                    );
                                }
                                return null;
                            }}
                        />
                        <Area
                            type="monotone"
                            dataKey="upper_band"
                            stroke="none"
                            fill="url(#stabilityGradient)"
                            baseLine={({ payload }) => payload.lower_band}
                        />
                        <Line
                            type="monotone"
                            dataKey="score"
                            stroke="#4b78b4"
                            strokeWidth={3}
                            dot={{ r: 4, fill: "#4b78b4", strokeWidth: 0 }}
                            activeDot={{ r: 6, fill: "#FFFFFF", stroke: "#4b78b4", strokeWidth: 2 }}
                        />
                        <Scatter
                            data={volatileMonths}
                            fill="#ea5b57"
                            stroke="#FFFFFF"
                            strokeWidth={2}
                            r={6}
                        />
                    </ComposedChart>
                </ResponsiveContainer>
            </div>
        </div>
    );
};

export default SentimentStabilityChart;
