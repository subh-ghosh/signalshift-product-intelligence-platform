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
        text = text.replace("\u2018", "'").replace("\u2019", "'").replace("\u201c", '"').replace("\u201d", '"')
        text = text.replace("\u2014", "--").replace("\u2013", "-").replace("\u2026", "...")
        return text.encode('latin-1', 'ignore').decode('latin-1')

    def generate_pdf_report(self):
        try:
            # Load Data
            aspect_df  = pd.read_csv(os.path.join(self.data_dir, "aspect_analysis.csv"))
            topic_df   = pd.read_csv(os.path.join(self.data_dir, "topic_analysis.csv"))

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
            pdf.cell(0, 10, f"Executive Report  |  {datetime.now().strftime('%Y-%m-%d %H:%M')}", ln=True, align='C')
            pdf.ln(20)

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
                sev_bar = "\u2b24" * min(round(avg_sev), 5)  # filled circles as severity indicator
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
                    pdf.cell(0, 10, "3. \u26a0  Emerging / Uncategorized Issues", ln=True)
                    pdf.set_text_color(0, 0, 0)
                    pdf.set_font("Helvetica", "", 11)
                    pdf.multi_cell(0, 7, "These clusters were detected in low-confidence reviews not covered by the current taxonomy. Review and consider adding to ISSUE_TAXONOMY.")
                    pdf.ln(5)

                    for _, row in flagged.iterrows():
                        pdf.set_font("Helvetica", "B", 10)
                        pdf.cell(0, 7, f"  Cluster #{int(row['cluster_id'])} — Est. Volume: {int(row['estimated_volume'])} reviews", ln=True)
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
                        bar = "\u25b2" * min(round(drift_score * 10), 5)
                        pdf.cell(0, 7, f"  {self.safe_text(cat)}  —  avg drift {drift_score:.3f}  {bar}", ln=True)
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
