import React, { useState, useEffect } from "react";
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, Brush } from "recharts";
import api from "../services/api";
import { SkeletonChart } from "./Skeleton";

// Clean Light Theme Color Palette
const COLORS = ["#3B82F6", "#8B5CF6", "#10B981", "#F59E0B", "#EF4444"];

export default function TrendingChart({ range, setRange }) {
    const [allData, setAllData] = useState([]);
    const [filteredData, setFilteredData] = useState([]);
    const [loading, setLoading] = useState(true);
    const [keys, setKeys] = useState([]);
    const [showBands, setShowBands] = useState(true);
    const [showForecast, setShowForecast] = useState(true);
    const [activeMetric, setActiveMetric] = useState("severity"); // "severity" or "revenue"

    const sliceData = (selectedRange, data = allData) => {
        if (!data.length) return;
        let sliced = [...data];
        if (selectedRange === "3M") sliced = data.slice(-3);
        else if (selectedRange === "6M") sliced = data.slice(-6);
        else if (selectedRange === "12M") sliced = data.slice(-12);
        setFilteredData(sliced);
    };

    const fetchTrendingData = async () => {
        setLoading(true);
        try {
            const limitMonths = range === "3M" ? 3 : range === "6M" ? 6 : range === "12M" ? 12 : 0;
            const res = await api.get("/dashboard/trending-issues", {
                params: { limit_months: limitMonths, metric: activeMetric }
            });
            const rawData = res.data;
            if (rawData.length > 0) {
                // Ignore metadata keys when registering the main interactive keys
                const firstRowKeys = Object.keys(rawData[0]).filter(k =>
                    k !== "month" &&
                    !k.endsWith("_upper_bound") &&
                    !k.endsWith("_mom") &&
                    !k.endsWith("_correlated_with") &&
                    k !== "is_forecast"
                );
                setKeys(firstRowKeys);
                setAllData(rawData);
                sliceData(range, rawData);
            } else {
                setAllData([]);
                setKeys([]);
                setFilteredData([]);
            }
        } catch (err) {
            console.error("Error fetching trending data:", err);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchTrendingData();
    }, [range, activeMetric]);

    if (loading) return <SkeletonChart height={360} />

    if (allData.length === 0) {
        return (
            <div style={{ height: "300px", display: "flex", alignItems: "center", justifyContent: "center" }}>
                <p style={{ color: "#64748B", fontWeight: 500 }}>No trending data available. Run analysis first.</p>
            </div>
        );
    }

    // Clean Light Theme Custom Tooltip
    const CustomTooltip = ({ active, payload, label }) => {
        if (active && payload && payload.length) {
            const isForecast = payload[0]?.payload?.is_forecast || false;
            const headerStyle = { margin: '0 0 10px 0', fontWeight: 700, borderBottom: '1px solid #E2E8F0', paddingBottom: '8px', fontSize: '14px' };

            return (
                <div style={{
                    background: '#FFFFFF',
                    border: '1px solid #E2E8F0',
                    padding: '16px',
                    borderRadius: '12px',
                    color: '#0F172A',
                    boxShadow: '0 10px 15px -3px rgba(0, 0, 0, 0.08), 0 4px 6px -2px rgba(0, 0, 0, 0.04)'
                }}>
                    {isForecast ? (
                        <p style={{ ...headerStyle, color: '#F59E0B' }}>{label} ⚡ Future Estimate</p>
                    ) : (
                        <p style={headerStyle}>{label}</p>
                    )}

                    {payload
                        .filter(entry =>
                            entry &&
                            entry.payload &&
                            entry.value !== undefined &&
                            entry.value !== null &&
                            // THIS IS THE FIX: Hides the faint background bands from the tooltip
                            !String(entry.name).endsWith("_upper_bound")
                        )
                        .slice()
                        .sort((a, b) => (b.value || 0) - (a.value || 0))
                        .map((entry, index) => {
                            const upperBoundKey = `${entry.name}_upper_bound`;
                            const upperBoundVal = entry.payload[upperBoundKey] || 0;
                                            const isAnomaly = (entry.value || 0) > upperBoundVal && upperBoundVal > 0 && !isForecast;

                            const momKey = `${entry.name}_mom`;
                            const momVal = entry.payload[momKey] || 0;
                            let momStr = "";
                            let momColor = "#64748B";

                            if (momVal > 0) {
                                momStr = `(Trending Up)`;
                                momColor = "#EF4444"; // Rose Red
                            } else if (momVal < 0) {
                                momStr = `(Trending Down)`;
                                momColor = "#10B981"; // Emerald Green
                            }

                            const corrKey = `${entry.name}_correlated_with`;
                            const corrVal = entry.payload[corrKey];

                            return (
                                <div key={`item-${index}`} style={{ margin: '10px 0' }}>
                                    <p style={{ margin: '0 0 3px 0', fontSize: '13px', color: entry.color, display: 'flex', alignItems: 'center', gap: '8px' }}>
                                        {isAnomaly && <span style={{ width: 6, height: 6, borderRadius: '50%', background: '#EF4444' }} />}
                                        <span style={{ fontWeight: 600 }}>{entry.name}:</span>
                                        <span style={{ color: '#0F172A', fontWeight: '800' }}>{Math.round(entry.value || 0)}</span>
                                        <span style={{ color: momColor, fontSize: '12px', marginLeft: '4px', fontWeight: 700 }}>{momStr}</span>
                                    </p>
                                    {corrVal && (
                                        <p style={{ margin: '0 0 0 14px', fontSize: '11px', color: '#64748B' }}>
                                            🔗 Also mentioned with: <span style={{ color: '#334155', fontWeight: 600 }}>{corrVal}</span>
                                        </p>
                                    )}
                                </div>
                            );
                        })}
                    <p style={{ margin: '15px 0 0', fontSize: '11px', color: '#94A3B8', fontWeight: 500 }}>
                        {activeMetric === "revenue" ? "Business Impact (Estimated $ Risk)" : "Priority Level (Higher = More Urgent)"}
                    </p>
                </div>
            );
        }
        return null;
    };

    return (
        <div style={{ width: '100% ' }}>
            {/* View Toggles & Badges - Clean Light Theme */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '24px', flexWrap: 'wrap', gap: '12px' }}>
                <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap' }}>
                    {/* CONFUSING BADGES REMOVED */}
                </div>

                {/* Dynamic UI Toggles */}
                <div style={{ display: 'flex', gap: '16px', background: '#F1F5F9', padding: '6px 14px', borderRadius: '12px', border: '1px solid #E2E8F0' }}>
                    <div style={{ display: "flex", gap: "4px" }}>
                        <button
                            title="Rank issues by how urgent they are to fix"
                            onClick={() => setActiveMetric("severity")}
                            style={{
                                padding: "6px 12px", borderRadius: "8px", border: "none", fontSize: "11px", fontWeight: 700,
                                background: activeMetric === "severity" ? "#FFFFFF" : "transparent",
                                color: activeMetric === "severity" ? "#3B82F6" : "#64748B", cursor: "pointer", transition: "all 0.2s",
                                boxShadow: activeMetric === "severity" ? "0 1px 3px rgba(0,0,0,0.1)" : "none"
                            }}
                        >PRIORITY</button>
                        <button
                            title="Rank issues by estimated cost to the business"
                            onClick={() => setActiveMetric("revenue")}
                            style={{
                                padding: "6px 12px", borderRadius: "8px", border: "none", fontSize: "11px", fontWeight: 700,
                                background: activeMetric === "revenue" ? "#FFFFFF" : "transparent",
                                color: activeMetric === "revenue" ? "#3B82F6" : "#64748B", cursor: "pointer", transition: "all 0.2s",
                                boxShadow: activeMetric === "revenue" ? "0 1px 3px rgba(0,0,0,0.1)" : "none"
                            }}
                        >BUSINESS IMPACT</button>
                    </div>

                    {/* Checkboxes */}
                    <div style={{ display: "flex", alignItems: "center", gap: "16px", borderLeft: "1px solid #CBD5E1", paddingLeft: "16px" }}>
                        <label title="Show expected range for mentions (Variance Band)" style={{ fontSize: '12px', color: '#475569', display: 'flex', alignItems: 'center', gap: '6px', cursor: 'pointer', fontWeight: 600 }}>
                            <input
                                type="checkbox"
                                checked={showBands}
                                onChange={(e) => setShowBands(e.target.checked)}
                                style={{ accentColor: '#3B82F6', width: '14px', height: '14px' }}
                            />
                            Normal Pattern
                        </label>
                        <label title="Show predicted trends based on historical data" style={{ fontSize: '12px', color: '#475569', display: 'flex', alignItems: 'center', gap: '6px', cursor: 'pointer', fontWeight: 600 }}>
                            <input
                                type="checkbox"
                                checked={showForecast}
                                onChange={(e) => setShowForecast(e.target.checked)}
                                style={{ accentColor: '#F59E0B', width: '14px', height: '14px' }}
                            />
                            Future Estimate
                        </label>
                    </div>
                </div>
            </div>

            <ResponsiveContainer width="100%" height={350}>
                <AreaChart
                    data={showForecast ? filteredData : filteredData.filter(d => !d.is_forecast)}
                    margin={{ top: 10, right: 30, left: 0, bottom: 0 }}
                >
                    <defs>
                        {keys.map((key, index) => (
                            <linearGradient key={`colorUv-${index}`} id={`colorUv-${index}`} x1="0" y1="0" x2="0" y2="1">
                                <stop offset="5%" stopColor={COLORS[index % COLORS.length]} stopOpacity={0.3} />
                                <stop offset="100%" stopColor={COLORS[index % COLORS.length]} stopOpacity={0.01} />
                            </linearGradient>
                        ))}
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="#E2E8F0" vertical={false} />
                    <XAxis
                        dataKey="month"
                        stroke="#94A3B8"
                        tick={{ fill: '#64748B', fontSize: 12, fontWeight: 500 }}
                        tickMargin={12}
                        axisLine={false}
                        tickLine={false}
                    />
                    <YAxis
                        stroke="#94A3B8"
                        tick={{ fill: '#64748B', fontSize: 12, fontWeight: 500 }}
                        tickFormatter={(val) => val === 0 ? '' : val}
                        domain={[0, 'auto']}
                        axisLine={false}
                        tickLine={false}
                    />
                    <Tooltip content={<CustomTooltip />} cursor={{ stroke: '#CBD5E1', strokeWidth: 1, strokeDasharray: '5 5' }} />
                    <Legend
                        wrapperStyle={{ paddingTop: "20px", color: "#475569", fontWeight: 600, fontSize: "13px" }}
                        iconType="circle"
                    />

                    {/* Clean Light Theme Scrubber */}
                    <Brush
                        dataKey="month"
                        height={24}
                        stroke="#CBD5E1"
                        fill="#F8FAFC"
                        tickFormatter={() => ""}
                        travellerWidth={8}
                        style={{ border: '1px solid #E2E8F0' }}
                    />

                    {/* Underlying Statistical Variance Bands (Soft Gray) */}
                    {showBands && keys.map((key, index) => (
                        <Area
                            key={`${key}_bound`}
                            type="monotone"
                            dataKey={`${key}_upper_bound`}
                            stroke="none"
                            fill="rgba(0, 0, 0, 0.04)"
                            isAnimationActive={false}
                            activeDot={false}
                            legendType="none"
                        />
                    ))}

                    {/* Main Signal Lines */}
                    {keys.map((key, index) => (
                        <Area
                            key={key}
                            type="monotone"
                            dataKey={key}
                            stroke={COLORS[index % COLORS.length]}
                            strokeWidth={2}
                            fillOpacity={1}
                            fill={`url(#colorUv-${index})`}
                            animationDuration={500}
                            dot={(props) => {
                                const { cx, cy, payload, dataKey } = props;
                                if (!payload) return null;

                                const upperBoundKey = `${dataKey}_upper_bound`;
                                const upperBoundVal = payload[upperBoundKey];

                                // Flat red dot for anomalies
                                if (showBands && payload[dataKey] > upperBoundVal && upperBoundVal > 0) {
                                    return (
                                        <circle
                                            key={`dot-${cx}-${cy}`}
                                            cx={cx} cy={cy} r={5}
                                            fill="#EF4444"
                                            stroke="#FFFFFF" strokeWidth={1.5}
                                        />
                                    );
                                }
                                return null;
                            }}
                        />
                    ))}
                </AreaChart>
            </ResponsiveContainer>
        </div>
    );
}