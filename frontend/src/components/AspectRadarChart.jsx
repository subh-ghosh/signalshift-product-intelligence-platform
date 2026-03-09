import {
    Radar,
    RadarChart,
    PolarGrid,
    PolarAngleAxis,
    PolarRadiusAxis,
    ResponsiveContainer,
    Tooltip
} from 'recharts';
import { useEffect, useState } from 'react';
import api from '../services/api';
import { SkeletonChart } from './Skeleton';

export default function AspectRadarChart({ limitMonths = 0 }) {
    const [data, setData] = useState([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const fetchAspects = async () => {
            setLoading(true);
            try {
                const res = await api.get("/dashboard/aspects", { params: { limit_months: limitMonths } });
                const filteredData = (res.data || []).filter(item => item.aspect !== "General");
                setData(filteredData);
            } catch (err) {
                console.error("Failed to load aspects", err);
            } finally {
                setLoading(false);
            }
        };
        fetchAspects();
    }, [limitMonths]);

    if (loading) return <SkeletonChart height={300} />;

    if (data.length === 0) return (
        <p style={{ textAlign: 'center', color: '#64748B', padding: "40px 0" }}>
            No aspect data available yet.
        </p>
    );

    return (
        <div style={{ width: "100%", height: "100%", minHeight: 320, display: "flex", flexDirection: "column" }}>
            <ResponsiveContainer width="100%" height={280}>
                <RadarChart cx="50%" cy="50%" outerRadius="75%" data={data}>
                    {/* Light, subtle grid lines */}
                    <PolarGrid stroke="#E2E8F0" />

                    {/* Clean slate text for the categories */}
                    <PolarAngleAxis
                        dataKey="aspect"
                        tick={{ fill: '#475569', fontSize: 11, fontWeight: 600 }}
                    />

                    <PolarRadiusAxis axisLine={false} tick={false} />

                    {/* Professional Blue Radar Polygon */}
                    <Radar
                        name="Mentions"
                        dataKey="mentions"
                        stroke="#3B82F6"
                        strokeWidth={2}
                        fill="#3B82F6"
                        fillOpacity={0.15}
                    />

                    {/* Clean Light Theme Tooltip */}
                    <Tooltip
                        contentStyle={{
                            backgroundColor: '#FFFFFF',
                            border: '1px solid #E2E8F0',
                            color: '#0F172A',
                            borderRadius: '8px',
                            boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.03)',
                            fontWeight: 600,
                            fontSize: '13px'
                        }}
                        itemStyle={{ color: '#3B82F6', fontWeight: 700 }}
                    />
                </RadarChart>
            </ResponsiveContainer>

            <p style={{ textAlign: 'center', fontSize: '12px', color: '#94A3B8', marginTop: 'auto', paddingTop: '16px' }}>
                Detected Business Categories
            </p>
        </div>
    );
}