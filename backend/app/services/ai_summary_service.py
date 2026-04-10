import pandas as pd
import ast

from .paths import processed_data_dir


class AiSummaryService:
    def __init__(self, data_dir=None):
        if data_dir is None:
            data_dir = processed_data_dir()
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
            
            # --- 1.5 ADVANCED COGNITIVE ENGINE ---
            diagnostic_prefix = "Steady: "
            cognitive_insights = []
            
            # A. Statistical Anomaly Detection
            top_ts = timeseries_df[timeseries_df["issue_label"] == top_label].sort_values("month")
            if len(top_ts) >= 3:
                vals = top_ts[metric_col].values
                mean = vals[:-1].mean()
                std = vals[:-1].std()
                upper_bound = mean + (1.5 * std) if std > 0 else mean 
                
                if vals[-1] > upper_bound and vals[-1] > 0.5:
                    diagnostic_prefix = "Significant Spike: "
                elif vals[-1] > mean:
                    diagnostic_prefix = "Rising: "
                else:
                    diagnostic_prefix = "Steady: "

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
                        cognitive_insights.append(f"Highly linked to **{linked_issue}**, suggesting they might have the same root cause.")

            # C. Simple Forecasting
            if len(top_ts) >= 3:
                vals_last = top_ts[metric_col].values[-3:]
                x = [0, 1, 2]
                y = vals_last
                slope = (3 * (x[0]*y[0] + x[1]*y[1] + x[2]*y[2]) - sum(x)*sum(y)) / (3*sum([i**2 for i in x]) - sum(x)**2)
                
                if slope > 0.2:
                    cognitive_insights.append(f"This is expected to get worse soon. We should look into it.")
                elif slope < -0.2:
                    cognitive_insights.append(f"This is expected to improve soon.")

            
            try:
                matching_reviews = ast.literal_eval(top_issue["sample_reviews"])
            except Exception:
                rev_string = str(top_issue["sample_reviews"]).strip('[]')
                matching_reviews = [r.strip(" '\"\n") for r in rev_string.split("', '") if r.strip()]

            evidence = matching_reviews[0] if matching_reviews else "No clear textual evidence."

            # 2. Aspect Intelligence Map Synthesis
            aspect_intelligence = []
            try:
                mapping = {
                    "Performance/Technical": ["App Crash & Launch Failure", "Performance & Speed", "Bugs & Technical Errors"],
                    "Content/Library": ["Content & Features", "Download & Offline", "Video & Streaming Playback"],
                    "UI/UX Experience": ["UI & Navigation", "Notifications & Spam"],
                    "Pricing/Subscription": ["Subscription & Billing", "Account & Login", "Privacy & Security"],
                }
                curr_months = months[-limit_months:] if limit_months > 0 else [months[-1]]
                prev_months = months[-(limit_months*2):-limit_months] if limit_months > 0 and len(months) >= limit_months*2 else []
                
                for aspect, labels in mapping.items():
                    curr_vol = timeseries_df[(timeseries_df["issue_label"].isin(labels)) & (timeseries_df["month"].isin(curr_months))]["mentions"].sum()
                    if curr_vol > 0:
                        prev_vol = timeseries_df[(timeseries_df["issue_label"].isin(labels)) & (timeseries_df["month"].isin(prev_months))]["mentions"].sum()
                        momentum = round(((curr_vol - prev_vol) / max(prev_vol, 1)) * 100, 1) if prev_vol > 0 else 0
                        status = "Getting Worse" if momentum > 15 else "Improving" if momentum < -15 else "Stable"
                        aspect_intelligence.append(f"{aspect}: **{status}**")
            except Exception as e:
                print(f"Aspect synthesis error: {e}")

            # 2.5 Sentiment Stability Synthesis
            stability_alert = ""
            try:
                severity_map = topic_df.set_index("label")["avg_severity"].to_dict()
                all_m = sorted(timeseries_df['month'].unique())
                monthly_sentiment = []
                for m in all_m:
                    m_df = timeseries_df[timeseries_df["month"] == m]
                    weighted_sum = sum(row["mentions"] * severity_map.get(row["issue_label"], 2.0) for _, row in m_df.iterrows())
                    vol = m_df["mentions"].sum()
                    if vol > 0: monthly_sentiment.append(weighted_sum / vol)
                
                if len(monthly_sentiment) >= 3:
                    vals = monthly_sentiment
                    mean = sum(vals[:-1]) / len(vals[:-1])
                    std = (sum((x - mean)**2 for x in vals[:-1]) / len(vals[:-1]))**0.5
                    if vals[-1] > mean + (1.5 * std) or vals[-1] < mean - (1.5 * std):
                        stability_alert = " ⚠️ **HIGH EMOTIONAL VOLATILITY DETECTED**."
            except Exception as e:
                print(f"Stability synthesis error: {e}")
            
            # 3. Time Series Trending
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

            # --- 4. Prescriptive Strategic Reasoning (Phase 55) ---
            def classify_issue(label: str) -> str:
                strategic_labels = {"Privacy & Security", "Subscription & Billing", "Content & Features", "Strategic Product Pivot"}
                return "Long-term Plan" if label in strategic_labels else "Immediate Action"

            def get_next_best_action(label: str, severity: float, momentum: float) -> str:
                if severity > 4.0:
                    return f"Urgent: Assign a team to fix this quickly to avoid losing money."
                if momentum > 25:
                    return f"Action: Check recent app updates to see what caused this sudden spike."
                if label == "App Crash & Launch Failure":
                    return "Action: Check technical logs and consider rolling back the last update."
                return "Standard: Keep an eye on this trend and plan a fix in the next roadmap."

            # --- Construct Narrative Report ---
            impact_desc = "high impact" if top_score > 800 else "notable impact" if top_score > 400 else "minor impact"
            
            # 1. Primary Focus Block
            primary_focus = f"### 💡 Primary Focus: {top_label}\n"
            primary_focus += f"**Current Situation:** This topic is currently **{diagnostic_prefix.lower().strip(': ')}** and is having a **{impact_desc}** on your customers. "
            if cognitive_insights:
                primary_focus += " ".join(cognitive_insights)
            
            # 2. Recommendation Block
            recommendation = f"### 🎯 Suggested Action\n"
            recommendation += f"**{get_next_best_action(top_label, top_sev, pct if is_trending else 0)}**"

            # 3. Overall Health Block
            health = f"### 📊 General App Health\n"
            health += f"**Status:** {stability_alert if stability_alert else '🟢 Monitoring is active. All systems are currently within normal performance ranges.'}\n\n"
            if aspect_intelligence:
                health += "**Category Performance:**\n" + "\n".join([f"- {item}" for item in aspect_intelligence])
            
            if biggest_riser and biggest_riser[0] != top_label:
                health += f"\n\n**Watch Out:** {biggest_riser[0]} is starting to trend upward."

            # 4. Customer Voice Block
            voice = f"### 💬 What Customers are Saying\n"
            voice += f"> *\"{evidence[:200]}...\"*"

            # Final Assembly with Dividers
            report_sections = [
                primary_focus,
                "---",
                recommendation,
                "---",
                health,
                "---",
                voice
            ]

            return "\n\n".join(report_sections)

        except Exception as e:
            print(f"Error generating AI Summary: {e}")
            return "> **Engine Error:** Failed to compile executive summary. Check logs."

# Expose a singleton instance
ai_summary_service = AiSummaryService()
