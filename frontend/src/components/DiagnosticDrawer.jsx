import React, { useState, useEffect } from "react";
import api from "../services/api";
import { highlightEntities } from "../utils/highlight_utils.jsx";

const DiagnosticDrawer = ({ isOpen, onClose, aspect, month, topic }) => {
    const [evidence, setEvidence] = useState([]);
    const [loading, setLoading] = useState(false);

    useEffect(() => {
        if (isOpen) {
            fetchEvidence();
        }
    }, [isOpen, aspect, month, topic]);

    const fetchEvidence = async () => {
        try {
            setLoading(true);
            const res = await api.get("/dashboard/diagnostic-evidence", {
                params: { aspect, month, topic }
            });
            setEvidence(res.data || []);
        } catch (err) {
            console.error("Evidence fetch error:", err);
        } finally {
            setLoading(false);
        }
    };

    if (!isOpen) return null;

    return (
        <div style={{
            position: "fixed",
            right: 0,
            top: 0,
            bottom: 0,
            width: "450px",
            background: "#FFFFFF", // Clean white background
            borderLeft: "1px solid #E2E8F0", // Subtle border
            zIndex: 1000,
            display: "flex",
            flexDirection: "column",
            boxShadow: "-10px 0 30px rgba(17, 12, 46, 0.08)", // Soft, widespread shadow
            color: "#0F172A", // Dark slate text
            padding: "32px",
            animation: "slideIn 0.4s cubic-bezier(0.16, 1, 0.3, 1)"
        }}>
            {/* Header Section */}
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "32px" }}>
                <div>
                    <h2 style={{ margin: 0, fontSize: "20px", color: "#0F172A", fontWeight: "800", letterSpacing: "-0.5px" }}>Customer Comments</h2>
                    <p style={{ margin: "4px 0 0 0", fontSize: "13px", color: "#64748B", fontWeight: "500" }}>
                        {month ? `Period: ${month}` : ""} {topic ? ` | Focus: ${topic}` : ""}
                    </p>
                </div>
                <button
                    onClick={onClose}
                    style={{
                        background: "#F1F5F9",
                        border: "1px solid #E2E8F0",
                        color: "#475569",
                        width: "32px",
                        height: "32px",
                        borderRadius: "8px",
                        cursor: "pointer",
                        fontSize: "18px",
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        transition: "all 0.2s ease"
                    }}
                    onMouseEnter={(e) => { e.currentTarget.style.background = "#E2E8F0"; e.currentTarget.style.color = "#0F172A"; }}
                    onMouseLeave={(e) => { e.currentTarget.style.background = "#F1F5F9"; e.currentTarget.style.color = "#475569"; }}
                >
                    ×
                </button>
            </div>

            {/* Evidence List */}
            <div style={{ flex: 1, overflowY: "auto", display: "flex", flexDirection: "column", gap: "16px", paddingRight: "8px" }}>
                {loading ? (
                    <div style={{ textAlign: "center", padding: "40px", color: "#64748B", fontWeight: "500" }}>
                        <div style={{ margin: "0 auto 12px auto", fontSize: "24px" }}>⏳</div>
                        Loading reviews...
                    </div>
                ) : evidence.length > 0 ? (
                    evidence.map((rev, i) => {
                        const isEnterprise = rev.user_tier === "Enterprise" || (rev.value_weight && rev.value_weight >= 4);
                        const isPremium = rev.user_tier === "Premium" || (rev.value_weight && rev.value_weight >= 2);

                        return (
                            <div key={i} style={{
                                padding: "20px",
                                background: "#F8FAFC",
                                borderRadius: "12px",
                                fontSize: "14px",
                                lineHeight: "1.6",
                                border: "1px solid #E2E8F0",
                                borderLeft: `4px solid ${rev.score <= 2 ? "#EF4444" : "#F59E0B"}` // Red for negative, Amber for neutral/positive
                            }}>
                                <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "12px", alignItems: "center" }}>
                                    <div style={{ display: "flex", gap: "8px", alignItems: "center" }}>
                                        {isEnterprise && (
                                            <span style={{
                                                fontSize: "10px", fontWeight: 800, background: "#EF4444", color: "#fff",
                                                padding: "2px 8px", borderRadius: "6px"
                                            }}>ENTERPRISE</span>
                                        )}
                                        {isPremium && !isEnterprise && (
                                            <span style={{
                                                fontSize: "10px", fontWeight: 800, background: "#F59E0B", color: "#fff",
                                                padding: "2px 8px", borderRadius: "6px"
                                            }}>PREMIUM</span>
                                        )}
                                        <span style={{ color: "#F59E0B", fontSize: "12px", fontWeight: 700 }}>
                                            {"★".repeat(parseInt(rev.score) || 0)}{"☆".repeat(5 - (parseInt(rev.score) || 0))}
                                        </span>
                                        {rev.upvotes > 0 && (
                                            <span style={{ fontSize: "12px", color: "#64748B", fontWeight: 700, marginLeft: "4px" }}>
                                                👍 {rev.upvotes}
                                            </span>
                                        )}
                                    </div>
                                    <div style={{ textAlign: "right" }}>
                                        <div style={{ fontSize: "12px", color: "#475569", fontWeight: 600 }}>
                                            {rev.at ? rev.at.split("T")[0] : "RECENT"}
                                        </div>
                                        {rev.app_version && rev.app_version !== "N/A" && rev.app_version !== "Build N/A" && (
                                            <div style={{ fontSize: "10px", color: "#94A3B8", fontWeight: 800, marginTop: "2px" }}>
                                                VER {rev.app_version.replace("Build ", "")}
                                            </div>
                                        )}
                                    </div>
                                </div>

                                <div style={{ color: "#334155", fontStyle: rev.score <= 2 ? "italic" : "normal" }}>
                                    "{highlightEntities(rev.text || "", "slow, crash, bug, error, login, payment, expensive, price, quality, feature")}"
                                </div>

                                {rev.value_weight > 1 && (
                                    <div style={{
                                        marginTop: "16px", display: "flex", justifyContent: "flex-end",
                                        paddingTop: "12px", borderTop: "1px solid #E2E8F0"
                                    }}>
                                        <span style={{
                                            fontSize: "11px", color: "#DC2626", fontWeight: 800,
                                            background: "#FEF2F2", padding: "2px 8px", borderRadius: "6px",
                                            border: "1px solid #FECACA"
                                        }}>
                                            {rev.value_weight.toFixed(1)}x BUSINESS IMPORTANCE
                                        </span>
                                    </div>
                                )}
                            </div>
                        );
                    })
                ) : (
                    <div style={{ textAlign: "center", padding: "40px", color: "#64748B", fontWeight: "500" }}>
                        No specific evidence found for this cross-section.
                    </div>
                )}
            </div>

            <style>{`
                @keyframes slideIn {
                    from { transform: translateX(100%); }
                    to { transform: translateX(0); }
                }
            `}</style>
        </div>
    );
};

export default DiagnosticDrawer;