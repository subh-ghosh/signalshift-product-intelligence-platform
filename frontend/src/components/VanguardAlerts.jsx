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
        <div className="glass-card" style={{
            padding: '24px',
            marginBottom: '32px',
            position: 'relative',
            overflow: 'hidden',
            borderTop: '4px solid #EF4444' // Rose Red accent line to signify Alerts
        }}>
            {/* Live Signal Pulse - Clean Light Theme Styled */}
            <div style={{
                display: 'flex',
                alignItems: 'center',
                gap: '12px',
                marginBottom: '24px'
            }}>
                <div style={{
                    width: '10px',
                    height: '10px',
                    borderRadius: '50%',
                    background: '#EF4444',
                    animation: 'vanguard-pulse 2s infinite'
                }} />
                <span style={{
                    fontSize: '12px',
                    fontWeight: 800,
                    letterSpacing: '0.1em',
                    color: '#EF4444',
                    textTransform: 'uppercase'
                }}>
                    Important Highlights
                </span>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))', gap: '20px' }}>
                {alerts.map((alert) => {
                    // Map severities to Clean Light Theme palette
                    const isCritical = alert.severity === 'CRITICAL';
                    const isHigh = alert.severity === 'HIGH';

                    const bgGlow = isCritical ? '#FEF2F2' : isHigh ? '#FFFBEB' : '#F8FAFC';
                    const borderColor = isCritical ? '#FECACA' : isHigh ? '#FDE68A' : '#E2E8F0';
                    const badgeColor = isCritical ? '#EF4444' : isHigh ? '#F59E0B' : '#3B82F6';
                    const textColor = '#FFFFFF';

                    return (
                        <div key={alert.id} style={{
                            background: bgGlow,
                            border: `1px solid ${borderColor}`,
                            borderRadius: '12px',
                            padding: '20px',
                            transition: 'all 0.2s ease',
                            cursor: 'default',
                            display: 'flex',
                            flexDirection: 'column',
                            gap: '12px',
                            boxShadow: isCritical ? '0 4px 12px rgba(239, 68, 68, 0.1)' : '0 2px 4px rgba(0,0,0,0.02)'
                        }}
                            onMouseEnter={(e) => {
                                e.currentTarget.style.transform = "translateY(-2px)";
                            }}
                            onMouseLeave={(e) => {
                                e.currentTarget.style.transform = "translateY(0)";
                            }}
                        >
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                                <span style={{
                                    fontSize: '11px',
                                    fontWeight: 800,
                                    padding: '4px 10px',
                                    borderRadius: '6px',
                                    background: badgeColor,
                                    color: textColor,
                                    letterSpacing: '0.5px'
                                }}>
                                    {alert?.severity}
                                </span>
                                {alert?.is_anomaly && (
                                    <span style={{ fontSize: '16px' }} title="Unusual Pattern">📈</span>
                                )}
                            </div>

                            <div>
                                <h4 style={{ margin: '8px 0 6px 0', fontSize: '16px', color: '#0F172A', fontWeight: 700, letterSpacing: '-0.01em' }}>
                                    {alert?.category}
                                </h4>
                                <p style={{ margin: 0, fontSize: '13px', color: '#475569', lineHeight: 1.5, fontWeight: 500 }}>
                                    {(alert?.message || "")
                                        .replace(/Statistically out-of-control \(Limit: [\d.]+\)/g, "Unusually high number of mentions")
                                        .replace(/MoM spike of \+([\d.]+)%/g, (match, p1) => `Increased by ${Math.round(parseFloat(p1))}% since last month`)
                                        .replace(/Dominant Volume: Accounting for ([\d.]+)% of all feedback\./g, (match, p1) => `Top Topic: Makes up ${Math.round(parseFloat(p1))}% of all reviews.`)
                                    }
                                </p>
                            </div>

                            {alert?.link && (
                                <div style={{
                                    marginTop: '8px',
                                    padding: '12px',
                                    background: '#FFFFFF',
                                    border: '1px solid #E2E8F0',
                                    borderRadius: '8px',
                                    fontSize: '12px',
                                    color: '#64748B',
                                    borderLeft: `3px solid #3B82F6`, // Primary Blue Accent
                                    boxShadow: '0 1px 2px rgba(0,0,0,0.02)'
                                }}>
                                    🔗 <strong style={{ color: '#0F172A' }}>Related Issue:</strong> Linked with <u title="Topic that often appears alongside this one" style={{ color: '#334155', textUnderlineOffset: '2px', fontWeight: 600 }}>{alert?.link?.linked_to}</u> ({Math.floor((alert?.link?.score || 0) * 100)}% connection)
                                </div>
                            )}
                        </div>
                    );
                })}
            </div>

            <style>{`
                @keyframes vanguard-pulse {
                    0% { transform: scale(1); opacity: 1; box-shadow: 0 0 0 0 rgba(239, 68, 68, 0.4); }
                    70% { transform: scale(1.3); opacity: 0.5; box-shadow: 0 0 0 10px rgba(239, 68, 68, 0); }
                    100% { transform: scale(1); opacity: 1; box-shadow: 0 0 0 0 rgba(239, 68, 68, 0); }
                }
            `}</style>
        </div>
    );
};

export default VanguardAlerts;