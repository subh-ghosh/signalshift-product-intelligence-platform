import React, { useState, useEffect } from "react";
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from "recharts";
import api from "../services/api";

// Use the same premium, vibrant color palette from the Dashboard
const COLORS = ["#E50914", "#833AB4", "#1DB954", "#F4B400", "#00A8E1"];

export default function TrendingChart({ range, setRange }) {
    const [allData, setAllData] = useState([]);
    const [filteredData, setFilteredData] = useState([]);
    const [loading, setLoading] = useState(true);
    const [keys, setKeys] = useState([]);

    useEffect(() => {
        fetchTrendingData();
    }, []);

    useEffect(() => {
        sliceData(range);
    }, [range, allData]);

    const fetchTrendingData = async () => {
        try {
            const res = await api.get("/dashboard/trending-issues");
            const rawData = res.data;
            
            if (rawData.length > 0) {
                const firstRowKeys = Object.keys(rawData[0]).filter(k => k !== "month");
                setKeys(firstRowKeys);
                setAllData(rawData);
            }
        } catch (err) {
            console.error("Error fetching trending data:", err);
        } finally {
            setLoading(false);
        }
    };

    const sliceData = (selectedRange) => {
        if (!allData.length) return;
        
        let sliced = [...allData];
        if (selectedRange === "3M") sliced = allData.slice(-3);
        else if (selectedRange === "6M") sliced = allData.slice(-6);
        else if (selectedRange === "12M") sliced = allData.slice(-12);
        
        setFilteredData(sliced);
    };

    if (loading) {
        return (
            <div style={{ height: "300px", display: "flex", alignItems: "center", justifyContent: "center" }}>
                <p style={{ color: "#888" }}>Loading trend data...</p>
            </div>
        );
    }

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
            return (
                <div style={{
                    background: 'rgba(20, 20, 20, 0.9)',
                    border: '1px solid rgba(255,255,255,0.1)',
                    backdropFilter: 'blur(10px)',
                    padding: '15px',
                    borderRadius: '8px',
                    color: '#fff'
                }}>
                    <p style={{ margin: '0 0 10px 0', fontWeight: 'bold', borderBottom: '1px solid #333', paddingBottom: '5px' }}>{label}</p>
                    {payload.map((entry, index) => (
                        <p key={`item-${index}`} style={{ margin: '3px 0', fontSize: '13px', color: entry.color }}>
                            {entry.name}: <span style={{ color: '#fff' }}>{entry.value}</span>
                        </p>
                    ))}
                </div>
            );
        }
        return null;
    };

    return (
        <div style={{ width: '100%' }}>
            {/* Time Range Selector */}
            <div style={{ display: 'flex', gap: '10px', marginBottom: '20px', justifyContent: 'flex-end', paddingRight: '30px' }}>
                {["3M", "6M", "12M", "ALL"].map(r => (
                    <button 
                        key={r}
                        onClick={() => setRange(r)}
                        style={{
                            background: range === r ? '#E50914' : 'rgba(255,255,255,0.05)',
                            color: range === r ? '#fff' : '#ccc',
                            border: '1px solid',
                            borderColor: range === r ? '#E50914' : 'rgba(255,255,255,0.1)',
                            padding: '4px 12px',
                            borderRadius: '20px',
                            fontSize: '12px',
                            cursor: 'pointer',
                            transition: 'all 0.2s',
                            fontWeight: 'bold'
                        }}
                    >
                        {r}
                    </button>
                ))}
            </div>

            <ResponsiveContainer width="100%" height={350}>
                <AreaChart data={filteredData} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
                    <defs>
                        {keys.map((key, index) => (
                            <linearGradient key={`colorUv-${index}`} id={`colorUv-${index}`} x1="0" y1="0" x2="0" y2="1">
                                <stop offset="5%" stopColor={COLORS[index % COLORS.length]} stopOpacity={0.8}/>
                                <stop offset="95%" stopColor={COLORS[index % COLORS.length]} stopOpacity={0}/>
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
                    />
                    <Tooltip content={<CustomTooltip />} />
                    <Legend 
                        wrapperStyle={{ paddingTop: "20px" }}
                        iconType="circle"
                    />
                    {keys.map((key, index) => (
                        <Area 
                            key={key} 
                            type="monotone" 
                            dataKey={key} 
                            stroke={COLORS[index % COLORS.length]} 
                            fillOpacity={1} 
                            fill={`url(#colorUv-${index})`} 
                            animationDuration={500}
                        />
                    ))}
                </AreaChart>
            </ResponsiveContainer>
        </div>
    );
}
