import React, { useState, useEffect } from "react";
import api from "../services/api";

const SignalTicker = () => {
    const [messages, setMessages] = useState([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const fetchTicker = async () => {
            try {
                const res = await api.get("/dashboard/live-ticker");
                setMessages(res.data || []);
            } catch (err) {
                console.error("Ticker fetch error:", err);
            } finally {
                setLoading(false);
            }
        };
        fetchTicker();
        const interval = setInterval(fetchTicker, 60000); // Refresh every minute
        return () => clearInterval(interval);
    }, []);

    if (loading || messages.length === 0) return null;

    return (
        <div style={{
            width: "100%",
            background: "#FFFFFF",
            borderBottom: "1px solid #E2E8F0",
            padding: "10px 0",
            overflow: "hidden",
            whiteSpace: "nowrap",
            position: "relative",
            zIndex: 100,
            display: "flex",
            alignItems: "center",
            boxShadow: "0 2px 4px rgba(0,0,0,0.02)"
        }}>
            <div style={{
                position: "absolute",
                left: 0,
                top: 0,
                bottom: 0,
                background: "#3B82F6", // Professional Primary Blue
                color: "#FFFFFF",
                display: "flex",
                alignItems: "center",
                padding: "0 20px",
                fontSize: "11px",
                fontWeight: 800,
                letterSpacing: "1px",
                zIndex: 2,
                boxShadow: "4px 0 10px rgba(0,0,0,0.05)"
            }}>
                LIVE FEEDBACK
            </div>

            <div className="ticker-scroll" style={{
                display: "inline-block",
                paddingLeft: "160px", // Offset for the label
                animation: "ticker 60s linear infinite",
                fontSize: "13px",
                color: "#334155" // Dark slate for readability
            }}>
                {messages.map((m, i) => (
                    <span key={i} style={{
                        marginRight: "60px",
                        display: "inline-flex",
                        alignItems: "center",
                        gap: "8px"
                    }}>
                        <span style={{
                            color: m.sentiment === "positive" ? "#10B981" : (m.sentiment === "negative" ? "#EF4444" : "#F59E0B"),
                            fontWeight: 800,
                            fontSize: "12px"
                        }}>
                            {m.sentiment === "positive" ? "● POSITIVE" : (m.sentiment === "negative" ? "● CRITICAL" : "● WATCH")}
                        </span>
                        <span style={{ color: "#94A3B8", fontWeight: 600 }}>
                            [{new Date(m.at).toLocaleDateString([], { month: 'short', day: 'numeric' })}]
                        </span>
                        <span style={{ fontStyle: m.sentiment === "negative" ? "italic" : "normal" }}>
                            "{m.text}..."
                        </span>
                    </span>
                ))}
            </div>

            <style>{`
                @keyframes ticker {
                    0% { transform: translateX(0); }
                    100% { transform: translateX(-50%); }
                }
                .ticker-scroll:hover {
                    animation-play-state: paused;
                }
            `}</style>
        </div>
    );
};

export default SignalTicker;