import React, { useState, useEffect } from "react";
import ReactMarkdown from "react-markdown";
import api from "../services/api";

export default function ExecutiveSummary({ range }) {
    const [summary, setSummary] = useState("");
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        fetchSummary();
    }, [range]);

    const fetchSummary = async () => {
        try {
            setLoading(true);
            let limit = 0;
            if (range === "3M") limit = 3;
            else if (range === "6M") limit = 6;
            else if (range === "12M") limit = 12;

            const res = await api.get("/dashboard/ai-summary", {
                params: { limit_months: limit }
            });
            setSummary(res.data.summary);
        } catch (err) {
            console.error(err);
            setSummary("> **System Offline:** Could not fetch insights from the analysis engine.");
        } finally {
            setLoading(false);
        }
    };

    if (loading) {
        return (
            <div className="glass-card" style={{ marginBottom: '32px', display: 'flex', alignItems: 'center' }}>
                <div style={{ marginRight: '16px', fontSize: '24px' }}>✨</div>
                <div>
                    <h3 style={{ margin: '0 0 4px 0', display: 'flex', alignItems: 'center', gap: '8px', color: '#0F172A', fontSize: '18px' }}>
                        Preparing Summary...
                    </h3>
                    <p style={{ margin: 0, color: '#64748B', fontSize: '14px' }}>Putting together the latest insights for you.</p>
                </div>
            </div>
        );
    }

    return (
        <div className="glass-card" style={{ marginBottom: '32px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
                <div style={{ display: 'flex', alignItems: 'center' }}>
                    <div style={{ marginRight: '12px', fontSize: '24px' }}>✨</div>
                    <h3 style={{ margin: 0, color: '#0F172A', fontSize: '18px', fontWeight: '700' }}>Executive Summary</h3>
                </div>
                <div style={{
                    fontSize: "11px", fontWeight: 700, color: "#64748B",
                    background: "#F8FAFC", padding: "6px 12px", borderRadius: "8px",
                    border: "1px solid #E2E8F0", letterSpacing: "0.5px"
                }}>
                    ANALYSIS OVERVIEW
                </div>
            </div>

            <div className="markdown-body" style={{ color: '#334155', lineHeight: '1.8', fontSize: '14px' }}>
                <ReactMarkdown
                    components={{
                        h3: ({ node, ...props }) => <h3 style={{ color: "#0F172A", borderBottom: "1px solid #E2E8F0", paddingBottom: "10px", marginBottom: "16px", marginTop: "24px", fontSize: "16px", fontWeight: "700" }} {...props} />,
                        p: ({ node, ...props }) => <p style={{ margin: "16px 0", color: "#475569" }} {...props} />,
                        ul: ({ node, ...props }) => <ul style={{ paddingLeft: "24px", margin: "16px 0", color: "#475569" }} {...props} />,
                        li: ({ node, ...props }) => <li style={{ marginBottom: '8px' }} {...props} />,
                        hr: ({ node, ...props }) => <hr style={{ border: 'none', borderTop: '1px solid #E2E8F0', margin: '24px 0' }} {...props} />,
                        strong: ({ node, ...props }) => <strong style={{ color: "#0F172A", fontWeight: 700 }} {...props} />,
                        blockquote: ({ node, ...props }) => (
                            <blockquote
                                style={{
                                    borderLeft: "4px solid #3B82F6",
                                    margin: "16px 0",
                                    padding: "12px 16px",
                                    background: "#EFF6FF",
                                    borderRadius: "0 8px 8px 0",
                                    fontStyle: "italic",
                                    color: "#1E293B"
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