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

    if (loading) return <p style={{ textAlign: 'center', color: '#666' }}>Loading specialized aspects...</p>;
    if (data.length === 0) return <p style={{ textAlign: 'center', color: '#666' }}>No aspect data available yet.</p>;

    return (
        <div style={{ width: "100%", height: 400, background: 'rgba(255,255,255,0.02)', borderRadius: '15px', padding: '20px' }}>
            <ResponsiveContainer>
                <RadarChart cx="50%" cy="50%" outerRadius="80%" data={data}>
                    <PolarGrid stroke="#444" />
                    <PolarAngleAxis dataKey="aspect" tick={{ fill: '#E50914', fontSize: 12 }} />
                    <PolarRadiusAxis stroke="#666" />
                    <Radar
                        name="Mentions"
                        dataKey="mentions"
                        stroke="#E50914"
                        fill="#E50914"
                        fillOpacity={0.6}
                    />
                    <Tooltip 
                        contentStyle={{ backgroundColor: '#141414', border: '1px solid #444', color: '#fff' }}
                    />
                </RadarChart>
            </ResponsiveContainer>
            <p style={{ textAlign: 'center', fontSize: '12px', color: '#888', marginTop: '10px' }}>
                AI-Detected Business Categories (ABSA)
            </p>
        </div>
    );
}
