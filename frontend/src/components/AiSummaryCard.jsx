import React, { useState, useEffect } from "react";
import ReactMarkdown from "react-markdown";
import api from "../services/api";

export default function AiSummaryCard() {
    const [summary, setSummary] = useState("");
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        fetchSummary();
    }, []);

    const fetchSummary = async () => {
        try {
            const res = await api.get("/dashboard/ai-summary");
            setSummary(res.data.summary);
        } catch (err) {
            console.error(err);
            setSummary("> **System Offline:** Could not fetch insights from the ML engine.");
        } finally {
            setLoading(false);
        }
    };

    if (loading) {
        return (
            <div className="glass-card ai-glow" style={{ marginBottom: '30px', padding: '25px', display: 'flex', alignItems: 'center' }}>
                <div style={{ marginRight: '15px', fontSize: '24px' }}>🤖</div>
                <div>
                    <h3 style={{ margin: '0 0 5px 0', display: 'flex', alignItems: 'center', gap: '8px' }}>
                        SignalShift Vanguard AI <span className="pulsing-dot"></span>
                    </h3>
                    <p style={{ margin: 0, color: '#888', fontStyle: 'italic' }}>Synthesizing mathematical outputs...</p>
                </div>
            </div>
        );
    }

    return (
        <div className="glass-card ai-glow" style={{ marginBottom: '30px', padding: '25px' }}>
            <div style={{ display: 'flex', alignItems: 'center', marginBottom: '15px' }}>
                <div style={{ marginRight: '15px', fontSize: '24px' }}>🤖</div>
                <h3 style={{ margin: 0 }}>SignalShift Vanguard AI</h3>
            </div>
            <div className="markdown-body" style={{ color: '#eee', lineHeight: '1.6', fontSize: '15px' }}>
                <ReactMarkdown
                    components={{
                        p: ({node, ...props}) => <p style={{ margin: "0 0 10px 0" }} {...props} />,
                        ul: ({node, ...props}) => <ul style={{ paddingLeft: "20px", margin: "10px 0", listStyleType: "circle" }} {...props} />,
                        li: ({node, ...props}) => <li style={{ marginBottom: "8px" }} {...props} />,
                        strong: ({node, ...props}) => <strong style={{ color: "#E50914" }} {...props} />,
                        blockquote: ({node, ...props}) => (
                            <blockquote 
                                style={{ 
                                    borderLeft: "4px solid #E50914", 
                                    margin: "10px 0", 
                                    padding: "10px 15px", 
                                    background: "rgba(229, 9, 20, 0.05)",
                                    borderRadius: "0 4px 4px 0",
                                    fontStyle: "italic",
                                    color: "#ccc"
                                }} 
                                {...props} 
                            />
                        )
                    }}
                >
                    {summary}
                </ReactMarkdown>
            </div>
        </div>
    );
}
