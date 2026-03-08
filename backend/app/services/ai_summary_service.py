import pandas as pd
import ast

class AiSummaryService:
    def __init__(self, data_dir="data/processed"):
        self.data_dir = data_dir

    def generate_executive_summary(self, limit_months=0) -> str:
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
                
                # Apply Dynamic Slicing
                if limit_months > 0:
                    all_months = sorted(timeseries_df['month'].unique())
                    target_months = all_months[-limit_months:]
                    timeseries_df = timeseries_df[timeseries_df['month'].isin(target_months)]
            except FileNotFoundError:
                return "> **Status:** No data analyzed yet. Please run a dataset sync to generate insights."

            if topic_df.empty:
                return "> **Status:** Analysis complete, but no high-confidence issues were detected."

            # --- PRE-FILTERING: Ignore the fallback bucket ---
            topic_df = topic_df[topic_df["label"] != "General App Feedback"]
            timeseries_df = timeseries_df[timeseries_df["issue_label"] != "General App Feedback"]

            if topic_df.empty:
                return "> **Status:** Analysis complete, but no specific high-confidence issues were detected."

            # Determine best metric available for ranking and calculating momentum
            metric_col = "mentions"
            if "severity_weighted_rate" in timeseries_df.columns:
                metric_col = "severity_weighted_rate"
            elif "normalized_rate" in timeseries_df.columns:
                metric_col = "normalized_rate"

            months = sorted(list(timeseries_df['month'].unique()))
            
            # --- 1. Core Problem Framing (Severity-Weighted) ---
            # Re-rank based on the target metric in the latest window, not raw historical mentions
            if len(months) > 0:
                current_window = timeseries_df[timeseries_df['month'].isin(months)]
                # Add Noise floor (requires 15 mentions over window to rank #1)
                valid_topics_vol = current_window.groupby("issue_label")["mentions"].sum()
                valid_topics = valid_topics_vol[valid_topics_vol >= 15].index
                
                if len(valid_topics) > 0:
                    current_window = current_window[current_window["issue_label"].isin(valid_topics)]
                    topic_rates = current_window.groupby("issue_label")[metric_col].max().to_dict()
                    topic_df["sort_score"] = topic_df["label"].map(topic_rates).fillna(0)
                else:
                    topic_df["sort_score"] = topic_df["mentions"]
            else:
                topic_df["sort_score"] = topic_df["mentions"]

            topic_df = topic_df.sort_values(by="sort_score", ascending=False)
            
            if topic_df.empty:
                 return "> **Status:** Analysis complete, but no high-confidence issues were detected."

            top_issue   = topic_df.iloc[0]
            top_label   = str(top_issue.get("label", top_issue.get("keywords", "Unknown")))
            top_score   = float(top_issue.get("sort_score", 0.0))
            top_sev     = float(top_issue.get("avg_severity", 0.0))
            
            # --- 1.5 ADVANCED COGNITIVE ENGINE (Anomalies, Correlations, Forecasts) ---
            diagnostic_prefix = "[STABLE] "
            cognitive_insights = []
            
            # A. Statistical Anomaly Detection (Bollinger)
            top_ts = timeseries_df[timeseries_df["issue_label"] == top_label].sort_values("month")
            if len(top_ts) >= 3:
                vals = top_ts[metric_col].values
                mean = vals[:-1].mean()
                std = vals[:-1].std()
                upper_bound = mean + (1.5 * std) if std > 0 else mean 
                
                if vals[-1] > upper_bound and vals[-1] > 0.5:
                    diagnostic_prefix = "🚨 [ANOMALY ALERT] "
                    cognitive_insights.append(f"Statistically out of control (>{upper_bound:.1f} threshold).")
                elif vals[-1] > mean:
                    diagnostic_prefix = "📈 [ACCELERATING] "
                else:
                    diagnostic_prefix = "📉 [STABILIZING] "

            # B. Pearson Correlation (Root Cause Linkage)
            top_5_labels = topic_df.head(5)["label"].tolist()
            if len(top_5_labels) > 1 and len(months) >= 3:
                # Pivot for correlation matrix - use pivot_table to handle potential duplicates
                pivot_df = timeseries_df[timeseries_df["issue_label"].isin(top_5_labels)].pivot_table(
                    index="month", columns="issue_label", values=metric_col, aggfunc='max'
                ).fillna(0)
                
                if top_label in pivot_df.columns:
                    corr_matrix = pivot_df.corr()
                    correlations = corr_matrix[top_label].drop(top_label)
                    strong_corr = correlations[correlations > 0.8]
                    
                    if not strong_corr.empty:
                        linked_issue = strong_corr.idxmax()
                        match_pct = int(strong_corr.max() * 100)
                        cognitive_insights.append(f"Highly linked to **{linked_issue}** ({match_pct}% correlation), suggesting a shared root cause.")

            # C. T+1 Linear Forecasting
            if len(top_ts) >= 3:
                vals = top_ts[metric_col].values[-3:]
                x = [0, 1, 2]
                y = vals
                slope = (3 * (x[0]*y[0] + x[1]*y[1] + x[2]*y[2]) - sum(x)*sum(y)) / (3*sum([i**2 for i in x]) - sum(x)**2)
                forecast_val = max(0, vals[-1] + slope)
                
                if slope > 0.2:
                    cognitive_insights.append(f"Risk Warning: Projected to rise to ~{forecast_val:.1f} next cycle.")
                elif slope < -0.2:
                    cognitive_insights.append(f"Recovery Path: Projected to drop to ~{forecast_val:.1f} next cycle.")

            
            try:
                matching_reviews = ast.literal_eval(top_issue["sample_reviews"])
            except Exception:
                rev_string = str(top_issue["sample_reviews"]).strip('[]')
                matching_reviews = [r.strip(" '\"\n") for r in rev_string.split("', '") if r.strip()]

            evidence = matching_reviews[0] if matching_reviews else "No clear textual evidence."

            # 2. Aspect Intelligence
            aspect_df_sorted = aspect_df.sort_values(by="mentions", ascending=False)
            top_aspect = aspect_df_sorted.iloc[0] if not aspect_df_sorted.empty else None
            
            # 3. Time Series Trending (Momentum based on Mathematical Rates, not Volume)
            is_trending = False
            trend_direction = ""
            pct = 0
            
            biggest_riser = None
            biggest_faller = None
            
            try:
                if len(months) >= 2:
                    curr_month = months[-1]
                    prev_month = months[0] # Compare to start of window
                    window_desc = f"over the last {len(months)} months" if limit_months > 0 else "this cycle"
                    
                    trends = []
                    # Pre-calculate noise floor over the window (must have > 15 total mentions to be a riser/faller)
                    topic_volumes = timeseries_df.groupby("issue_label")["mentions"].sum()

                    for topic in timeseries_df['issue_label'].unique():
                        # Noise Floor Check
                        if topic_volumes.get(topic, 0) < 15:
                            continue
                            
                        t_df = timeseries_df[timeseries_df['issue_label'] == topic]
                        curr_rate = t_df[t_df['month'] == curr_month][metric_col].max() # sum or max
                        prev_rate = t_df[t_df['month'] == prev_month][metric_col].max()
                        
                        if pd.isna(curr_rate): curr_rate = 0
                        if pd.isna(prev_rate): prev_rate = 0
                        
                        if prev_rate > 0:
                            change_pct = ((curr_rate - prev_rate) / prev_rate) * 100
                            # Only record mathematically significant jumps (e.g. at least 0.5 rate points)
                            if abs(curr_rate - prev_rate) >= 0.5:
                                trends.append((topic, change_pct, curr_rate - prev_rate))
                            
                    if trends:
                        trends.sort(key=lambda x: x[1])
                        if trends[0][1] < 0: biggest_faller = trends[0]
                        if trends[-1][1] > 0: biggest_riser = trends[-1]

                # Check specific trend for the #1 Top Issue
                top_issue_timeseries = timeseries_df[timeseries_df["issue_label"] == top_label].sort_values(by="month")
                if len(top_issue_timeseries) >= 2:
                    curr_rate_top = top_issue_timeseries.iloc[-1][metric_col]
                    prev_rate_top = top_issue_timeseries.iloc[-2][metric_col]
                    if curr_rate_top > prev_rate_top and prev_rate_top > 0:
                        is_trending = True
                        trend_direction = "spiking"
                        pct = int(((curr_rate_top - prev_rate_top) / prev_rate_top) * 100)
                    elif curr_rate_top < prev_rate_top and prev_rate_top > 0:
                        is_trending = True
                        trend_direction = "decreasing"
                        pct = int(((prev_rate_top - curr_rate_top) / prev_rate_top) * 100)
            except Exception as e:
                print(f"Trend calculation error: {e}")

            # 4. Time Range Calculation
            time_range_str = "Recent data"
            try:
                all_months = sorted(list(timeseries_df['month'].unique()))
                if all_months:
                    start_m = all_months[0]
                    end_m = all_months[-1]
                    count_m = len(all_months)
                    time_range_str = f"Analysis Period: {start_m} — {end_m} ({count_m} months total)"
            except Exception:
                pass

            # Construct Markdown Report with Advanced Cognitive Synthesis
            unit_suffix = " impact score" if metric_col == "severity_weighted_rate" else " rate" if metric_col == "normalized_rate" else " mentions"

            report = [
                f"- **{time_range_str}**",
                f"\n- **Critical Action Item:** {diagnostic_prefix}{top_label} (Score: {top_score:.1f})"
            ]

            if cognitive_insights:
                insight_str = "\n- **Cognitive Diagnostics:** " + " ".join(cognitive_insights)
                report.append(insight_str)

            if is_trending and not cognitive_insights: # Fallback if no deep insights
                report.append(f"\n- **Trend:** {trend_direction.capitalize()} by {pct}% MoM")

            if top_aspect is not None:
                report.append(f"\n- **Root Cause Area:** {top_aspect['aspect']} functionality")

            if biggest_riser and biggest_riser[0] != top_label:
                report.append(f"\n- **Top Riser:** {biggest_riser[0]} spiked {int(biggest_riser[1])}% (+{biggest_riser[2]:.1f}{unit_suffix}) {window_desc}")
                
            if biggest_faller:
                report.append(f"\n- **Top Faller:** {biggest_faller[0]} dropped {abs(int(biggest_faller[1]))}% {window_desc}")

            if len(topic_df) > 1:
                second_issue = topic_df.iloc[1]
                second_label = str(second_issue.get("label", second_issue.get("keywords", "Unknown")))
                second_score = float(second_issue.get("sort_metric", second_issue.get("sort_score", second_issue["mentions"])))
                report.append(f"\n- **Secondary Watchlist:** {second_label} (Score: {second_score:.1f})")

            report.append(f"\n- **Severity Indicator:** {top_label} scores {top_sev:.1f}/5.0 avg severity")
            report.append(f"\n- **Primary Evidence:**\n  > *\"{evidence[:150]}...\"*")

            return "".join(report)

        except Exception as e:
            print(f"Error generating AI Summary: {e}")
            return "> **Engine Error:** Failed to compile executive summary. Check logs."

# Expose a singleton instance
ai_summary_service = AiSummaryService()
