import React, { useState, useEffect } from "react";
import api from "../services/api";

const VanguardAlerts = ({ range }) => {
    const [alerts, setAlerts] = useState([]);
    const [loading, setLoading] = useState(true);

    const fetchAlerts = async () => {
        setLoading(true);
        try {
            const limitMonths = range === "3M" ? 3 : range === "6M" ? 6 : range === "12M" ? 12 : 3;
            const res = await api.get("/dashboard/intelligence-alerts", { params: { limit_months: limitMonths } });
            setAlerts(res.data.alerts || []);
        } catch (err) {
            console.error("Signal Center Error:", err);
            setAlerts([]);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchAlerts();
        const interval = setInterval(fetchAlerts, 60000); // Polling every minute
        return () => clearInterval(interval);
    }, [range]);

    if (loading && alerts.length === 0) return null;
    if (alerts.length === 0) return null;

    return (
        <div style={{
            background: 'rgba(255, 255, 255, 0.02)',
            backdropFilter: 'blur(20px)',
            borderRadius: '12px',
            border: '1px solid rgba(255, 255, 255, 0.08)',
            padding: '24px',
            marginBottom: '30px',
            position: 'relative',
            overflow: 'hidden'
        }}>
            {/* Live Signal Pulse */}
            <div style={{
                position: 'absolute',
                top: '24px',
                left: '24px',
                display: 'flex',
                alignItems: 'center',
                gap: '12px'
            }}>
                <div style={{
                    width: '8px',
                    height: '8px',
                    borderRadius: '50%',
                    background: '#ff3b3b',
                    boxShadow: '0 0 10px #ff3b3b',
                    animation: 'pulse 2s infinite'
                }} />
                <span style={{ 
                    fontSize: '11px', 
                    fontWeight: 800, 
                    letterSpacing: '0.1em', 
                    color: '#ff3b3b',
                    textTransform: 'uppercase'
                }}>
                    Vanguard Signal Center // Active
                </span>
            </div>

            <div style={{ marginTop: '30px', display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))', gap: '16px' }}>
                {alerts.map((alert) => (
                    <div key={alert.id} style={{
                        background: alert.severity === 'CRITICAL' ? 'rgba(229, 9, 20, 0.08)' : 'rgba(255, 255, 255, 0.03)',
                        border: `1px solid ${alert.severity === 'CRITICAL' ? 'rgba(229, 9, 20, 0.3)' : 'rgba(255, 255, 255, 0.1)'}`,
                        borderRadius: '10px',
                        padding: '16px',
                        transition: 'transform 0.2s',
                        cursor: 'default',
                        display: 'flex',
                        flexDirection: 'column',
                        gap: '10px'
                    }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                            <span style={{ 
                                fontSize: '10px', 
                                fontWeight: 900, 
                                padding: '2px 8px', 
                                borderRadius: '4px',
                                background: alert.severity === 'CRITICAL' ? '#E50914' : alert.severity === 'HIGH' ? '#f39c12' : '#444',
                                color: '#fff'
                            }}>
                                {alert.severity}
                            </span>
                            {alert.is_anomaly && (
                                <span style={{ fontSize: '14px' }} title="Statistical Anomaly">📈</span>
                            )}
                        </div>

                        <div>
                            <h4 style={{ margin: '0 0 4px 0', fontSize: '15px', color: '#fff' }}>{alert.category}</h4>
                            <p style={{ margin: 0, fontSize: '12px', color: '#aaa', lineHeight: 1.4 }}>{alert.message}</p>
                        </div>

                        {alert.link && (
                            <div style={{ 
                                marginTop: '4px',
                                padding: '8px', 
                                background: 'rgba(255,255,255,0.03)', 
                                borderRadius: '6px',
                                fontSize: '11px',
                                color: '#888',
                                borderLeft: '2px solid #00A8E1'
                            }}>
                                🔗 <strong>Potential Root Cause:</strong> Linked with <u>{alert.link.linked_to}</u> ({Math.floor(alert.link.score * 100)}% correlation)
                            </div>
                        )}
                    </div>
                ))}
            </div>

            <style>{`
                @keyframes pulse {
                    0% { transform: scale(1); opacity: 1; }
                    50% { transform: scale(1.5); opacity: 0.5; }
                    100% { transform: scale(1); opacity: 1; }
                }
            `}</style>
        </div>
    );
};

export default VanguardAlerts;
