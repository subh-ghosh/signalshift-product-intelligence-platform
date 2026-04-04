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
        const interval = setInterval(fetchTicker, 60000);
        return () => clearInterval(interval);
    }, []);

    if (loading || messages.length === 0) return null;

    return (
        <div style={{ width: "100%", overflow: "hidden", position: "relative", minHeight: 78 }}>
            <div
                style={{
                    position: "absolute",
                    left: 18,
                    top: "50%",
                    transform: "translateY(-50%)",
                    zIndex: 2,
                    padding: "8px 12px",
                    borderRadius: 999,
                    background: "linear-gradient(180deg, #f57e4d, #ef6437)",
                    color: "white",
                    fontSize: 10,
                    fontWeight: 800,
                    letterSpacing: "0.12em",
                    textTransform: "uppercase",
                }}
            >
                Live Feedback
            </div>

            <div
                className="ticker-scroll"
                style={{
                    display: "inline-block",
                    whiteSpace: "nowrap",
                    padding: "28px 18px 28px 144px",
                    animation: "ticker 72s linear infinite",
                    fontSize: 12,
                    color: "#56637a",
                }}
            >
                {messages.map((m, i) => (
                    <span
                        key={i}
                        style={{
                            marginRight: 54,
                            display: "inline-flex",
                            alignItems: "center",
                            gap: 8,
                        }}
                    >
                        <span
                            style={{
                                color: m.sentiment === "positive" ? "#2bb684" : (m.sentiment === "negative" ? "#ea5a6a" : "#e2a63c"),
                                fontWeight: 800,
                                fontSize: 10,
                                letterSpacing: "0.1em",
                            }}
                        >
                            {m.sentiment === "positive" ? "POSITIVE" : (m.sentiment === "negative" ? "CRITICAL" : "WATCH")}
                        </span>
                        <span style={{ color: "#93a0b3", fontWeight: 700 }}>
                            [{new Date(m.at).toLocaleDateString([], { month: "short", day: "numeric" })}]
                        </span>
                        <span style={{ color: "#455066" }}>"{m.text}..."</span>
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
