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

const SentimentStabilityChart = ({ limitMonths = 0, onStabilityClick }) => {
    const [data, setData] = useState([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const fetchStability = async () => {
            setLoading(true);
            try {
                const res = await api.get("/dashboard/sentiment-stability");
                const rawData = res.data || [];
                const displayData = limitMonths > 0 ? rawData.slice(-limitMonths) : rawData;
                setData(displayData);
            } catch (err) {
                console.error("Stability Chart Error:", err);
            } finally {
                setLoading(false);
            }
        };
        fetchStability();
    }, [limitMonths]);

    if (loading) return <SkeletonChart height={250} />;
    if (!data.length) return <p style={{ color: "#64748B", fontSize: "14px", padding: "20px 0" }}>No stability data available.</p>;

    const volatileCount = data.filter(d => d.is_volatile).length;
    const stabilityScore = Math.max(0, 100 - (volatileCount * 20));

    // Clean Light Theme Health Status
    const healthStatus = stabilityScore > 90 ? "EXCELLENT" : stabilityScore > 70 ? "CONSISTENT" : "FLUCTUATING";
    const healthColor = stabilityScore > 90 ? "#10B981" : stabilityScore > 70 ? "#3B82F6" : "#EF4444"; // Emerald, Blue, Rose
    const healthBg = stabilityScore > 90 ? "#ECFDF5" : stabilityScore > 70 ? "#EFF6FF" : "#FEF2F2";

    return (
        <div style={{ width: "100%", height: 340, position: "relative", marginTop: "10px" }}>
            {/* Responsive Header: Stability Index + Status + Legend */}
            <div style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                flexWrap: "wrap",
                gap: "16px",
                marginBottom: "20px",
                padding: "0 10px"
            }}>
                {/* Consistency Health Index */}
                <div title="Measure of how consistent customer satisfaction is over time" style={{
                    display: "flex",
                    alignItems: "center",
                    gap: "12px"
                }}>
                    <div style={{
                        fontSize: "12px",
                        fontWeight: 700,
                        color: healthColor,
                        padding: "4px 10px",
                        borderRadius: "8px",
                        background: healthBg,
                        border: `1px solid ${healthColor}33`,
                        letterSpacing: "0.5px",
                        whiteSpace: "nowrap"
                    }}>
                        {stabilityScore}% HAPPINESS STABILITY
                    </div>
                    <div style={{ fontSize: "11px", fontWeight: 700, color: "#94A3B8", textTransform: "uppercase", whiteSpace: "nowrap" }}>
                        Status: <span style={{ color: "#0F172A", marginLeft: "4px" }}>{healthStatus}</span>
                    </div>
                </div>

                {/* Legend */}
                <div style={{
                    display: "flex",
                    gap: "16px",
                    fontSize: "11px",
                    fontWeight: 600,
                    color: "#64748B",
                    textTransform: "uppercase"
                }}>
                    <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                        <div style={{ width: "10px", height: "10px", background: "#EFF6FF", border: "1px solid #BFDBFE", borderRadius: "2px" }}></div>
                        Normal Range
                    </div>
                    <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                        <div style={{ width: "10px", height: "10px", background: "#EF4444", borderRadius: "50%" }}></div>
                        Notable Change
                    </div>
                </div>
            </div>

            <div style={{ width: "100%", height: 280 }}>

            <ResponsiveContainer>
                <ComposedChart data={data} margin={{ top: 20, right: 20, left: -20, bottom: 0 }}>
                    <defs>
                        {/* Clean Light Blue Gradient */}
                        <linearGradient id="stabilityGradient" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="5%" stopColor="#3B82F6" stopOpacity={0.15} />
                            <stop offset="95%" stopColor="#3B82F6" stopOpacity={0.0} />
                        </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="#E2E8F0" vertical={false} />
                    <XAxis
                        dataKey="month"
                        axisLine={false}
                        tickLine={false}
                        tick={{ fill: "#64748B", fontSize: 11, fontWeight: 500 }}
                        dy={10}
                    />
                    <YAxis
                        domain={['dataMin - 0.2', 'dataMax + 0.2']}
                        hide
                    />
                    <Tooltip
                        content={({ active, payload }) => {
                            if (active && payload && payload.length) {
                                const d = payload[0].payload;
                                return (
                                    <div style={{
                                        background: "#FFFFFF",
                                        border: "1px solid #E2E8F0",
                                        padding: "16px",
                                        borderRadius: "12px",
                                        fontSize: "13px",
                                        boxShadow: "0 10px 15px -3px rgba(0, 0, 0, 0.08), 0 4px 6px -2px rgba(0, 0, 0, 0.04)"
                                    }}>
                                        <div style={{ fontWeight: 700, color: "#0F172A", marginBottom: "8px", borderBottom: "1px solid #E2E8F0", paddingBottom: "6px" }}>
                                            {d.month}
                                        </div>
                                        <div style={{ color: "#64748B", marginBottom: "4px" }}>
                                            Happiness Level: <strong style={{ color: "#0F172A", fontSize: "14px" }}>{d.score}</strong>
                                        </div>
                                        {d.is_volatile && (
                                            <div style={{
                                                marginTop: "12px",
                                                fontSize: "11px",
                                                fontWeight: 800,
                                                color: "#DC2626",
                                                background: "#FEF2F2",
                                                border: "1px solid #FECACA",
                                                padding: "4px 8px",
                                                borderRadius: "6px",
                                                textAlign: "center",
                                                letterSpacing: "0.5px"
                                            }}>
                                                ⚠️ NOTABLE SHIFT
                                            </div>
                                        )}
                                    </div>
                                );
                            }
                            return null;
                        }}
                    />
                    {/* Shaded Stability Band (Area) */}
                    <Area
                        type="monotone"
                        dataKey="upper_band"
                        stroke="none"
                        fill="url(#stabilityGradient)"
                        baseLine={({ payload }) => payload.lower_band}
                    />
                    {/* The Sentiment Line - Primary Blue */}
                    <Line
                        type="monotone"
                        dataKey="score"
                        stroke="#3B82F6"
                        strokeWidth={3}
                        dot={{ r: 4, fill: "#3B82F6", strokeWidth: 0 }}
                        activeDot={{ r: 6, fill: "#FFFFFF", stroke: "#3B82F6", strokeWidth: 2 }}
                        animationDuration={1500}
                        onClick={(data) => onStabilityClick && onStabilityClick(data.month)}
                        style={{ cursor: onStabilityClick ? 'pointer' : 'default' }}
                    />
                    {/* Scatter for Volatility Points - Rose Red */}
                    <Scatter
                        data={data.filter(d => d.is_volatile)}
                        fill="#EF4444"
                        stroke="#FFFFFF"
                        strokeWidth={2}
                        r={6}
                        onClick={(data) => onStabilityClick && onStabilityClick(data.month)}
                        style={{ cursor: onStabilityClick ? 'pointer' : 'default' }}
                    />
                </ComposedChart>
            </ResponsiveContainer>
        </div>
    </div>
    );
};

export default SentimentStabilityChart;