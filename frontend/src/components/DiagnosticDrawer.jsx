import React, { useState, useEffect } from "react";
import api from "../services/api";
import { highlightEntities } from "../utils/highlight_utils.jsx";

function ReviewSurface({ review, keywordsString }) {
    const isEnterprise = review.user_tier === "Enterprise" || (review.value_weight && review.value_weight >= 4);
    const isPremium = review.user_tier === "Premium" || (review.value_weight && review.value_weight >= 2);

    return (
        <div
            className="evidence-modal__review"
            style={{
                border: `1px solid ${review.score <= 2 ? "rgba(234, 90, 106, 0.18)" : "rgba(148, 163, 184, 0.14)"}`,
            }}
        >
            <div style={{ display: "flex", justifyContent: "space-between", gap: 12, alignItems: "flex-start", marginBottom: 14 }}>
                <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
                    {isEnterprise && <span className="tag tag--warm">Enterprise</span>}
                    {isPremium && !isEnterprise && <span className="tag">Premium</span>}
                    <span style={{ color: "#e2a63c", fontSize: 12, fontWeight: 700 }}>
                        {"★".repeat(parseInt(review.score) || 0)}
                        {"☆".repeat(5 - (parseInt(review.score) || 0))}
                    </span>
                    {review.upvotes > 0 && <span className="muted-note">👍 {review.upvotes}</span>}
                </div>

                <div style={{ textAlign: "right" }}>
                    <div className="muted-note">{review.at ? String(review.at).split("T")[0] : "Recent"}</div>
                    {review.app_version && review.app_version !== "N/A" && review.app_version !== "Build N/A" && (
                        <div className="muted-note" style={{ fontSize: 11 }}>
                            Ver {review.app_version.replace("Build ", "")}
                        </div>
                    )}
                </div>
            </div>

            <div style={{ color: "#425069", lineHeight: 1.8, fontSize: 15, fontStyle: review.score <= 2 ? "italic" : "normal" }}>
                "{highlightEntities(review.text || "", keywordsString || "slow, crash, bug, error, login, payment, expensive, price, quality, feature")}"
            </div>

            {review.value_weight > 1 && (
                <div style={{ marginTop: 16, display: "flex", justifyContent: "flex-end" }}>
                    <span className="tag tag--warm">{review.value_weight.toFixed(1)}x Business Importance</span>
                </div>
            )}
        </div>
    );
}

const DiagnosticDrawer = ({ isOpen, onClose, aspect, month, topic, items, title, subtitle, keywordsString }) => {
    const [evidence, setEvidence] = useState([]);
    const [loading, setLoading] = useState(false);

    useEffect(() => {
        if (!isOpen) return;
        if (items && items.length) {
            setEvidence(items);
            setLoading(false);
            return;
        }

        let ignore = false;

        const fetchEvidence = async () => {
            try {
                setLoading(true);
                const res = await api.get("/dashboard/diagnostic-evidence", {
                    params: { aspect, month, topic }
                });
                if (!ignore) {
                    setEvidence(res.data || []);
                }
            } catch (err) {
                console.error("Evidence fetch error:", err);
                if (!ignore) {
                    setEvidence([]);
                }
            } finally {
                if (!ignore) {
                    setLoading(false);
                }
            }
        };

        fetchEvidence();

        return () => {
            ignore = true;
        };
    }, [isOpen, aspect, month, topic, items]);

    if (!isOpen) return null;

    const resolvedTitle = title || "Customer Comments";
    const resolvedSubtitle = subtitle || [month && `Period ${month}`, topic && `Focus ${topic}`, aspect && `Aspect ${aspect}`].filter(Boolean).join(" • ");

    return (
        <div className="evidence-modal__backdrop" onClick={onClose}>
            <div className="evidence-modal" onClick={(event) => event.stopPropagation()}>
                <div className="evidence-modal__header">
                    <div>
                        <span className="eyebrow">Evidence</span>
                        <h2>{resolvedTitle}</h2>
                        {resolvedSubtitle ? <p className="muted-note" style={{ marginTop: 8 }}>{resolvedSubtitle}</p> : null}
                    </div>
                    <button onClick={onClose} className="btn-secondary evidence-modal__close">
                        Close
                    </button>
                </div>

                <div className="evidence-modal__body">
                    {loading ? (
                        <div className="glass-card" style={{ textAlign: "center", padding: 32, background: "#ffffff" }}>
                            <div style={{ fontSize: 24, marginBottom: 12 }}>⏳</div>
                            <div className="muted-note">Loading evidence...</div>
                        </div>
                    ) : evidence.length > 0 ? (
                        evidence.map((rev, index) => (
                            <ReviewSurface key={`${rev.at || "row"}-${index}`} review={rev} keywordsString={keywordsString} />
                        ))
                    ) : (
                        <div className="glass-card" style={{ textAlign: "center", padding: 32, background: "#ffffff" }}>
                            <div className="muted-note">No specific evidence found for this cross-section.</div>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
};

export default DiagnosticDrawer;
