import os
import ast
import pandas as pd
from fpdf import FPDF
from datetime import datetime

class ReportService:
    def __init__(self, data_dir="data/processed"):
        self.data_dir = data_dir
        self.output_dir = "data/reports"
        os.makedirs(self.output_dir, exist_ok=True)

    def safe_text(self, text: str) -> str:
        if not text: return ""
        text = str(text)
        # Map common high-unicode to ASCII/Latin-1
        text = text.replace("\u2018", "'").replace("\u2019", "'").replace("\u201c", '"').replace("\u201d", '"')
        text = text.replace("\u2014", "--").replace("\u2013", "-").replace("\u2026", "...")
        text = text.replace("\u2b24", "*").replace("\u26a0", "!!").replace("\u25b2", "^")
        # Directional arrows
        text = text.replace("\u2191", "^").replace("\u2193", "v")
        return text.encode('latin-1', 'ignore').decode('latin-1')

    def generate_pdf_report(self, limit_months: int = 0):
        try:
            # Load Data
            aspect_df  = pd.read_csv(os.path.join(self.data_dir, "aspect_analysis.csv"))
            topic_df   = pd.read_csv(os.path.join(self.data_dir, "topic_analysis.csv"))

            # Apply time window filter for mention counts
            window_label = f"Last {limit_months} Months" if limit_months > 0 else "All Time"
            if limit_months > 0:
                try:
                    ts_df = pd.read_csv(os.path.join(self.data_dir, "topic_timeseries.csv"))
                    all_months = sorted(ts_df["month"].unique())
                    target_months = all_months[-limit_months:]
                    ts_filt = ts_df[ts_df["month"].isin(target_months)]
                    label_col = "topic_id" if "topic_id" in ts_filt.columns else "issue_label"
                    windowed = ts_filt.groupby(label_col)["mentions"].sum().reset_index()
                    windowed.columns = ["label", "windowed_mentions"]
                    topic_df = topic_df.merge(windowed, on="label", how="left")
                    topic_df["mentions"] = topic_df["windowed_mentions"].fillna(0).astype(int)
                    # Scale aspects proportionally
                    total_months = max(len(all_months), 1)
                    eff = min(limit_months, total_months)
                    scale = eff / total_months
                    aspect_df = aspect_df.copy()
                    aspect_df["mentions"] = (aspect_df["mentions"] * scale).round().astype(int)
                except Exception as e:
                    print(f"[PDF] Windowed filter error: {e}")

            topic_df = topic_df.sort_values("mentions", ascending=False)

            # Optional enrichment data
            quality_df  = None
            drift_df    = None
            emerging_df = None
            try:
                quality_df  = pd.read_csv(os.path.join(self.data_dir, "classification_quality.csv"))
            except Exception: pass
            try:
                drift_df = pd.read_csv(os.path.join(self.data_dir, "semantic_drift.csv"))
            except Exception: pass
            try:
                emerging_df = pd.read_csv(os.path.join(self.data_dir, "emerging_issues.csv"))
            except Exception: pass

            # Create PDF
            pdf = FPDF()
            pdf.add_page()

            # ── Header ──────────────────────────────────────────────────────
            pdf.set_fill_color(229, 9, 20)
            pdf.rect(0, 0, 210, 40, 'F')
            pdf.set_font("Helvetica", "B", 24)
            pdf.set_text_color(255, 255, 255)
            pdf.cell(0, 20, "SignalShift Intelligence", ln=True, align='C')
            pdf.set_font("Helvetica", "", 12)
            pdf.cell(0, 10, f"Executive Report  |  {window_label}  |  {datetime.now().strftime('%Y-%m-%d %H:%M')}", ln=True, align='C')
            pdf.ln(20)

            # ── KPI Summary with Period-over-Period Deltas ───────────────────
            try:
                reviews_df = None
                for fname in ["uploaded_reviews.csv", "cleaned_reviews.csv"]:
                    p = os.path.join(self.data_dir, fname)
                    if os.path.exists(p):
                        reviews_df = pd.read_csv(p)
                        break

                if reviews_df is not None:
                    has_dates = limit_months > 0 and "at" in reviews_df.columns

                    def _kpi(df):
                        tot = len(df)
                        avg_r = round(float(df["score"].mean()), 2) if "score" in df.columns and tot > 0 else None
                        pos = int((df["sentiment"] == "positive").sum()) if "sentiment" in df.columns else 0
                        pos_pct = round((pos / tot) * 100, 1) if tot > 0 else 0
                        return tot, avg_r, pos_pct

                    if has_dates:
                        reviews_df["at"] = pd.to_datetime(reviews_df["at"], errors="coerce")
                        now = pd.Timestamp.now()
                        curr_df = reviews_df[reviews_df["at"] >= now - pd.DateOffset(months=limit_months)]
                        prev_df = reviews_df[(reviews_df["at"] >= now - pd.DateOffset(months=limit_months * 2)) &
                                             (reviews_df["at"] < now - pd.DateOffset(months=limit_months))]
                    else:
                        curr_df = reviews_df
                        prev_df = pd.DataFrame()

                    tot, avg_r, pos_pct = _kpi(curr_df)
                    prev_tot, prev_r, prev_pos = _kpi(prev_df) if not prev_df.empty else (None, None, None)

                    def _arrow(cur, prv):
                        if prv is None or prv == 0: return ""
                        return " ^" if cur > prv else " v" if cur < prv else " ="

                    pdf.set_text_color(0, 0, 0)
                    pdf.set_font("Helvetica", "B", 14)
                    pdf.cell(0, 10, "Key Performance Indicators", ln=True)
                    pdf.set_font("Helvetica", "B", 9)
                    for col, w in [("Metric", 70), ("Value", 40), ("Prev Period", 40), ("Trend", 30)]:
                        pdf.cell(w, 8, col, border=1)
                    pdf.ln()
                    pdf.set_font("Helvetica", "", 9)
                    rows_kpi = [
                        ("Total Reviews", f"{tot:,}", f"{prev_tot:,}" if prev_tot else "N/A", _arrow(tot, prev_tot)),
                        ("Avg Star Rating", f"{avg_r}/5.0" if avg_r else "N/A", f"{prev_r}/5.0" if prev_r else "N/A", _arrow(avg_r, prev_r)),
                        ("Positive Sentiment", f"{pos_pct}%", f"{prev_pos}%" if prev_pos is not None else "N/A", _arrow(pos_pct, prev_pos)),
                    ]
                    for label, val, pval, trend in rows_kpi:
                        pdf.cell(70, 7, label, border=1)
                        pdf.cell(40, 7, val, border=1)
                        pdf.cell(40, 7, pval, border=1)
                        pdf.cell(30, 7, trend, border=1, ln=True)
                    pdf.ln(8)
            except Exception as e:
                print(f"[PDF] KPI section error: {e}")

            # ── Model Quality Card ───────────────────────────────────────────
            if quality_df is not None and not quality_df.empty:
                pdf.set_text_color(0, 0, 0)
                pdf.set_font("Helvetica", "B", 14)
                pdf.cell(0, 10, "Model Quality Snapshot", ln=True)
                pdf.set_font("Helvetica", "", 10)
                row = quality_df.iloc[0]
                sil = round(float(row.get("value", 0)), 4)
                n_cats = int(row.get("n_categories", 0))
                sil_label = "Excellent" if sil > 0.4 else ("Good" if sil > 0.25 else "Fair")
                pdf.cell(0, 7, f"  Silhouette Score: {sil}  ({sil_label})  |  Active Categories: {n_cats}", ln=True)
                pdf.cell(0, 7, f"  Confidence Threshold: {row.get('threshold_confidence', 0.30)}  |  Dedup Threshold: {row.get('dedup_threshold', 0.85)}", ln=True)
                pdf.ln(5)

            # ── 1. Business Aspect Intelligence ──────────────────────────────
            pdf.set_text_color(0, 0, 0)
            pdf.set_font("Helvetica", "B", 16)
            pdf.cell(0, 10, "1. Business Aspect Intelligence (ABSA)", ln=True)
            pdf.set_font("Helvetica", "", 11)
            pdf.multi_cell(0, 7, "Distribution of dissatisfaction signals across primary business categories.")
            pdf.ln(5)

            pdf.set_font("Helvetica", "B", 10)
            pdf.cell(100, 10, "Category", border=1)
            pdf.cell(40, 10, "Mentions", border=1)
            pdf.cell(40, 10, "Priority", border=1, ln=True)

            pdf.set_font("Helvetica", "", 10)
            total_mentions = aspect_df["mentions"].sum()
            for _, row in aspect_df.sort_values("mentions", ascending=False).iterrows():
                pct = (row["mentions"] / total_mentions) * 100 if total_mentions > 0 else 0
                priority = "CRITICAL" if pct > 20 else "NORMAL"
                pdf.cell(100, 8, self.safe_text(str(row["aspect"])), border=1)
                pdf.cell(40, 8, str(row["mentions"]), border=1)
                pdf.cell(40, 8, priority, border=1, ln=True)

            pdf.ln(10)

            # ── 2. Top Issue Clusters ─────────────────────────────────────────
            pdf.set_font("Helvetica", "B", 16)
            pdf.cell(0, 10, "2. Top Issue Clusters (MiniLM Semantic Classification)", ln=True)
            pdf.set_font("Helvetica", "", 11)
            pdf.multi_cell(0, 7, "Top 5 issues classified via direct cosine similarity against 12 canonical taxonomy categories:")
            pdf.ln(5)

            for rank, (_, row) in enumerate(topic_df.head(5).iterrows(), 1):
                # Phase 24+: label IS the canonical string
                label = self.safe_text(str(row.get("label", row.get("keywords", "Unknown"))))
                mentions = int(row["mentions"])
                avg_sev = float(row.get("avg_severity", 0.0))

                # Parse evidence
                try:
                    reviews = ast.literal_eval(row["sample_reviews"])
                except Exception:
                    rev_string = str(row["sample_reviews"]).strip('[]')
                    reviews = [r.strip(" '\"\n") for r in rev_string.split("', ") if r.strip()]

                evidence = self.safe_text((reviews[0][:160] + "...") if reviews else "No evidence available.")

                pdf.set_font("Helvetica", "B", 11)
                pdf.set_text_color(229, 9, 20)
                pdf.cell(0, 8, f"#{rank}  {label}", ln=True)

                pdf.set_text_color(50, 50, 50)
                pdf.set_font("Helvetica", "", 10)
                sev_bar = "*" * min(round(avg_sev), 5)  # Replaced filled circle with asterisk
                pdf.cell(0, 7, f"   Mentions: {mentions:,}   |   Avg Severity: {avg_sev:.1f}/5.0  {sev_bar}", ln=True)

                pdf.set_text_color(100, 100, 100)
                pdf.set_font("Helvetica", "I", 9)
                pdf.multi_cell(0, 6, f'   Evidence: "{evidence}"')

                pdf.set_text_color(0, 0, 0)
                pdf.ln(3)

            pdf.ln(5)

            # ── 3. Emerging Issues (if available) ───────────────────────────
            if emerging_df is not None and not emerging_df.empty:
                flagged = emerging_df[emerging_df.get("is_flagged", False) == True]
                if not flagged.empty:
                    pdf.add_page()
                    pdf.set_font("Helvetica", "B", 16)
                    pdf.set_text_color(229, 9, 20)
                    pdf.cell(0, 10, "3. [!!]  Emerging / Uncategorized Issues", ln=True)
                    pdf.set_text_color(0, 0, 0)
                    pdf.set_font("Helvetica", "", 11)
                    pdf.multi_cell(0, 7, "These clusters were detected in low-confidence reviews not covered by the current taxonomy. Review and consider adding to ISSUE_TAXONOMY.")
                    pdf.ln(5)

                    for _, row in flagged.iterrows():
                        pdf.set_font("Helvetica", "B", 10)
                        txt = self.safe_text(f"  Cluster #{int(row['cluster_id'])} - Est. Volume: {int(row['estimated_volume'])} reviews")
                        pdf.cell(0, 7, txt, ln=True)
                        pdf.set_font("Helvetica", "I", 9)
                        pdf.set_text_color(80, 80, 80)
                        sample = self.safe_text(str(row.get("sample_review_1", ""))[:120])
                        pdf.multi_cell(0, 6, f"  Sample: \"{sample}\"")
                        pdf.set_text_color(0, 0, 0)
                        pdf.ln(3)

            # ── 4. Semantic Drift Highlights ─────────────────────────────────
            if drift_df is not None and not drift_df.empty:
                evolving = drift_df[drift_df["is_evolving"] == True]
                if not evolving.empty:
                    pdf.set_font("Helvetica", "B", 16)
                    pdf.set_text_color(0, 0, 0)
                    pdf.cell(0, 10, "4. Semantically Evolving Issues", ln=True)
                    pdf.set_font("Helvetica", "", 11)
                    pdf.multi_cell(0, 7, "Categories where complaint language is shifting significantly month-over-month (drift > 0.15):")
                    pdf.ln(3)

                    top_drift = evolving.groupby("category")["drift_score"].mean().sort_values(ascending=False).head(5)
                    for cat, drift_score in top_drift.items():
                        pdf.set_font("Helvetica", "", 10)
                        bar = "^" * min(round(drift_score * 10), 5)
                        txt = self.safe_text(f"  {cat} - avg drift {drift_score:.3f} {bar}")
                        pdf.cell(0, 7, txt, ln=True)
                    pdf.ln(5)

            # ── Footer ───────────────────────────────────────────────────────
            pdf.set_y(-30)
            pdf.set_font("Helvetica", "I", 8)
            pdf.set_text_color(150, 150, 150)
            pdf.cell(0, 10, f"Confidential  |  SignalShift Intelligence Platform  |  Generated {datetime.now().strftime('%Y-%m-%d')}", align='C')

            report_path = os.path.join(self.output_dir, f"signalshift_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf")
            pdf.output(report_path)
            return report_path

        except Exception as e:
            print(f"Error generating PDF: {e}")
            return None
