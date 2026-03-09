import React, { useState, useEffect } from "react";
import {
    Radar,
    RadarChart,
    PolarGrid,
    PolarAngleAxis,
    PolarRadiusAxis,
    ResponsiveContainer,
    Tooltip
} from 'recharts';
import api from '../services/api';
import { SkeletonChart } from './Skeleton';

const VanguardAspectMap = ({ range, onAspectClick }) => {
    const [data, setData] = useState([]);
    const [loading, setLoading] = useState(true);

    const fetchAspects = async () => {
        setLoading(true);
        try {
            const limitMonths = range === "3M" ? 3 : range === "6M" ? 6 : range === "12M" ? 12 : 3;
            const res = await api.get("/dashboard/aspects", { params: { limit_months: limitMonths } });
            setData(res.data || []);
        } catch (err) {
            console.error("Vanguard Map Error:", err);
            setData([]);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchAspects();
    }, [range]);

    // Clean Light Theme Color logic based on sentiment_score (1.0 - 5.0)
    const getIntensityColor = (score) => {
        if (score >= 4.0) return "#EF4444"; // Critical - Rose Red
        if (score >= 3.0) return "#F59E0B"; // High - Amber
        if (score >= 2.5) return "#3B82F6"; // Watch - Primary Blue
        return "#10B981"; // Stable - Emerald Green
    };

    if (loading && data.length === 0) return <SkeletonChart height={300} />;
    if (data.length === 0) return null;

    return (
        <div style={{ width: '100%', display: 'flex', flexDirection: 'column', position: 'relative' }}>

            {/* Optional Subtitle */}
            <h3 title="A breakdown showing which product areas have the most complaints and how satisfaction is changing" style={{
                margin: '0 0 10px 0',
                fontSize: '11px',
                fontWeight: 700,
                letterSpacing: '0.05em',
                color: '#64748B',
                textTransform: 'uppercase'
            }}>
                Problem Breakdown
            </h3>

            <div style={{ position: "relative", width: "100%", height: "280px" }}>
                {/* Soft Light Theme Radial Background */}
                <div style={{
                    position: "absolute",
                    top: "50%",
                    left: "50%",
                    transform: "translate(-50%, -50%)",
                    width: "200px",
                    height: "200px",
                    background: "radial-gradient(circle, rgba(59, 130, 246, 0.08) 0%, rgba(59, 130, 246, 0) 70%)",
                    pointerEvents: "none",
                    zIndex: 0
                }} />

                <ResponsiveContainer width="100%" height="100%">
                    <RadarChart cx="50%" cy="50%" outerRadius="75%" data={data}>
                        <PolarGrid stroke="#E2E8F0" />
                        <PolarAngleAxis
                            dataKey="aspect"
                            tick={({ x, y, payload }) => {
                                const item = data.find(d => d.aspect === payload.value);
                                return (
                                    <g transform={`translate(${x},${y})`}>
                                        <text
                                            x={0}
                                            y={0}
                                            dy={4}
                                            textAnchor="middle"
                                            fill={getIntensityColor(item?.sentiment_score || 2)}
                                            style={{ fontSize: '11px', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.02em' }}
                                        >
                                            {payload.value}
                                        </text>
                                    </g>
                                );
                            }}
                        />
                        <PolarRadiusAxis axisLine={false} tick={false} />
                        <Radar
                            name="Risk Level"
                            dataKey="mentions"
                            stroke="#3B82F6"
                            strokeWidth={2}
                            fill="url(#radarGradient)"
                            fillOpacity={0.6}
                            onClick={(data) => onAspectClick && onAspectClick(data.top_topic || data.aspect)}
                            style={{
                                cursor: onAspectClick ? 'pointer' : 'default'
                                // Removed the heavy drop-shadow for a flatter look
                            }}
                        />
                        <Tooltip
                            content={({ active, payload }) => {
                                if (active && payload && payload.length) {
                                    const d = payload[0].payload;
                                    return (
                                        <div style={{
                                            background: '#FFFFFF',
                                            border: '1px solid #E2E8F0',
                                            padding: '16px',
                                            borderRadius: '12px',
                                            fontSize: '13px',
                                            boxShadow: '0 10px 15px -3px rgba(0, 0, 0, 0.08), 0 4px 6px -2px rgba(0, 0, 0, 0.04)'
                                        }}>
                                            <div style={{ fontWeight: 800, color: getIntensityColor(d.sentiment_score), marginBottom: '10px', fontSize: '14px', borderBottom: '1px solid #E2E8F0', paddingBottom: '6px' }}>
                                                {d.aspect}
                                            </div>
                                            <div style={{ color: '#64748B', marginBottom: '4px', fontWeight: 500 }}>
                                                Complaints Found: <strong style={{ color: '#0F172A' }}>{d.mentions}</strong>
                                            </div>
                                            <div style={{ color: '#64748B', marginBottom: '4px', fontWeight: 500 }}>
                                                Happiness Score: <strong style={{ color: '#0F172A' }}>{d.sentiment_score}/5.0</strong>
                                            </div>
                                            <div style={{ color: '#64748B', marginBottom: '10px', fontWeight: 500 }}>
                                                Recent Trend: <strong style={{ color: d.momentum_pct > 0 ? '#EF4444' : '#10B981' }}>
                                                    {d.momentum_pct > 0 ? 'Getting Worse' : 'Improving'} ({Math.abs(d.momentum_pct)}%)
                                                </strong>
                                            </div>
                                            <div style={{ paddingTop: '10px', borderTop: '1px solid #E2E8F0', fontSize: '11px', color: '#64748B' }}>
                                                Main Issue: <span style={{ color: '#0F172A', fontWeight: 700 }}>{d.top_topic}</span>
                                            </div>
                                        </div>
                                    );
                                }
                                return null;
                            }}
                        />
                        <defs>
                            <linearGradient id="radarGradient" x1="0" y1="0" x2="0" y2="1">
                                <stop offset="5%" stopColor="#3B82F6" stopOpacity={0.4} />
                                <stop offset="95%" stopColor="#3B82F6" stopOpacity={0.05} />
                            </linearGradient>
                        </defs>
                    </RadarChart>
                </ResponsiveContainer>
            </div>

            {/* Bottom Momentum Badges */}
            <div style={{
                display: 'flex',
                justifyContent: 'center',
                gap: '24px',
                marginTop: '16px',
                borderTop: '1px solid #E2E8F0',
                paddingTop: '16px'
            }}>
                {data.map(item => (
                    <div
                        key={item.aspect}
                        style={{ textAlign: 'center', cursor: onAspectClick ? 'pointer' : 'default' }}
                        onClick={() => onAspectClick && onAspectClick(item.top_topic || item.aspect)}
                    >
                        <div style={{ fontSize: '11px', color: '#64748B', fontWeight: 700, textTransform: 'uppercase', marginBottom: '4px' }}>
                            {item.aspect.split('/')[0]}
                        </div>
                        <div title="Change in complaints for this category" style={{
                            fontSize: '11px',
                            fontWeight: 800,
                            color: item.momentum_pct > 0 ? '#EF4444' : '#10B981'
                        }}>
                            Complaints: {item.momentum_pct > 0 ? 'UP' : 'DOWN'}
                        </div>
                    </div>
                ))}
            </div>
        </div>
    );
};

export default VanguardAspectMap;