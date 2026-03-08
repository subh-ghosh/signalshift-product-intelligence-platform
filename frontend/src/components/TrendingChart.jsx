import React, { useState, useEffect } from "react";
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, Brush } from "recharts";
import api from "../services/api";
import { SkeletonChart } from "./Skeleton";

// Use the same premium, vibrant color palette from the Dashboard
const COLORS = ["#E50914", "#833AB4", "#1DB954", "#F4B400", "#00A8E1"];

export default function TrendingChart({ range, setRange }) {
    const [allData, setAllData] = useState([]);
    const [filteredData, setFilteredData] = useState([]);
    const [loading, setLoading] = useState(true);
    const [keys, setKeys] = useState([]);
    const [showBands, setShowBands] = useState(true);
    const [showForecast, setShowForecast] = useState(true);

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
            const res = await api.get("/dashboard/trending-issues", { params: { limit_months: limitMonths } });
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

    // Re-fetch from server when range changes
    useEffect(() => {
        fetchTrendingData();
    }, [range]);

    if (loading) return <SkeletonChart height={360} />

    if (allData.length === 0) {
        return (
            <div style={{ height: "300px", display: "flex", alignItems: "center", justifyContent: "center" }}>
                <p style={{ color: "#888" }}>No trending data available. Run analysis first.</p>
            </div>
        );
    }

    // Custom Tooltip for Glassmorphism Styling
    const CustomTooltip = ({ active, payload, label }) => {
        if (active && payload && payload.length) {
            // Safe access to payload properties
            const isForecast = payload[0]?.payload?.is_forecast || false;
            const headerStyle = { margin: '0 0 10px 0', fontWeight: 'bold', borderBottom: '1px solid #333', paddingBottom: '5px' };
            
            return (
                <div style={{
                    background: 'rgba(20, 20, 20, 0.9)',
                    border: '1px solid rgba(255,255,255,0.1)',
                    backdropFilter: 'blur(10px)',
                    padding: '15px',
                    borderRadius: '8px',
                    color: '#fff'
                }}>
                    {isForecast ? (
                        <p style={{ ...headerStyle, color: '#f39c12' }}>{label} ⚡ Projected Trajectory</p>
                    ) : (
                        <p style={headerStyle}>{label}</p>
                    )}
                    
                    {payload
                        .filter(entry => entry && entry.payload && entry.value !== undefined && entry.value !== null)
                        .slice()
                        .sort((a, b) => (b.value || 0) - (a.value || 0))
                        .map((entry, index) => {
                            // Check if this point is an anomaly based on the payload data
                            const upperBoundKey = `${entry.name}_upper_bound`;
                            const upperBoundVal = entry.payload[upperBoundKey] || 0;
                            const isAnomaly = (entry.value || 0) > upperBoundVal && upperBoundVal > 0 && !isForecast;
                            
                            // Momentum values
                            const momKey = `${entry.name}_mom`;
                            const momVal = entry.payload[momKey] || 0;
                            let momStr = "";
                            let momColor = "#888"; // neutral
                            
                            if (momVal > 0) {
                                momStr = `(▲ +${momVal}%)`;
                                momColor = "#ff4d4d"; // Red means bad (rate going up)
                            } else if (momVal < 0) {
                                momStr = `(▼ ${momVal}%)`;
                                momColor = "#00e676"; // Green means good (rate going down)
                            } else if (momVal === 0) {
                                momStr = `(- 0%)`;
                            }
                            
                            // Correlation mapping
                            const corrKey = `${entry.name}_correlated_with`;
                            const corrVal = entry.payload[corrKey];
                            
                            return (
                                <div key={`item-${index}`} style={{ margin: '8px 0' }}>
                                    <p style={{ margin: '0 0 3px 0', fontSize: '13px', color: entry.color, display: 'flex', alignItems: 'center', gap: '6px' }}>
                                        {isAnomaly && <span style={{ width: 6, height: 6, borderRadius: '50%', background: '#ff3b3b', boxShadow: '0 0 4px #ff3b3b' }} />}
                                        <span>{entry.name}:</span>
                                        <span style={{ color: '#fff', fontWeight: 'bold' }}>{(entry.value || 0).toFixed(1)}</span>
                                        <span style={{ color: momColor, fontSize: '11px', marginLeft: '4px' }}>{momStr}</span>
                                    </p>
                                    {corrVal && (
                                        <p style={{ margin: '0 0 0 12px', fontSize: '11px', color: '#aab' }}>
                                            🔗 Correlated softly with: {corrVal}
                                        </p>
                                    )}
                                </div>
                            );
                        })}
                    <p style={{ margin: '15px 0 0', fontSize: '10px', color: '#444' }}>Severity-weighted rate / 1k reviews (3-mo smoothed)</p>
                </div>
            );
        }
        return null;
    };

    return (
        <div style={{ width: '100%' }}>
            {/* View Toggles & Badges */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '15px', flexWrap: 'wrap', gap: '10px' }}>
                <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                    <span style={{ fontSize: '10px', color: '#555', background: 'rgba(255,255,255,0.04)', padding: '2px 8px', borderRadius: '4px', border: '1px solid #222' }}>
                        ✦ Severity-weighted per 1k reviews
                    </span>
                    <span style={{ fontSize: '10px', color: '#555', background: 'rgba(255,255,255,0.04)', padding: '2px 8px', borderRadius: '4px', border: '1px solid #222' }}>
                        ✦ 3-month rolling average
                    </span>
                    <span style={{ fontSize: '10px', color: '#555', background: 'rgba(255,255,255,0.04)', padding: '2px 8px', borderRadius: '4px', border: '1px solid #222' }}>
                        ✦ Pearson anomaly correlation
                    </span>
                </div>
                
                {/* Dynamic UI Toggles */}
                <div style={{ display: 'flex', gap: '15px', background: 'rgba(0,0,0,0.2)', padding: '6px 12px', borderRadius: '6px', border: '1px solid #333' }}>
                    <label style={{ fontSize: '11px', color: '#ccc', display: 'flex', alignItems: 'center', gap: '6px', cursor: 'pointer' }}>
                        <input 
                            type="checkbox" 
                            checked={showBands} 
                            onChange={(e) => setShowBands(e.target.checked)} 
                            style={{ accentColor: '#ff3b3b' }}
                        /> 
                        Show Variance Bands
                    </label>
                    <label style={{ fontSize: '11px', color: '#ccc', display: 'flex', alignItems: 'center', gap: '6px', cursor: 'pointer' }}>
                        <input 
                            type="checkbox" 
                            checked={showForecast} 
                            onChange={(e) => setShowForecast(e.target.checked)} 
                            style={{ accentColor: '#f39c12' }}
                        /> 
                        Show Predictive Forecast
                    </label>
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
                                <stop offset="5%" stopColor={COLORS[index % COLORS.length]} stopOpacity={0.5}/>
                                <stop offset="100%" stopColor={COLORS[index % COLORS.length]} stopOpacity={0}/>
                            </linearGradient>
                        ))}
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="#333" vertical={false} />
                    <XAxis 
                        dataKey="month" 
                        stroke="#888" 
                        tick={{ fill: '#888', fontSize: 12 }} 
                        tickMargin={10} 
                    />
                    <YAxis 
                        stroke="#888" 
                        tick={{ fill: '#888', fontSize: 12 }} 
                        tickFormatter={(val) => val === 0 ? '' : val} 
                        domain={[0, 'auto']}
                    />
                    <Tooltip content={<CustomTooltip />} />
                    <Legend 
                        wrapperStyle={{ paddingTop: "20px" }}
                        iconType="circle"
                    />
                    
                    {/* 0. Interactive Scrubber */}
                    <Brush 
                        dataKey="month" 
                        height={25} 
                        stroke="#444" 
                        fill="rgba(0,0,0,0.5)"
                        tickFormatter={() => ""}
                        travellerWidth={10}
                    />

                    {/* 1. Underlying Statistical Variance Bands (Conditional) */}
                    {showBands && keys.map((key, index) => (
                        <Area 
                            key={`${key}_bound`} 
                            type="monotone" 
                            dataKey={`${key}_upper_bound`} 
                            stroke="none" 
                            fill="rgba(50, 50, 50, 0.15)" 
                            isAnimationActive={false}
                            activeDot={false}
                            legendType="none"
                        />
                    ))}

                    {/* 2. Main Signal Lines with Conditional Anomaly Dots */}
                    {keys.map((key, index) => (
                        <Area 
                            key={key} 
                            type="monotone" 
                            dataKey={key} 
                            stroke={COLORS[index % COLORS.length]} 
                            fillOpacity={1} 
                            fill={`url(#colorUv-${index})`} 
                            animationDuration={500}
                            dot={(props) => {
                                const { cx, cy, payload, dataKey } = props;
                                if (!payload) return null;
                                
                                const upperBoundKey = `${dataKey}_upper_bound`;
                                const upperBoundVal = payload[upperBoundKey];
                                
                                // Only draw a dot if it's a statistical anomaly and the bound exists (and bounds are turned on)
                                if (showBands && payload[dataKey] > upperBoundVal && upperBoundVal > 0) {
                                    return (
                                        <circle 
                                            key={`dot-${cx}-${cy}`} 
                                            cx={cx} cy={cy} r={4} 
                                            fill="#ff3b3b" 
                                            stroke="#111" strokeWidth={1} 
                                            style={{ filter: 'drop-shadow(0 0 3px rgba(255,59,59,0.8))' }}
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
