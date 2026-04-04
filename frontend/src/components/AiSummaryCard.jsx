import React, { useEffect, useMemo, useState } from "react";
import api from "../services/api";

function cleanSummaryMarkdown(text = "") {
    return text
        .replace(/[\u{1F300}-\u{1FAFF}\u{2600}-\u{27BF}]/gu, "")
        .replace(/[ \t]{2,}/g, " ")
        .replace(/\n{3,}/g, "\n\n")
        .replace(/###\s+Primary Focus:\s*/g, "### Primary Focus: ")
        .replace(/###\s+Suggested Action/g, "### Suggested Action")
        .replace(/###\s+General App Health/g, "### General App Health")
        .replace(/###\s+What Customers are Saying/g, "### What Customers are Saying")
        .replace(/\*\*Status:\*\*\s*/g, "**Status:** ")
        .trim();
}

function stripMarkdown(text = "") {
    return text
        .replace(/\*\*(.*?)\*\*/g, "$1")
        .replace(/\*(.*?)\*/g, "$1")
        .replace(/^>\s?/gm, "")
        .replace(/^-\s?/gm, "")
        .replace(/\s{2,}/g, " ")
        .trim();
}

function parseSummary(summary = "") {
    const cleaned = cleanSummaryMarkdown(summary);
    const sections = cleaned
        .split(/\n-{3,}\n/g)
        .map((part) => part.trim())
        .filter(Boolean)
        .map((part) => {
            const lines = part.split("\n").filter(Boolean);
            const heading = stripMarkdown((lines[0] || "").replace(/^###\s*/, ""));
            return {
                heading,
                body: lines.slice(1).join("\n").trim(),
                plain: stripMarkdown(lines.slice(1).join(" ").trim()),
            };
        });

    const focus = sections.find((section) => section.heading.startsWith("Primary Focus")) || sections[0];
    const action = sections.find((section) => section.heading === "Suggested Action");
    const health = sections.find((section) => section.heading === "General App Health");
    const voice = sections.find((section) => section.heading === "What Customers are Saying");

    const focusTopic = focus?.heading.split(":")[1]?.trim() || "Executive Focus";
    const focusSummary = stripMarkdown(focus?.body || "")
        .replace(/^Current Situation:\s*/i, "")
        .trim();
    const actionSummary = stripMarkdown(action?.body || "No recommended action was generated.")
        .replace(/^(Action|Urgent|Standard):\s*/i, "")
        .trim();
    const healthLines = (health?.body || "")
        .split("\n")
        .map((line) => stripMarkdown(line))
        .filter(Boolean);
    const statusLine = healthLines.find((line) => line.startsWith("Status:")) || "Status: Monitoring is active.";
    const watchLine = healthLines.find((line) => line.startsWith("Watch Out:")) || "";
    const categoryLines = healthLines
        .filter((line) => !line.startsWith("Status:") && !line.startsWith("Category Performance:") && !line.startsWith("Watch Out:"))
        .slice(0, 3);
    const voiceQuote = stripMarkdown(voice?.body || "No representative customer quote was available.");

    return {
        focusTopic,
        focusSummary,
        actionSummary,
        statusLine,
        watchLine,
        categoryLines,
        voiceQuote,
    };
}

function BriefSection({ label, title, body, lines = [], tone = "neutral", quote = false }) {
    return (
        <section className={`executive-brief-card executive-brief-card--${tone}`}>
            <div className="executive-brief-card__eyebrow">{label}</div>
            <h3>{title}</h3>
            {body && !quote && <p>{body}</p>}
            {lines.length > 0 && (
                <div className="executive-brief-card__lines">
                    {lines.map((line) => (
                        <div key={line} className="executive-brief-card__line">
                            {line}
                        </div>
                    ))}
                </div>
            )}
            {quote && <blockquote className="executive-brief-card__quote">{body}</blockquote>}
        </section>
    );
}

export default function ExecutiveSummary({ range }) {
    const [summary, setSummary] = useState("");
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        let ignore = false;

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

                if (!ignore) {
                    setSummary(res.data.summary || "");
                }
            } catch (err) {
                console.error(err);
                if (!ignore) {
                    setSummary("> **System Offline:** Could not fetch insights from the analysis engine.");
                }
            } finally {
                if (!ignore) {
                    setLoading(false);
                }
            }
        };

        fetchSummary();

        return () => {
            ignore = true;
        };
    }, [range]);

    const model = useMemo(() => parseSummary(summary), [summary]);

    if (loading) {
        return (
            <div className="glass-card summary-surface executive-summary executive-summary--loading">
                <div>
                    <div className="eyebrow executive-summary__eyebrow">AI Summary</div>
                    <h3 className="executive-summary__loading-title">Preparing executive brief...</h3>
                    <p className="executive-summary__loading-copy">Organizing the latest customer-signal narrative for this window.</p>
                </div>
            </div>
        );
    }

    return (
        <div className="glass-card summary-surface executive-summary">
            <div className="executive-summary__header">
                <div>
                    <div className="executive-summary__eyebrow">Executive Summary</div>
                    <h2>{model.focusTopic}</h2>
                    <p>{model.focusSummary || "No executive brief was generated for this window."}</p>
                </div>
                <span className="tag executive-summary__tag">Analysis Overview</span>
            </div>

            <div className="executive-summary__support">
                <BriefSection
                    label="Suggested Action"
                    title="Recommended next step"
                    body={model.actionSummary}
                    tone="action"
                />

                <section className="executive-brief-card executive-brief-card--health executive-brief-card--snapshot">
                    <div className="executive-brief-card__eyebrow">General App Health</div>
                    <h3>Current operating context</h3>
                    <p>{model.statusLine}</p>
                    <div className="executive-brief-card__snapshot">
                        {model.categoryLines.map((line) => (
                            <div key={line} className="executive-brief-card__snapshot-line">
                                {line}
                            </div>
                        ))}
                        {model.watchLine && (
                            <div className="executive-brief-card__snapshot-line executive-brief-card__snapshot-line--watch">
                                {model.watchLine}
                            </div>
                        )}
                    </div>
                </section>
            </div>

            <div className="executive-summary__quote-row">
                <BriefSection
                    label="Customer Voice"
                    title="Representative feedback"
                    body={model.voiceQuote}
                    tone="voice"
                    quote
                />
            </div>
        </div>
    );
}
