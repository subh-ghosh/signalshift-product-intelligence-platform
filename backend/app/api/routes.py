from fastapi import APIRouter, UploadFile, File, BackgroundTasks
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel
from typing import List
import pandas as pd
import os
import io

from app.services.csv_processor import process_uploaded_csv
from app.services.data_sync_service import DataSyncService
from app.services.report_service import ReportService
from app.services.alerting_service import AlertingService
from app.services.ai_summary_service import ai_summary_service
from app.services.paths import processed_data_dir
from fastapi.responses import Response

router = APIRouter()

PROCESSED_DIR = processed_data_dir()


def processed_file(filename: str) -> str:
    return os.path.join(PROCESSED_DIR, filename)

ml_service = None
sync_service = DataSyncService()
report_service = ReportService()
alerting_service = AlertingService()

def set_ml_service(service):
    global ml_service
    ml_service = service


def _ml_not_ready_response() -> dict:
    if ml_service is None:
        return {"error": "ML service not initialized."}
    init_error = getattr(ml_service, "init_error", None)
    return {
        "error": "ML models are not available. Retrain the models and restart the backend.",
        "details": init_error,
    }


def _is_ml_ready() -> bool:
    if ml_service is None:
        return False
    is_ready = getattr(ml_service, "is_ready", None)
    return bool(is_ready()) if callable(is_ready) else True


# -----------------------------
# Request Schemas
# -----------------------------

class ReviewRequest(BaseModel):
    review: str


class BatchReviewRequest(BaseModel):
    reviews: List[str]


# -----------------------------
# Health
# -----------------------------

@router.get("/")
def root():
    return {"message": "SignalShift API is running"}


@router.get("/health")
def health():
    return {"status": "healthy"}


# -----------------------------
# Analyze Single Review
# -----------------------------

@router.post("/analyze-review")
def analyze_review(request: ReviewRequest):
    if not _is_ml_ready():
        return _ml_not_ready_response()
    result = ml_service.analyze_review(request.review)
    return result


# -----------------------------
# Analyze Multiple Reviews
# -----------------------------

@router.post("/analyze-batch")
def analyze_batch(request: BatchReviewRequest):
    if not _is_ml_ready():
        return _ml_not_ready_response()
    results = []
    for review in request.reviews:
        result = ml_service.analyze_review(review)
        results.append(result)
    return {
        "total_reviews": len(results),
        "results": results
    }


# -----------------------------
# Detect Issues
# -----------------------------

@router.post("/detect-issues")
def detect_issues(request: BatchReviewRequest):
    if not _is_ml_ready():
        return _ml_not_ready_response()
    issues = ml_service.detect_issues(request.reviews)
    return {
        "total_reviews": len(request.reviews),
        "top_issues": issues
    }


# -----------------------------
# Dashboard APIs
# -----------------------------

def get_dashboard_dataset():
    uploaded = processed_file("uploaded_reviews.csv")
    cleaned = processed_file("cleaned_reviews.csv")
    try:
        if os.path.exists(uploaded):
            return pd.read_csv(uploaded)
        elif os.path.exists(cleaned):
            return pd.read_csv(cleaned)
    except Exception as e:
        print(f"Dashboard dataset missing or corrupted: {e}")
    return pd.DataFrame()


# -----------------------------
# SENTIMENT DISTRIBUTION
# -----------------------------

@router.get("/dashboard/sentiment")
def sentiment_distribution(limit_months: int = 0):
    try:
        df = get_dashboard_dataset()
        if "at" in df.columns:
            df["at"] = pd.to_datetime(df["at"], errors="coerce")
            
        now = pd.Timestamp.now()
        
        # Current Window
        if limit_months > 0:
            cutoff = now - pd.DateOffset(months=limit_months)
            curr_df = df[df["at"] >= cutoff]
            # Previous Window (for momentum)
            prev_cutoff = now - pd.DateOffset(months=limit_months * 2)
            prev_df = df[(df["at"] >= prev_cutoff) & (df["at"] < cutoff)]
        else:
            curr_df = df
            prev_df = pd.DataFrame()

        pos = (curr_df["sentiment"] == "positive").sum()
        neg = (curr_df["sentiment"] == "negative").sum()
        total = pos + neg
        pos_pct = (pos / total * 100) if total > 0 else 0
        
        # Calculate Momentum
        momentum = 0.0
        if not prev_df.empty:
            prev_pos = (prev_df["sentiment"] == "positive").sum()
            prev_neg = (prev_df["sentiment"] == "negative").sum()
            prev_total = prev_pos + prev_neg
            prev_pos_pct = (prev_pos / prev_total * 100) if prev_total > 0 else 0
            momentum = round(pos_pct - prev_pos_pct, 1)

        return {
            "positive": int(pos),
            "negative": int(neg),
            "momentum": momentum
        }
    except Exception as e:
        print(f"Sentiment error: {e}")
        df = get_dashboard_dataset()
        return {
            "positive": int((df["sentiment"] == "positive").sum()),
            "negative": int((df["sentiment"] == "negative").sum()),
            "momentum": 0.0
        }


# -----------------------------
# TOP ISSUES
# -----------------------------

@router.get("/dashboard/top-issues")
def top_issues(limit_months: int = 0):
    try:
        topic_df = pd.read_csv(processed_file("topic_analysis.csv"))

        # Detect the label column
        if "label" in topic_df.columns:
            label_col_ta = "label"
        elif "topic_id" in topic_df.columns:
            label_col_ta = "topic_id"
        else:
            label_col_ta = topic_df.columns[0]

        curr_mentions_map = {}
        prev_mentions_map = {}
        metric_col = "mentions" # Default fallback

        if limit_months > 0:
            try:
                ts_df = pd.read_csv(processed_file("topic_timeseries.csv"))
                all_months = sorted(ts_df["month"].unique())
                curr_months = all_months[-limit_months:]
                prev_months = all_months[-(limit_months * 2):-limit_months] if len(all_months) >= limit_months * 2 else []

                # Use issue_label for grouping to match the "label" column in topic_df
                curr_win = ts_df[ts_df["month"].isin(curr_months)].groupby("issue_label")["mentions"].sum()
                curr_mentions_map = curr_win.to_dict()

                if prev_months:
                    prev_win = ts_df[ts_df["month"].isin(prev_months)].groupby("issue_label")["mentions"].sum()
                    prev_mentions_map = prev_win.to_dict()
                    
                # Vanguard Elite: Prioritize Revenue Risk over simple Severity
                if "revenue_risk_score" in ts_df.columns:
                    metric_col = "revenue_risk_score"
                elif "severity_weighted_rate" in ts_df.columns:
                    metric_col = "severity_weighted_rate"
                elif "normalized_rate" in ts_df.columns:
                    metric_col = "normalized_rate"
                else:
                    metric_col = "mentions"
                
                # Apply the dynamically scaled noise floor (5% volume or min 2)
                total_window_mentions = curr_win.sum()
                dynamic_threshold = max(2, int(total_window_mentions * 0.05)) if limit_months > 0 else 15
                valid_curr_topics = curr_win[curr_win >= dynamic_threshold].index
                
                # Peak rate in the window
                curr_rate = ts_df[
                    (ts_df["month"].isin(curr_months)) & 
                    (ts_df["issue_label"].isin(valid_curr_topics))
                ].groupby("issue_label")[metric_col].max()

                # Apply windowed counts to topic_df
                windowed = curr_win.reset_index()
                windowed.columns = [label_col_ta, "windowed_mentions"]
                topic_df = topic_df.merge(windowed, on=label_col_ta, how="left")
                topic_df["mentions"] = topic_df["windowed_mentions"].fillna(0).astype(int)
                topic_df = topic_df.drop(columns=["windowed_mentions"], errors="ignore")
                
                # Apply the metric rate for sorting
                rate_df = curr_rate.reset_index()
                rate_df.columns = [label_col_ta, "windowed_rate"]
                topic_df = topic_df.merge(rate_df, on=label_col_ta, how="left")
                topic_df["sort_metric"] = topic_df["windowed_rate"].fillna(0.0).astype(float)
            except Exception as e:
                print(f"[top-issues] Windowed mentions error: {e}")
        else:
            # Phase 62: Global Revenue Risk fallback for "All Time"
            try:
                ts_df = pd.read_csv(processed_file("topic_timeseries.csv"))
                # Group by label and sum the revenue risk score across all time
                global_risk = ts_df.groupby("issue_label")["revenue_risk_score"].sum()
                global_risk_df = global_risk.reset_index()
                global_risk_df.columns = [label_col_ta, "global_revenue_risk"]
                topic_df = topic_df.merge(global_risk_df, on=label_col_ta, how="left")
                # If SortByRevenue is active, this will be used
                topic_df["sort_metric_revenue"] = topic_df["global_revenue_risk"].fillna(0.0)
                metric_col = "revenue_risk_score" # Signal to the loop below
            except:
                pass

        if "sort_metric" not in topic_df.columns:
            topic_df["sort_metric"] = topic_df["mentions"]

        topic_df = topic_df.sort_values("sort_metric", ascending=False)
        issues = []
        for _, row in topic_df.iterrows():
            label = str(row.get(label_col_ta, row.get("keywords", "Unknown")))
            mentions = int(row["mentions"])
            if mentions == 0:
                continue

            # Compute velocity vs previous period
            velocity = None
            velocity_dir = "same"
            velocity_label = ""
            if limit_months > 0 and prev_mentions_map:
                prev = prev_mentions_map.get(label, 0)
                if prev > 0:
                    pct = round(((mentions - prev) / prev) * 100, 1)
                    velocity = pct
                    velocity_dir = "up" if pct > 5 else "down" if pct < -5 else "same"
                    sign = "+" if pct > 0 else ""
                    velocity_label = f"{sign}{pct}%"
                elif mentions > 0:
                    velocity_dir = "new"
                    velocity_label = "NEW"

            # Phase 62: Use global revenue risk if sorting by it
            rr_val = row.get("sort_metric_revenue", row.get("sort_metric", 0.0))

            issues.append({
                "issue": label,
                "keywords": label,
                "mentions": mentions,
                "sort_metric": row.get("sort_metric", mentions),
                "avg_severity": round(float(row.get("avg_severity", 0.0)), 2),
                "revenue_risk": round(float(rr_val), 2) if metric_col == "revenue_risk_score" else None,
                "velocity": velocity,
                "velocity_dir": velocity_dir,
                "velocity_label": velocity_label
            })
            if len(issues) >= 10:
                break
        return issues
    except FileNotFoundError:
        return []


# -----------------------------
# TOP ASPECTS (ABSA)
# -----------------------------

@router.get("/dashboard/aspects")
def top_aspects(limit_months: int = 3):
    """
    Vanguard Aspect Intelligence Map endpoint.
    Synthesizes semantic mapping, sentiment intensity, and MoM momentum.
    """
    try:
        ts_df = pd.read_csv(processed_file("topic_timeseries.csv"))
        topic_analysis = pd.read_csv(processed_file("topic_analysis.csv"))
        all_months = sorted(ts_df["month"].unique())
        
        # 1. Topic-to-Aspect Mapping
        mapping = {
            "Performance/Technical": ["App Crash & Launch Failure", "Performance & Speed", "Bugs & Technical Errors"],
            "Content/Library": ["Content & Features", "Download & Offline", "Video & Streaming Playback"],
            "UI/UX Experience": ["UI & Navigation", "Notifications & Spam"],
            "Pricing/Subscription": ["Subscription & Billing", "Account & Login", "Privacy & Security"],
            "General": ["Customer Support", "General App Feedback"]
        }
        
        # 2. Setup Windows
        curr_months = all_months[-limit_months:]
        prev_months = all_months[-(limit_months * 2):-limit_months] if len(all_months) >= limit_months * 2 else all_months[:-limit_months]
        
        # 3. Sentiment intensity (avg_severity from topic_analysis)
        # Historical schemas have used different label columns.
        label_col = None
        for candidate in ("label", "issue_label", "keywords"):
            if candidate in topic_analysis.columns:
                label_col = candidate
                break

        if label_col is None:
            topic_sev = {}
        else:
            sev_col = "avg_severity" if "avg_severity" in topic_analysis.columns else None
            if sev_col is None:
                topic_sev = {}
            else:
                topic_sev = topic_analysis.set_index(label_col)[sev_col].to_dict()

        aspect_data = []
        for aspect, labels in mapping.items():
            if aspect == "General": continue # Radar usually excludes general

            # Current Window Stats
            curr_window = ts_df[(ts_df["issue_label"].isin(labels)) & (ts_df["month"].isin(curr_months))]
            mentions = int(curr_window["mentions"].sum())
            
            # Weighted Sentiment Intensity
            # (Average of severity across contributes topics, weighted by their mentions)
            total_sev = 0
            total_vol = 0
            for label in labels:
                vol = curr_window[curr_window["issue_label"] == label]["mentions"].sum()
                total_sev += topic_sev.get(label, 2.0) * vol
                total_vol += vol
            sentiment_score = round(total_sev / max(total_vol, 1), 2)

            # MoM Momentum
            prev_window = ts_df[(ts_df["issue_label"].isin(labels)) & (ts_df["month"].isin(prev_months))]
            curr_vol = curr_window["mentions"].sum()
            prev_vol = prev_window["mentions"].sum()
            momentum_pct = round(((curr_vol - prev_vol) / max(prev_vol, 1)) * 100, 1) if prev_vol > 0 else 100

            # Top Contributor
            top_topic = curr_window.groupby("issue_label")["mentions"].sum().idxmax() if not curr_window.empty else "None"

            aspect_data.append({
                "aspect": aspect,
                "mentions": mentions,
                "sentiment_score": sentiment_score,
                "momentum_pct": momentum_pct,
                "top_topic": top_topic
            })

        return sorted(aspect_data, key=lambda x: x["mentions"], reverse=True)
    except Exception as e:
        print(f"[dashboard/aspects] error: {e}")
        return []

# -----------------------------
# AUTOMATION & REPORTING
# -----------------------------

@router.get("/dashboard/alerts")
async def get_alerts():
    """Returns any active threshold alerts."""
    return {"alerts": alerting_service.get_active_alerts()}

@router.get("/dashboard/ai-summary")
async def get_ai_summary(limit_months: int = 0):
    """
    Returns a dynamically generated executive summary from the ML pipeline.
    """
    try:
        summary = ai_summary_service.generate_executive_summary(limit_months=limit_months)
        return {"summary": summary}
    except Exception as e:
         print(f"Error serving AI Summary: {e}")
         return {"summary": "> **System Offline:** Could not fetch insights."}

@router.get("/dashboard/topic-benchmark")
def get_topic_benchmark():
    """Returns the qualitative shift in intelligence after our core model upgrade."""
    try:
        df = pd.read_csv(processed_file("topic_evolution_summary.csv"))
        return df.to_dict(orient="records")
    except FileNotFoundError:
        return []

@router.get("/dashboard/trending-issues")
def trending_issues(limit_months: int = 0, metric: str = "severity"):
    """
    Phase 35 (final) — Statistically rigorous time-series.

    Improvements applied in order:
    1. Metric Selection: dynamically uses revenue_risk_score, severity_weighted_rate, or normalized_rate based on the UI toggle.
    2. Full month coverage: every month in the corpus range is present for every
       category (filled with NaN, not 0). Prevents the rolling average from bridging
       over genuine data-void gaps.
    3. Gap-safe rolling average: uses min_periods=2 so months flanked by real data
       are smoothed, but isolated single-month spikes without neighbors are preserved
       as-is rather than being suppressed.
    4. Velocity-based Top-5: peak rate in window, not total volume — catches fast-
       rising issues before they dominate in raw counts.
    Backwards-compatible: works with old CSV (raw mentions only).
    """
    try:
        df = pd.read_csv(processed_file("topic_timeseries.csv"))
        df = df.sort_values(by="month")

        # ── 1. Pick best available metric column ────────────────────────────
        if metric == "revenue" and "revenue_risk_score" in df.columns:
            metric_col = "revenue_risk_score"
        elif "severity_weighted_rate" in df.columns:
            metric_col = "severity_weighted_rate"
        elif "normalized_rate" in df.columns:
            metric_col = "normalized_rate"
        else:
            metric_col = "mentions"

        # ── 2. Select the time window ────────────────────────────────────────
        all_months = sorted(df["month"].unique())
        if limit_months > 0:
            target_months = all_months[-limit_months:]
            window_df = df[df["month"].isin(target_months)]
        else:
            target_months = all_months
            window_df = df

        # ── 3. Select Top-5 by VELOCITY (peak rate in window) ────────────────
        # First, establish a noise floor.
        # An issue must have at least 15 raw mentions in the window to be
        # considered statistically significant enough for Top 5 ranking.
        valid_topics_series = (
            window_df.groupby("issue_label")["mentions"]
            .sum()
        )
        
        # Dynamically scale noise floor based on available total volume in the window
        total_window_mentions = window_df["mentions"].sum()
        dynamic_threshold = max(2, int(total_window_mentions * 0.05)) if limit_months > 0 else 15
        
        valid_topics = valid_topics_series[valid_topics_series >= dynamic_threshold].index
        
        peak_velocity = (
            window_df[window_df["issue_label"].isin(valid_topics)]
            .groupby("issue_label")[metric_col]
            .max()
            .nlargest(5)
            .index
        )
        df_top = df[df["issue_label"].isin(peak_velocity)]

        # ── 4. Full month coverage (no gap bridging in rolling average) ──────
        # Build a complete month index from the full corpus date range
        try:
            full_range = pd.period_range(
                start=all_months[0], end=all_months[-1], freq="M"
            ).astype(str).tolist()
        except Exception:
            full_range = all_months  # fallback if period_range fails

        complete_index = pd.DataFrame({"month": full_range})

        # Pivot with NaN for missing months (do NOT use fill_value=0)
        pivot = df_top.pivot_table(
            index="month", columns="issue_label",
            values=metric_col
            # fill_value intentionally omitted — missing months stay NaN
        ).reset_index()

        # Merge onto complete month index to expose gaps as NaN rows
        pivot = complete_index.merge(pivot, on="month", how="left")
        issue_cols = [c for c in pivot.columns if c != "month"]

        # ── 5. Gap-safe rolling average & Statistical Control Bands ────────────
        # Calculate Rolling Mean (Expected Baseline)
        rolling_mean = (
            pivot[issue_cols]
            .rolling(window=3, min_periods=2, center=True)
            .mean()
        )
        
        # Calculate Rolling Standard Deviation (Expected Variance)
        # min_periods=2 ensures we don't divide by zero or NaN on single data points
        rolling_std = (
            pivot[issue_cols]
            .rolling(window=3, min_periods=2, center=True)
            .std()
        )
        
        # Compute Upper Bound (Mean + 1.5 StdDev)
        upper_bounds = rolling_mean + (1.5 * rolling_std)
        upper_bounds = upper_bounds.round(2).fillna(0)
        
        # Rename upper bounds columns
        upper_cols = [f"{c}_upper_bound" for c in issue_cols]
        upper_bounds.columns = upper_cols
        
        # Calculate Month-over-Month Momentum before replacing pivot with mean
        # (We want momentum of the smoothed line for stability)
        mom_pct = pivot[issue_cols].pct_change() * 100
        mom_pct = mom_pct.round(1).fillna(0)
        mom_cols = [f"{c}_mom" for c in issue_cols]
        mom_pct.columns = mom_cols
        
        # Apply mean back to pivot
        pivot[issue_cols] = rolling_mean.round(2)

        # Fill remaining NaN with 0 for clean JSON serialisation
        pivot[issue_cols] = pivot[issue_cols].fillna(0)
        
        # ── 5.5 Statistical Correlation Engine (Pearson Matrix) ──────────────
        correlation_matrix = pivot[issue_cols].corr()
        correlation_keys = {}
        for col in issue_cols:
            corr_key = f"{col}_correlated_with"
            correlation_keys[corr_key] = ""
            if not correlation_matrix.empty and col in correlation_matrix.columns:
                # Find the highest correlated issue (excluding itself)
                others = correlation_matrix[col].drop(col)
                if not others.empty:
                    best_match = others.idxmax()
                    best_score = others.max()
                    # Only flag strong statistical correlations (>0.80)
                    if best_score > 0.80:
                        score_pct = int(best_score * 100)
                        correlation_keys[corr_key] = f"{best_match} ({score_pct}% match)"

        # Apply static correlations across the window so the UI always has access to them
        correlations_df = pd.DataFrame([correlation_keys] * len(pivot), index=pivot.index)
        
        # Concatenate bounds, momentum, and correlations into the final JSON payload
        pivot = pd.concat([pivot, upper_bounds, mom_pct, correlations_df], axis=1)

        # ── 6. Predictive Forecasting (T+1 Month) ────────────────────────────
        if len(pivot) >= 3:
            # Use last 3 months to calculate a linear slope for each issue
            last_3 = pivot[(pivot["month"].isin(target_months)) if limit_months > 0 else (pivot.index == pivot.index)].tail(3)
            
            if len(last_3) >= 3:
                # Slope = (Y_last - Y_first) / 2
                slope = (last_3[issue_cols].iloc[-1] - last_3[issue_cols].iloc[0]) / 2.0
                
                # Predict T+1
                forecast_vals = (pivot[issue_cols].iloc[-1] + slope).clip(lower=0).round(2)
                
                # Predict T+1 Bounds (assuming same standard deviation as current month)
                forecast_bounds = (pivot[upper_cols].iloc[-1] + slope.values).clip(lower=0).round(2)
                
                # Momentum for forecast
                forecast_mom = ((forecast_vals - pivot[issue_cols].iloc[-1]) / pivot[issue_cols].iloc[-1].replace(0, 1)) * 100
                forecast_mom = forecast_mom.round(1).fillna(0)
                
                last_month_str = pivot["month"].iloc[-1]
                if pd.isna(last_month_str) and len(target_months) > 0:
                     last_month_str = target_months[-1]
                     
                try:
                    y, m = last_month_str.split('-')
                    next_m = int(m) + 1
                    next_y = int(y)
                    if next_m > 12:
                        next_m = 1
                        next_y += 1
                    next_month_str = f"{next_y}-{next_m:02d} (Forecast)"
                    
                    # Build forecast row dictionary
                    forecast_row = {"month": next_month_str}
                    for c in issue_cols:
                        forecast_row[c] = forecast_vals[c]
                        forecast_row[f"{c}_upper_bound"] = forecast_bounds[f"{c}_upper_bound"]
                        forecast_row[f"{c}_mom"] = forecast_mom[c]
                        forecast_row[f"{c}_correlated_with"] = correlation_keys.get(f"{c}_correlated_with", "")
                    forecast_row["is_forecast"] = True
                    
                    # Store forecast row to append later
                    forecast_df = pd.DataFrame([forecast_row])
                except Exception as e:
                    forecast_df = None
            else:
                forecast_df = None
        else:
            forecast_df = None

        # ── 7. Return only the requested window to the chart ─────────────────
        if limit_months > 0:
            pivot = pivot[pivot["month"].isin(target_months)]
        
        pivot["is_forecast"] = False
        if forecast_df is not None:
             pivot = pd.concat([pivot, forecast_df], ignore_index=True)

        return pivot.to_dict(orient="records")

    except Exception as e:
        print(f"Error serving trending issues: {e}")
        return []

@router.get("/dashboard/export-pdf")
async def export_report(limit_months: int = 0):
    """Generates and returns a branded PDF executive report for the selected time window."""
    report_result = report_service.generate_pdf_report(limit_months=limit_months)
    if not report_result:
        return {"error": "Failed to generate report"}

    filename, pdf_bytes = report_result
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )

# -----------------------------
# REVIEWS FOR ISSUE
# -----------------------------

@router.get("/dashboard/issue-reviews")
def issue_reviews(issue: str, limit_months: int = 0):
    """
    Returns evidence reviews for a given issue category.
    When limit_months > 0, filters to reviews within the time window.
    Reads from review_classifications.csv (Phase 31) for time-aware results,
    falls back to topic_analysis.csv sample_reviews if not yet generated.
    """
    import ast

    CLF_PATH = processed_file("review_classifications.csv")

    # ── Primary: time-aware review_classifications.csv ──────────────────────
    if os.path.exists(CLF_PATH):
        try:
            clf_df = pd.read_csv(CLF_PATH)

            # Filter by category
            matched = clf_df[clf_df["category"].str.strip() == issue.strip()].copy()

            # Filter by date window if requested
            if limit_months > 0 and "date" in matched.columns:
                matched = matched[matched["date"].notna() & (matched["date"] != "")]
                if not matched.empty:
                    # date column is YYYY-MM (month string)
                    all_months_in_cat = sorted(matched["date"].unique())
                    target_months = all_months_in_cat[-limit_months:]
                    matched = matched[matched["date"].isin(target_months)]

            if not matched.empty:
                # Phase 62: Return rich metadata objects, not just strings
                matched = matched.sort_values("confidence", ascending=False)
                
                # Phase 63: Increase limit to 100 and soften deduplication
                seen = set()
                results = []
                for _, row in matched.iterrows():
                    txt = str(row["text"])
                    key = txt[:200]  # More specific key
                    if key not in seen and len(txt) > 20:
                        seen.add(key)
                        results.append({
                            "text": txt,
                            "at": str(row.get("date", "Recent")),
                            "score": int(row.get("severity", 0)),
                            "user_tier": str(row.get("user_tier", "Standard")),
                            "value_weight": float(row.get("value_weight", 1.0)),
                            "app_version": str(row.get("app_version", "N/A")),
                            "upvotes": int(row.get("upvotes", 0))
                        })
                    if len(results) >= 100:
                        break
                
                return {
                    "issue": issue,
                    "keywords": issue,
                    "reviews": results,
                    "window": f"Last {limit_months}M" if limit_months > 0 else "All Time",
                    "total_in_window": len(matched)
                }
        except Exception as e:
            print(f"[issue-reviews] clf fallback: {e}")

    # ── Fallback: pre-stored sample_reviews in topic_analysis.csv ───────────
    try:
        topic_df = pd.read_csv(processed_file("topic_analysis.csv"))
        matching_reviews = []
        matched_label = issue
        for _, row in topic_df.iterrows():
            label = str(row.get("label", row.get("keywords", "")))
            if label.strip() == issue.strip():
                try:
                    matching_reviews = ast.literal_eval(row["sample_reviews"])
                except Exception:
                    rev_string = str(row["sample_reviews"]).strip('[]')
                    matching_reviews = [r.strip(" '\"\n") for r in rev_string.split("', ") if r.strip()]
                matched_label = label
                break
        return {
            "issue": issue,
            "keywords": matched_label,
            "reviews": [r for r in matching_reviews if len(str(r)) > 20][:20],
            "window": "All Time (pre-computed)"
        }
    except FileNotFoundError:
        return {"issue": issue, "keywords": "", "reviews": [], "window": "No data"}


# -----------------------------
# REVIEWS LIST
# -----------------------------

@router.get("/dashboard/reviews")
def reviews():
    df = get_dashboard_dataset()
    return df.head(50).to_dict(orient="records")


# -----------------------------
# CSV EXPORT
# -----------------------------

@router.get("/dashboard/export-csv")
def export_csv(limit_months: int = 0):
    """Exports filtered reviews as a CSV file download."""
    import io
    from fastapi.responses import StreamingResponse

    df = get_dashboard_dataset()
    if limit_months > 0 and "at" in df.columns:
        df["at"] = pd.to_datetime(df["at"], errors="coerce")
        cutoff = pd.Timestamp.now() - pd.DateOffset(months=limit_months)
        df = df[df["at"] >= cutoff]

    # Keep only useful columns
    keep_cols = [c for c in ["reviewId", "content", "score", "sentiment", "at", "app", "appVersion"] if c in df.columns]
    export_df = df[keep_cols].copy()

    stream = io.StringIO()
    export_df.to_csv(stream, index=False)
    stream.seek(0)

    window_label = f"Last{limit_months}M" if limit_months > 0 else "AllTime"
    filename = f"SignalShift_Reviews_{window_label}_{pd.Timestamp.now().strftime('%Y%m%d')}.csv"
    return StreamingResponse(
        iter([stream.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


# -----------------------------
# VELOCITY-BASED SMART ALERTS
# -----------------------------

@router.get("/dashboard/velocity-alerts")
def velocity_alerts(limit_months: int = 3):
    """
    Detects categories spiking or collapsing vs the previous equivalent period.
    Returns alert objects with severity (CRITICAL / HIGH / WATCH) when velocity > threshold.
    """
    SPIKE_CRITICAL = 40   # > 40% increase → CRITICAL
    SPIKE_HIGH     = 20   # > 20% increase → HIGH
    SPIKE_WATCH    = 10   # > 10% increase → WATCH
    DROP_CRITICAL  = -40  # > 40% drop     → good news, silent
    alerts_out = []
    try:
        ts_df = pd.read_csv(processed_file("topic_timeseries.csv"))
        all_months = sorted(ts_df["month"].unique())
        if len(all_months) < limit_months:
            return []

        curr_months = all_months[-limit_months:]
        prev_months = all_months[-(limit_months * 2):-limit_months] if len(all_months) >= limit_months * 2 else []
        if not prev_months:
            return []

        curr = ts_df[ts_df["month"].isin(curr_months)].groupby("topic_id")["mentions"].sum()
        prev = ts_df[ts_df["month"].isin(prev_months)].groupby("topic_id")["mentions"].sum()

        categories = set(curr.index) | set(prev.index)
        for cat in categories:
            c_val = int(curr.get(cat, 0))
            p_val = int(prev.get(cat, 0))
            if p_val == 0:
                continue
            pct = round(((c_val - p_val) / p_val) * 100, 1)

            severity = None
            if pct >= SPIKE_CRITICAL:
                severity = "CRITICAL"
            elif pct >= SPIKE_HIGH:
                severity = "HIGH"
            elif pct >= SPIKE_WATCH:
                severity = "WATCH"

            if severity:
                sign = "+" if pct > 0 else ""
                alerts_out.append({
                    "id": f"vel-{cat.lower().replace(' ', '-')[:20]}",
                    "category": cat,
                    "velocity_pct": pct,
                    "curr_mentions": c_val,
                    "prev_mentions": p_val,
                    "severity": severity,
                    "window": f"Last {limit_months}M",
                    "message": f"🔴 {cat}: {sign}{pct}% mentions vs previous {limit_months}M ({p_val} → {c_val})"
                })

        # Sort by velocity descending (worst spikes first)
        alerts_out.sort(key=lambda x: x["velocity_pct"], reverse=True)
        return alerts_out
    except Exception as e:
        print(f"[velocity-alerts] error: {e}")
        return []


@router.get("/dashboard/intelligence-alerts")
def get_intelligence_alerts(limit_months: int = 3):
    """
    The "Vanguard Signal Center" endpoint.
    Unifies Anomalies (Bollinger), Velocity (MoM), and Correlations (Pearson)
    into a single high-priority stream.
    """
    try:
        ts_df = pd.read_csv(processed_file("topic_timeseries.csv"))
        all_months = sorted(ts_df["month"].unique())
        if len(all_months) < 2:
            return {"alerts": []}

        # 1. Setup Windows
        curr_months = all_months[-limit_months:]
        prev_months = all_months[-(limit_months * 2):-limit_months] if len(all_months) >= limit_months * 2 else all_months[:-limit_months]
        
        # 2. Compute Velocity & Anomaly Metrics
        metric_col = "severity_weighted_rate" if "severity_weighted_rate" in ts_df.columns else "normalized_rate" if "normalized_rate" in ts_df.columns else "mentions"
        
        curr_stats = ts_df[ts_df["month"].isin(curr_months)].groupby("topic_id")[metric_col].agg(['max', 'sum']).rename(columns={'max': 'curr_rate', 'sum': 'curr_vol'})
        prev_stats = ts_df[ts_df["month"].isin(prev_months)].groupby("topic_id")[metric_col].agg(['max', 'sum']).rename(columns={'max': 'prev_rate', 'sum': 'prev_vol'}) if prev_months else pd.DataFrame()

        # 3. Correlation Matrix (for top items)
        top_labels = curr_stats.sort_values("curr_rate", ascending=False).head(5).index.tolist()
        corr_links = {}
        if len(top_labels) > 1 and len(all_months) >= 3:
            pivot_df = ts_df[ts_df["topic_id"].isin(top_labels)].pivot_table(
                index="month", columns="topic_id", values=metric_col, aggfunc='max'
            ).fillna(0)
            if not pivot_df.empty:
                corr_matrix = pivot_df.corr()
                for label in top_labels:
                    if label in corr_matrix.columns:
                        corrs = corr_matrix[label].drop(label)
                        strong = corrs[corrs > 0.85]
                        if not strong.empty:
                            corr_links[label] = {"linked_to": strong.idxmax(), "score": round(float(strong.max()), 2)}

        alerts = []
        
        # 4. Aspect Dominance Sensor (Legacy Sensor Unification)
        try:
            aspect_df = pd.read_csv(processed_file("aspect_analysis.csv"))
            total_aspect_mentions = aspect_df["mentions"].sum()
            if total_aspect_mentions > 0:
                for _, row in aspect_df.iterrows():
                    pct_share = (row["mentions"] / total_aspect_mentions) * 100
                    if pct_share >= 25.0:
                        alerts.append({
                            "id": f"asp-{row['aspect'].lower()[:15]}",
                            "category": row["aspect"],
                            "type": "ASPECT_DOMINANCE",
                            "severity": "HIGH",
                            "message": f"Dominant Volume: Accounting for {pct_share:.1f}% of all feedback.",
                            "velocity_pct": 0,
                            "is_anomaly": False,
                            "link": None
                        })
        except Exception: pass

        # 5. Generate Unified Topic Alerts
        for topic in curr_stats.index:
            c_rate = curr_stats.loc[topic, "curr_rate"]
            c_vol = curr_stats.loc[topic, "curr_vol"]
            
            # Skip if volume is negligible
            if c_vol < 5: continue
            
            p_vol = prev_stats.loc[topic, "prev_vol"] if topic in prev_stats.index else 0
            
            # --- Velocity Signal (Volume Based) ---
            velocity_pct = 0
            if p_vol > 0:
                velocity_pct = round(((c_vol - p_vol) / p_vol) * 100, 1)
            else:
                velocity_pct = 100 # New issue spike
            
            # --- Anomaly Signal (Bollinger) ---
            topic_ts = ts_df[ts_df["topic_id"] == topic].sort_values("month")
            is_anomaly = False
            threshold = 0
            if len(topic_ts) >= 3:
                vals = topic_ts[metric_col].values[:-1]
                mean_val = vals.mean()
                std_val = vals.std()
                threshold = mean_val + (1.5 * std_val) if std_val > 0 else mean_val
                if topic_ts[metric_col].values[-1] > threshold and topic_ts[metric_col].values[-1] > 0.5:
                    is_anomaly = True

            # Create Alert if Significant (lower threshold to 10% to catch WATCH items)
            if is_anomaly or velocity_pct > 10:
                severity = "CRITICAL" if (is_anomaly and velocity_pct > 40) else "HIGH" if (is_anomaly or velocity_pct > 25) else "WATCH"
                
                # Build Message
                msg_parts = []
                if is_anomaly: msg_parts.append(f"Statistically out-of-control (Limit: {threshold:.1f})")
                if velocity_pct > 10: msg_parts.append(f"MoM spike of +{velocity_pct}%")
                
                alert_obj = {
                    "id": f"int-{topic.lower().replace(' ', '-')[:15]}",
                    "category": topic,
                    "type": "ANOMALY" if is_anomaly else "VELOCITY",
                    "severity": severity,
                    "message": " | ".join(msg_parts),
                    "velocity_pct": velocity_pct,
                    "is_anomaly": is_anomaly,
                    "link": corr_links.get(topic)
                }
                alerts.append(alert_obj)

        # Sort by severity and velocity
        severity_map = {"CRITICAL": 0, "HIGH": 1, "WATCH": 2}
        alerts.sort(key=lambda x: (severity_map.get(x["severity"], 3), -x["velocity_pct"]))

        return {"alerts": alerts[:6]} 

    except Exception as e:
        print(f"[intelligence-alerts] error: {e}")
        return {"alerts": []}



# -----------------------------
# KPI SUMMARY
# -----------------------------

@router.get("/dashboard/kpis")
def dashboard_kpis(limit_months: int = 0):
    """Returns key metrics with period-over-period deltas for the selected time window."""
    try:
        full_df = get_dashboard_dataset()
        has_dates = limit_months > 0 and "at" in full_df.columns

        def compute_metrics(df):
            total = len(df)
            avg_rating = round(float(df["score"].mean()), 2) if "score" in df.columns and total > 0 else None
            positive = int((df["sentiment"] == "positive").sum()) if "sentiment" in df.columns else 0
            positive_pct = round((positive / total) * 100, 1) if total > 0 else 0
            return total, avg_rating, positive_pct

        if has_dates:
            full_df["at"] = pd.to_datetime(full_df["at"], errors="coerce")
            now = pd.Timestamp.now()
            curr_cutoff = now - pd.DateOffset(months=limit_months)
            prev_cutoff = now - pd.DateOffset(months=limit_months * 2)
            curr_df = full_df[full_df["at"] >= curr_cutoff]
            prev_df = full_df[(full_df["at"] >= prev_cutoff) & (full_df["at"] < curr_cutoff)]
        else:
            curr_df = full_df
            prev_df = pd.DataFrame()

        total, avg_rating, positive_pct = compute_metrics(curr_df)
        prev_total, prev_rating, prev_pos_pct = compute_metrics(prev_df) if not prev_df.empty else (None, None, None)

        def delta(curr, prev):
            if prev is None or prev == 0: return None
            return round(curr - prev, 2) if isinstance(curr, float) else curr - prev

        def pct_delta(curr, prev):
            if prev is None or prev == 0: return None
            return round(((curr - prev) / prev) * 100, 1)

        # Active issues from timeseries
        active_issues, prev_active = 0, None
        try:
            ts_df = pd.read_csv(processed_file("topic_timeseries.csv"))
            all_months = sorted(ts_df["month"].unique())
            if limit_months > 0:
                curr_months = all_months[-limit_months:]
                prev_months = all_months[-(limit_months * 2):-limit_months] if len(all_months) >= limit_months * 2 else []
                active_issues = int(ts_df[ts_df["month"].isin(curr_months)].groupby("issue_label")["mentions"].sum().gt(0).sum())
                if prev_months:
                    prev_active = int(ts_df[ts_df["month"].isin(prev_months)].groupby("issue_label")["mentions"].sum().gt(0).sum())
            else:
                active_issues = int(ts_df.groupby("issue_label")["mentions"].sum().gt(0).sum())
        except Exception:
            pass

        has_prev = prev_total and prev_total > 0

        return {
            "total_reviews": total,
            "avg_rating": avg_rating,
            "positive_pct": positive_pct,
            "active_issues": active_issues,
            "window": f"Last {limit_months}M" if limit_months > 0 else "All Time",
            "deltas": {
                "reviews": pct_delta(total, prev_total) if has_prev else None,
                "rating": delta(avg_rating, prev_rating) if has_prev and avg_rating and prev_rating else None,
                "positive_pct": delta(positive_pct, prev_pos_pct) if has_prev else None,
                "active_issues": delta(active_issues, prev_active) if prev_active is not None else None,
            } if has_dates else None
        }
    except Exception as e:
        print(f"[kpis] error: {e}")
        return {"total_reviews": 0, "avg_rating": None, "positive_pct": 0, "active_issues": 0, "deltas": None}


# -----------------------------
# EMERGING ISSUES
# -----------------------------

@router.get("/dashboard/sentiment-stability")
def get_sentiment_stability(limit_months: int = 0):
    """Calculates app-wide sentiment stability using Bollinger bands."""
    try:
        ts_df = pd.read_csv(processed_file("topic_timeseries.csv"))
        topic_analysis = pd.read_csv(processed_file("topic_analysis.csv"))
        
        # Get severity mapping
        severity_map = topic_analysis.set_index("label")["avg_severity"].to_dict()
        
        # Aggregate sentiment per month
        months = sorted(ts_df["month"].unique())
        stability_data = []
        
        for m in months:
            m_df = ts_df[ts_df["month"] == m]
            total_vol = m_df["mentions"].sum()
            if total_vol == 0: continue
            
            weighted_sev_sum = 0
            for _, row in m_df.iterrows():
                weighted_sev_sum += row["mentions"] * severity_map.get(row["issue_label"], 2.0)
            
            avg_sentiment = round(weighted_sev_sum / total_vol, 3)
            stability_data.append({"month": m, "score": avg_sentiment})

        if not stability_data: return []

        # Convert to DF for rolling stats
        df = pd.DataFrame(stability_data)
        df["rolling_mean"] = df["score"].rolling(window=3, min_periods=1).mean()
        df["rolling_std"] = df["score"].rolling(window=3, min_periods=1).std().fillna(0)
        
        df["upper_band"] = df["rolling_mean"] + (1.5 * df["rolling_std"])
        df["lower_band"] = df["rolling_mean"] - (1.5 * df["rolling_std"])
        
        # High volatility = score is outside the bands
        df["is_volatile"] = (df["score"] > df["upper_band"]) | (df["score"] < df["lower_band"])
        
        # Filter to requested time window
        if limit_months > 0:
            df = df.tail(limit_months)
        
        return df.to_dict(orient="records")
    except Exception as e:
        print(f"Sentiment Stability Error: {e}")
        return []

@router.get("/dashboard/semantic-search")
def semantic_search(query: str, limit_months: int = 0):
    try:
        if not query:
            return []
            
        df = get_dashboard_dataset()
        if "at" in df.columns:
            df["at"] = pd.to_datetime(df["at"], errors="coerce")
            
        if limit_months > 0:
            cutoff = pd.Timestamp.now() - pd.DateOffset(months=limit_months)
            df = df[df["at"] >= cutoff]
            
        reviews = df["content"].astype(str).tolist()
        
        if ml_service is None:
            return []
            
        return ml_service.semantic_search(query, reviews)
    except Exception as e:
        print(f"Semantic search error: {e}")
        return []

@router.get("/dashboard/live-ticker")
def get_live_ticker():
    """Returns a stream of high-confidence recently processed reviews."""
    try:
        # Vanguard Elite: Use central dataset utility to respect user uploads
        df = get_dashboard_dataset()
        if "at" in df.columns:
            df["at"] = pd.to_datetime(df["at"], errors="coerce")
            df = df.sort_values("at", ascending=False)
        else:
            df = df.iloc[::-1]
            
        latest = df.head(15)
        result = []
        for _, row in latest.iterrows():
            content = str(row.get("content", row.get("cleaned_content", "")))
            if len(content) < 30: continue
            result.append({
                "id": str(row.get("reviewId", "unknown")),
                "text": content[:200],
                "sentiment": str(row.get("sentiment", "neutral")),
                "at": str(row.get("at", "recent"))
            })
        return result
    except Exception as e:
        print(f"Ticker Error: {e}")
        return []

@router.get("/dashboard/diagnostic-evidence")
def get_diagnostic_evidence(aspect: str = None, month: str = None, topic: str = None):
    """Returns grounded evidence reviews for a specific cross-section."""
    try:
        # Phase 62: Try to use enriched dataset first to enable rich badges/weights
        CLF_PATH = processed_file("review_classifications.csv")
        if os.path.exists(CLF_PATH):
            df = pd.read_csv(CLF_PATH)
            # Filter logic (search strings)
            if month:
                df = df[df["date"].astype(str).str.contains(month, na=False)]
            if topic:
                df = df[df["category"].str.contains(topic, case=False, na=False) | 
                       df["text"].str.contains(topic, case=False, na=False)]
            
            # Phase 63: Bump limit for diagnostic cross-sections
            df = df.sort_values("confidence", ascending=False).head(100)
            result = []
            for _, row in df.iterrows():
                result.append({
                    "id": "enriched-" + str(row.name),
                    "text": str(row.get("text")),
                    "at": str(row.get("date", "")),
                    "score": int(row.get("severity", 0)),
                    "user_tier": str(row.get("user_tier", "Standard")),
                    "value_weight": float(row.get("value_weight", 1.0)),
                    "app_version": str(row.get("app_version", "N/A")),
                    "upvotes": int(row.get("upvotes", 0))
                })
            if result:
                return result

        # Fallback to base dataset
        df = get_dashboard_dataset()
        if month:
            df = df[df["at"].astype(str).str.contains(month, na=False)]
        if topic:
            df = df[df["content"].str.contains(topic, case=False, na=False)]
        
        # Phase 63: Bump fallback limit
        df = df.head(100)
        result = []
        for _, row in df.iterrows():
            result.append({
                "id": str(row.get("reviewId")),
                "text": str(row.get("content")),
                "score": int(row.get("score", 0)),
                "at": str(row.get("at")),
                "user_tier": "Standard",
                "value_weight": 1.0
            })
        return result
    except Exception as e:
        print(f"Diagnostic Error: {e}")
        return []

@router.get("/dashboard/emerging-issues")
def emerging_issues_endpoint(limit_months: int = 0):
    """Returns flagged emerging issue clusters."""
    try:
        df = pd.read_csv(processed_file("emerging_issues.csv"))
        flagged = df[df["is_flagged"] == True].copy()

        # Sort by volume descending
        flagged = flagged.sort_values("estimated_volume", ascending=False)

        result = []
        for _, row in flagged.iterrows():
            samples = []
            for col in ["sample_review_1", "sample_review_2", "sample_review_3"]:
                val = str(row.get(col, ""))
                if val and val != "nan" and len(val) > 10:
                    samples.append(val[:180])
            result.append({
                "cluster_id": int(row["cluster_id"]),
                "label": str(row.get("label", f"Cluster #{int(row['cluster_id'])+1}")).replace(" (Proto)", ""),
                "keywords": str(row.get("keywords", "")) if str(row.get("keywords", "")) not in ("nan", "", "None") else "",
                "estimated_volume": int(row["estimated_volume"]),
                "momentum_pct": float(row.get("momentum_pct", 0)),
                "sample_reviews": samples
            })
        return result
    except FileNotFoundError:
        return []


# -----------------------------
# SEMANTIC DRIFT
# -----------------------------

@router.get("/dashboard/semantic-drift")
def semantic_drift_endpoint(limit_months: int = 0):
    """Returns semantically evolving categories (drift > threshold), optionally filtered to recent window."""
    try:
        df = pd.read_csv(processed_file("semantic_drift.csv"))

        # Filter to selected window if limit_months set
        if limit_months > 0:
            all_months = sorted(df["month_from"].unique())
            target_months = all_months[-limit_months:]
            df = df[df["month_from"].isin(target_months)]

        # Aggregate avg drift per category
        # Also grab the most recent shifting_terms for the context
        agg = (
            df.groupby("category")
            .agg({
                "drift_score": ["mean", "max", "count"],
                "shifting_terms": "last"
            })
            .reset_index()
        )
        agg.columns = ["category", "avg_drift", "max_drift", "n_months", "shifting_terms"]
        
        agg["is_evolving"] = agg["avg_drift"] > 0.10
        agg = agg[agg["is_evolving"]].sort_values("avg_drift", ascending=False)

        result = []
        for _, row in agg.iterrows():
            result.append({
                "category": row["category"],
                "avg_drift": round(float(row["avg_drift"]), 4),
                "max_drift": round(float(row["max_drift"]), 4),
                "n_months": int(row["n_months"]),
                "shifting_terms": str(row.get("shifting_terms", "stable")),
                "trend_bar": min(round(row["avg_drift"] * 50), 5)  # 0-5 visual bar
            })
        return result
    except FileNotFoundError:
        return []


# -----------------------------
# Upload Progress & Control
# -----------------------------

@router.get("/upload-progress")
def get_upload_progress():
    if ml_service is None:
        return {"processed": 0, "total": 0, "status": "idle", "eta_seconds": 0}
    return ml_service.progress


@router.post("/stop-upload")
def stop_upload():
    if ml_service is None:
        return {"error": "ML service not initialized"}
    ml_service.stop_analysis()
    return {"message": "Stopping analysis..."}


# -----------------------------
# Sync Control
# -----------------------------

@router.get("/sync/status")
def get_sync_status():
    return sync_service.get_sync_status()


@router.post("/sync/kaggle")
def sync_kaggle(background_tasks: BackgroundTasks):
    """Triggers a download from Kaggle and starts analysis in the background"""
    if ml_service is None:
        return {"error": "ML service not initialized"}
        
    # Initialize progress for the download phase immediately
    ml_service.progress["processed"] = 0
    ml_service.progress["total"] = 100
    ml_service.progress["status"] = "downloading"
    ml_service.progress["eta_seconds"] = 0

    # Offload the entire sync + analysis process to a background job
    background_tasks.add_task(_process_kaggle_sync_job)
    
    return {
        "message": "Kaggle sync started. Tracking download progress...",
        "status": "pending"
    }


# -----------------------------
# Background Processing
# -----------------------------

def _process_kaggle_sync_job():
    """Background job for Kaggle sync: Download -> Load -> Analyze"""
    try:
        # 0. Define progress callback for sync
        def sync_progress_callback(processed, total, status):
            ml_service.progress["processed"] = processed
            ml_service.progress["total"] = total
            ml_service.progress["status"] = status
            ml_service.progress["eta_seconds"] = 0 

        # 1. Download from Kaggle
        file_path = sync_service.sync_from_kaggle(progress_callback=sync_progress_callback)
        
        # 2. Load and process
        df = pd.read_csv(file_path)
        
        possible_columns = ["content", "review", "text", "comment"]
        review_column = None
        for col in possible_columns:
            if col in df.columns:
                review_column = col
                break

        if review_column:
            df["content"] = df[review_column]
            # 3. Hand off to the standard analysis job
            _process_reviews_job(df)
        else:
            print("Dataset missing review column during Kaggle sync.")
            ml_service.progress["status"] = "error"
            
    except Exception as e:
        print(f"Kaggle Sync job failed: {e}")
        ml_service.progress["status"] = "error"


def _process_reviews_job(df: pd.DataFrame):
    """Heavy processing task that runs in the background with stop support"""
    try:
        reviews = df["content"].astype(str).tolist()
        
        # Phase 1: Sentiment
        sentiments = ml_service.predict_sentiment_batch(reviews)
        
        # If stopped early, we only keep the rows we actually have sentiments for
        if ml_service.should_stop:
            processed_count = len(sentiments)
            df = df.iloc[:processed_count].copy()
            df["sentiment"] = sentiments
        else:
            df["sentiment"] = sentiments
            
        df["cleaned_content"] = df["content"].str.lower()

        os.makedirs(PROCESSED_DIR, exist_ok=True)
        df.to_csv(processed_file("uploaded_reviews.csv"), index=False)
        
        # Phase 2: Topics/Cache (Always run on what we have, even if Phase 1 was stopped)
        ml_service.generate_topic_analysis_cache(df)
            
        ml_service.progress["status"] = "complete"
        
    except Exception as e:
        print(f"Background job failed: {e}")
        ml_service.progress["status"] = "error"


# -----------------------------
# Upload Reviews CSV
# -----------------------------

# io and run_in_threadpool imported at file top

@router.post("/upload-reviews")
async def upload_reviews(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    if ml_service is None:
        return {"error": "ML service not initialized"}

    content = await file.read()
    # Processing heavy pandas CSV parsing in a worker thread
    df = await run_in_threadpool(pd.read_csv, io.BytesIO(content))
    possible_columns = ["content", "review", "text", "comment"]
    review_column = None
    for col in possible_columns:
        if col in df.columns:
            review_column = col
            break

    if review_column is None:
        return {"error": "CSV must contain a review column"}

    # Standardize column name
    df["content"] = df[review_column]
    
    # Initialize progress early
    ml_service.progress["total"] = len(df)
    ml_service.progress["processed"] = 0
    ml_service.progress["status"] = "sentiment"
    ml_service.progress["eta_seconds"] = 0
    
    # Offload the long task to the background
    background_tasks.add_task(_process_reviews_job, df)

    return {
        "message": "Upload successful. AI Analysis started in the background.",
        "total_reviews": len(df)
    }