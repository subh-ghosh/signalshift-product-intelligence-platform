import pandas as pd
import json
import ast
from app.ml.issue_labeler import generate_issue_label

class AiSummaryService:
    def __init__(self, data_dir="data/processed"):
        self.data_dir = data_dir

    def generate_executive_summary(self) -> str:
        """
        Dynamically generates a human-readable executive summary markdown string
        based on the latest mathematical clusters from the ML pipeline.
        """
        try:
            # Load Data
            try:
                topic_df = pd.read_csv(f"{self.data_dir}/topic_analysis.csv")
                aspect_df = pd.read_csv(f"{self.data_dir}/aspect_analysis.csv")
                timeseries_df = pd.read_csv(f"{self.data_dir}/topic_timeseries.csv")
            except FileNotFoundError:
                return "> **Status:** No data analyzed yet. Please run a dataset sync to generate insights."

            if topic_df.empty:
                return "> **Status:** Analysis complete, but no high-confidence issues were detected."

            # 1. Core Problem Framing
            top_issue = topic_df.iloc[0]
            top_label = generate_issue_label(str(top_issue["keywords"]))
            top_mentions = top_issue["mentions"]
            
            # Extract evidence
            try:
                matching_reviews = ast.literal_eval(top_issue["sample_reviews"])
            except Exception:
                rev_string = str(top_issue["sample_reviews"]).strip('[]')
                matching_reviews = [r.strip(" '\"") for r in rev_string.split("', '")]
                
            evidence = matching_reviews[0] if matching_reviews else "No clear textual evidence."

            # 2. Aspect Intelligence
            aspect_df_sorted = aspect_df.sort_values(by="mentions", ascending=False)
            top_aspect = aspect_df_sorted.iloc[0] if not aspect_df_sorted.empty else None
            
            # 3. Time Series Trending
            is_trending = False
            trend_direction = ""
            try:
                top_issue_timeseries = timeseries_df[timeseries_df["issue_label"] == top_label].sort_values(by="month")
                if len(top_issue_timeseries) >= 2:
                    current_month_mentions = top_issue_timeseries.iloc[-1]["mentions"]
                    prev_month_mentions = top_issue_timeseries.iloc[-2]["mentions"]
                    if current_month_mentions > prev_month_mentions:
                        is_trending = True
                        trend_direction = "spiking"
                        pct = int(((current_month_mentions - prev_month_mentions) / prev_month_mentions) * 100)
                    elif current_month_mentions < prev_month_mentions:
                        is_trending = True
                        trend_direction = "decreasing"
                        pct = int(((prev_month_mentions - current_month_mentions) / prev_month_mentions) * 100)
            except Exception:
                pass

            # Construct Markdown Report
            report = [
                f"**Executive Overview:** The mathematical pipeline has identified **{top_label}** as the most critical action item this cycle, actively affecting **{top_mentions}** recorded interactions. "
            ]

            if is_trending:
                report.append(f"Time-series analysis shows this issue is **{trend_direction} by {pct}%** compared to the previous reporting period.")

            if top_aspect:
                report.append(f" The SignalShiftBERT model indicates this is primarily a **'{top_aspect['aspect']}'** related breakdown.")

            report.append("\n\n**Primary Evidence:** ")
            report.append(f"\n> *\"{evidence[:150]}...\"*")

            if len(topic_df) > 1:
                second_issue = topic_df.iloc[1]
                second_label = generate_issue_label(str(second_issue["keywords"]))
                report.append(f"\n\n**Secondary Watchlist:** High prevalence of **{second_label}** ({second_issue['mentions']} mentions). Engineering tracking recommended.")

            return "".join(report)

        except Exception as e:
            print(f"Error generating AI Summary: {e}")
            return "> **Engine Error:** Failed to compile executive summary. Check logs."

# Expose a singleton instance
ai_summary_service = AiSummaryService()
