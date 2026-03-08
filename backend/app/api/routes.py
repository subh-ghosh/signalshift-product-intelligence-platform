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

                # Apply windowed counts to topic_df
                windowed = curr_win.reset_index()
                windowed.columns = [label_col_ta, "windowed_mentions"]
                topic_df = topic_df.merge(windowed, on=label_col_ta, how="left")
                topic_df["mentions"] = topic_df["windowed_mentions"].fillna(0).astype(int)
                topic_df = topic_df.drop(columns=["windowed_mentions"], errors="ignore")
            except Exception as e:
                print(f"[top-issues] Windowed mentions error: {e}")

        topic_df = topic_df.sort_values("mentions", ascending=False)
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
    """Serves time-series data of topic prevalence. Top-N chosen within the selected window."""
    try:
        df = pd.read_csv("data/processed/topic_timeseries.csv")
        df = df.sort_values(by="month")

        # Pick top-5 issues BY the selected window (not all time)
        if limit_months > 0:
            all_months = sorted(df["month"].unique())
            target_months = all_months[-limit_months:]
            window_df = df[df["month"].isin(target_months)]
        else:
            window_df = df

        top_issues = window_df.groupby("issue_label")["mentions"].sum().nlargest(5).index
        df_top = df[df["issue_label"].isin(top_issues)]

        pivot = df_top.pivot_table(index="month", columns="issue_label", values="mentions", fill_value=0).reset_index()
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