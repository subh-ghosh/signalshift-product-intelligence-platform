import os
import pandas as pd
from fpdf import FPDF
from datetime import datetime

class ReportService:
    def __init__(self, data_dir="data/processed"):
        self.data_dir = data_dir
        self.output_dir = "data/reports"
        os.makedirs(self.output_dir, exist_ok=True)

    def generate_pdf_report(self):
        try:
            # Load Data
            aspect_df = pd.read_csv(os.path.join(self.data_dir, "aspect_analysis.csv"))
            topic_df = pd.read_csv(os.path.join(self.data_dir, "topic_analysis.csv"))
            
            # Create PDF
            pdf = FPDF()
            pdf.add_page()
            
            # Header
            pdf.set_fill_color(229, 9, 20) # Netflix Red
            pdf.rect(0, 0, 210, 40, 'F')
            
            pdf.set_font("Helvetica", "B", 24)
            pdf.set_text_color(255, 255, 255)
            pdf.cell(0, 20, "SignalShift Elite Intelligence", ln=True, align='C')
            pdf.set_font("Helvetica", "", 12)
            pdf.cell(0, 10, f"Executive Summary Report - {datetime.now().strftime('%Y-%m-%d %H:%M')}", ln=True, align='C')
            
            pdf.ln(20)
            
            # Global Sentiment Summary (Mock/Aggregated)
            pdf.set_text_color(0, 0, 0)
            pdf.set_font("Helvetica", "B", 16)
            pdf.cell(0, 10, "1. Business Aspect Intelligence (ABSA)", ln=True)
            pdf.set_font("Helvetica", "", 11)
            pdf.multi_cell(0, 7, "This section visualizes the distribution of dissatisfaction across primary business categories using SignalShiftBERT.")
            pdf.ln(5)
            
            # Table for Aspects
            pdf.set_font("Helvetica", "B", 10)
            pdf.cell(100, 10, "Category", border=1)
            pdf.cell(40, 10, "Mentions", border=1)
            pdf.cell(40, 10, "Priority", border=1, ln=True)
            
            pdf.set_font("Helvetica", "", 10)
            total_mentions = aspect_df["mentions"].sum()
            for _, row in aspect_df.iterrows():
                percentage = (row["mentions"] / total_mentions) * 100
                priority = "CRITICAL" if percentage > 20 else "NORMAL"
                
                pdf.cell(100, 8, str(row["aspect"]), border=1)
                pdf.cell(40, 8, str(row["mentions"]), border=1)
                pdf.cell(40, 8, priority, border=1, ln=True)
            
            pdf.ln(10)
            
            # Topic Intelligence
            pdf.set_font("Helvetica", "B", 16)
            pdf.cell(0, 10, "2. High-Priority Issue Clusters (NMF / SignalShiftBERT)", ln=True)
            pdf.set_font("Helvetica", "", 11)
            pdf.multi_cell(0, 7, "The top 5 recurring themes requiring immediate engineering or customer success attention, powered by precision topic modeling:")
            pdf.ln(5)
            
            # Top 5 Topics
            from app.ml.issue_labeler import generate_issue_label
            import ast
            
            for idx, row in topic_df.head(5).iterrows():
                label = generate_issue_label(str(row['keywords']))
                
                try:
                    matching_reviews = ast.literal_eval(row["sample_reviews"])
                except Exception:
                    rev_string = str(row["sample_reviews"]).strip('[]')
                    matching_reviews = [r.strip(" '\"") for r in rev_string.split("', '")]
                
                evidence = (matching_reviews[0][:150] + "...") if matching_reviews else "No precise evidence available."
                
                pdf.set_font("Helvetica", "B", 11)
                pdf.set_text_color(229, 9, 20)
                pdf.cell(0, 8, f"Issue #{idx+1}: {label}", ln=True)
                
                pdf.set_text_color(80, 80, 80)
                pdf.set_font("Helvetica", "I", 9)
                pdf.multi_cell(0, 6, f"Evidence: \"{evidence}\"")
                
                pdf.set_text_color(0, 0, 0)
                pdf.set_font("Helvetica", "", 10)
                pdf.cell(0, 8, f"Business Impact: {row['mentions']} active mentions", ln=True)
                pdf.ln(3)

            # Footer
            pdf.set_y(-30)
            pdf.set_font("Helvetica", "I", 8)
            pdf.set_text_color(150, 150, 150)
            pdf.cell(0, 10, "Confidential - SignalShift Research V2.0 - Generated for Netflix Manager", align='C')
            
            report_path = os.path.join(self.output_dir, f"signalshift_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf")
            pdf.output(report_path)
            
            return report_path
            
        except Exception as e:
            print(f"Error generating PDF: {e}")
            return None
