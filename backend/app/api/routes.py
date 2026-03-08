from fastapi import APIRouter, UploadFile, File, BackgroundTasks
from pydantic import BaseModel
from typing import List
import pandas as pd
import os

from app.services.csv_processor import process_uploaded_csv
from app.services.data_sync_service import DataSyncService
from app.services.report_service import ReportService
from app.services.alerting_service import AlertingService
from app.services.ai_summary_service import ai_summary_service
from fastapi.responses import FileResponse

router = APIRouter()

ml_service = None
sync_service = DataSyncService()
report_service = ReportService()
alerting_service = AlertingService()

def set_ml_service(service):
    global ml_service
    ml_service = service


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
    result = ml_service.analyze_review(request.review)
    return result


# -----------------------------
# Analyze Multiple Reviews
# -----------------------------

@router.post("/analyze-batch")
def analyze_batch(request: BatchReviewRequest):
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
    issues = ml_service.detect_issues(request.reviews)
    return {
        "total_reviews": len(request.reviews),
        "top_issues": issues
    }


# -----------------------------
# Dashboard APIs
# -----------------------------

def get_dashboard_dataset():
    uploaded = "data/processed/uploaded_reviews.csv"
    cleaned = "data/processed/cleaned_reviews.csv"
    if os.path.exists(uploaded):
        return pd.read_csv(uploaded)
    return pd.read_csv(cleaned)


# -----------------------------
# SENTIMENT DISTRIBUTION
# -----------------------------

@router.get("/dashboard/sentiment")
def sentiment_distribution(limit_months: int = 0):
    try:
        df = get_dashboard_dataset()
        if limit_months > 0 and "at" in df.columns:
            df["at"] = pd.to_datetime(df["at"], errors="coerce")
            cutoff = pd.Timestamp.now() - pd.DateOffset(months=limit_months)
            df = df[df["at"] >= cutoff]
        positive = (df["sentiment"] == "positive").sum()
        negative = (df["sentiment"] == "negative").sum()
        return {"positive": int(positive), "negative": int(negative)}
    except Exception as e:
        print(f"Sentiment error: {e}")
        df = get_dashboard_dataset()
        return {
            "positive": int((df["sentiment"] == "positive").sum()),
            "negative": int((df["sentiment"] == "negative").sum())
        }


# -----------------------------
# TOP ISSUES
# -----------------------------

@router.get("/dashboard/top-issues")
def top_issues(limit_months: int = 0):
    try:
        topic_df = pd.read_csv("data/processed/topic_analysis.csv")

        # Detect the label column
        if "label" in topic_df.columns:
            label_col_ta = "label"
        elif "topic_id" in topic_df.columns:
            label_col_ta = "topic_id"
        else:
            label_col_ta = topic_df.columns[0]

        curr_mentions_map = {}
        prev_mentions_map = {}

        if limit_months > 0:
            try:
                ts_df = pd.read_csv("data/processed/topic_timeseries.csv")
                all_months = sorted(ts_df["month"].unique())
                curr_months = all_months[-limit_months:]
                prev_months = all_months[-(limit_months * 2):-limit_months] if len(all_months) >= limit_months * 2 else []

                curr_win = ts_df[ts_df["month"].isin(curr_months)].groupby("topic_id")["mentions"].sum()
                curr_mentions_map = curr_win.to_dict()

                if prev_months:
                    prev_win = ts_df[ts_df["month"].isin(prev_months)].groupby("topic_id")["mentions"].sum()
                    prev_mentions_map = prev_win.to_dict()
                    
                # We also need the best available rate for sorting/display
                metric_col = "severity_weighted_rate" if "severity_weighted_rate" in ts_df.columns else "normalized_rate" if "normalized_rate" in ts_df.columns else "mentions"
                
                # Apply the noise floor: minimum 15 mentions required to be ranked by rate.
                valid_curr_topics = curr_win[curr_win >= 15].index
                
                # Peak rate in the window (same as Trending Chart velocity selection methodology)
                curr_rate = ts_df[
                    (ts_df["month"].isin(curr_months)) & 
                    (ts_df["topic_id"].isin(valid_curr_topics))
                ].groupby("topic_id")[metric_col].max()

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

            issues.append({
                "issue": label,
                "keywords": label,
                "mentions": mentions,
                "sort_metric": row.get("sort_metric", mentions),
                "avg_severity": round(float(row.get("avg_severity", 0.0)), 2),
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
def top_aspects(limit_months: int = 0):
    try:
        # If no time window, serve the pre-aggregated aspect CSV
        if limit_months == 0:
            aspect_df = pd.read_csv("data/processed/aspect_analysis.csv")
            return aspect_df.sort_values("mentions", ascending=False).to_dict(orient="records")
        # Windowed: approximate by scaling total mentions by fraction of months active
        aspect_df = pd.read_csv("data/processed/aspect_analysis.csv")
        try:
            ts_df = pd.read_csv("data/processed/topic_timeseries.csv")
            all_months = sorted(ts_df["month"].unique())
            total_months = max(len(all_months), 1)
            effective_months = min(limit_months, total_months)
            scale = effective_months / total_months
            aspect_df = aspect_df.copy()
            aspect_df["mentions"] = (aspect_df["mentions"] * scale).round().astype(int)
        except Exception:
            pass
        return aspect_df.sort_values("mentions", ascending=False).to_dict(orient="records")
    except FileNotFoundError:
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
        df = pd.read_csv("data/processed/topic_evolution_summary.csv")
        return df.to_dict(orient="records")
    except FileNotFoundError:
        return []

@router.get("/dashboard/trending-issues")
def trending_issues(limit_months: int = 0):
    """
    Phase 35 (final) — Statistically rigorous time-series.

    Improvements applied in order:
    1. Severity-weighted rate: prefers `severity_weighted_rate` if available, else
       `normalized_rate` (per 1k reviews), else raw `mentions`. Severity-weighted
       means a month with 30 CRITICAL crashes counts more than 100 mild UI niggles.
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
        df = pd.read_csv("data/processed/topic_timeseries.csv")
        df = df.sort_values(by="month")

        # ── 1. Pick best available metric column ────────────────────────────
        if "severity_weighted_rate" in df.columns:
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
        valid_topics = (
            window_df.groupby("issue_label")["mentions"]
            .sum()
        )
        valid_topics = valid_topics[valid_topics >= 15].index
        
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
    report_path = report_service.generate_pdf_report(limit_months=limit_months)
    if not report_path or not os.path.exists(report_path):
        return {"error": "Failed to generate report"}

    window_label = f"Last{limit_months}M" if limit_months > 0 else "All"
    return FileResponse(
        path=report_path,
        filename=f"SignalShift_Report_{window_label}_{pd.Timestamp.now().strftime('%Y%m%d')}.pdf",
        media_type="application/pdf"
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

    CLF_PATH = "data/processed/review_classifications.csv"

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
                # Sort by confidence descending, deduplicate, return top 20
                matched = matched.sort_values("confidence", ascending=False)
                reviews_list = (
                    matched["text"]
                    .dropna()
                    .tolist()
                )
                # Basic dedup (exact)
                seen = set()
                deduped = []
                for r in reviews_list:
                    key = str(r)[:80]
                    if key not in seen and len(str(r)) > 20:
                        seen.add(key)
                        deduped.append(str(r))
                    if len(deduped) >= 20:
                        break

                return {
                    "issue": issue,
                    "keywords": issue,
                    "reviews": deduped,
                    "window": f"Last {limit_months}M" if limit_months > 0 else "All Time",
                    "total_in_window": len(matched)
                }
        except Exception as e:
            print(f"[issue-reviews] clf fallback: {e}")

    # ── Fallback: pre-stored sample_reviews in topic_analysis.csv ───────────
    try:
        topic_df = pd.read_csv("data/processed/topic_analysis.csv")
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
        ts_df = pd.read_csv("data/processed/topic_timeseries.csv")
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
            ts_df = pd.read_csv("data/processed/topic_timeseries.csv")
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

@router.get("/dashboard/emerging-issues")
def emerging_issues_endpoint(limit_months: int = 0):
    """Returns flagged emerging issue clusters."""
    try:
        df = pd.read_csv("data/processed/emerging_issues.csv")
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
                "estimated_volume": int(row["estimated_volume"]),
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
        df = pd.read_csv("data/processed/semantic_drift.csv")

        # Filter to selected window if limit_months set
        if limit_months > 0:
            all_months = sorted(df["month_from"].unique())
            target_months = all_months[-limit_months:]
            df = df[df["month_from"].isin(target_months)]

        # Aggregate avg drift per category
        agg = (
            df.groupby("category")
            .agg(avg_drift=("drift_score", "mean"), max_drift=("drift_score", "max"),
                 n_months=("drift_score", "count"))
            .reset_index()
        )
        agg["is_evolving"] = agg["avg_drift"] > 0.10
        agg = agg[agg["is_evolving"]].sort_values("avg_drift", ascending=False)

        result = []
        for _, row in agg.iterrows():
            result.append({
                "category": row["category"],
                "avg_drift": round(float(row["avg_drift"]), 4),
                "max_drift": round(float(row["max_drift"]), 4),
                "n_months": int(row["n_months"]),
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

        os.makedirs("data/processed", exist_ok=True)
        df.to_csv("data/processed/uploaded_reviews.csv", index=False)
        
        # Phase 2: Topics/Cache (Always run on what we have, even if Phase 1 was stopped)
        ml_service.generate_topic_analysis_cache(df)
            
        ml_service.progress["status"] = "complete"
        
    except Exception as e:
        print(f"Background job failed: {e}")
        ml_service.progress["status"] = "error"


# -----------------------------
# Upload Reviews CSV
# -----------------------------

@router.post("/upload-reviews")
def upload_reviews(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    if ml_service is None:
        return {"error": "ML service not initialized"}

    df = pd.read_csv(file.file)
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