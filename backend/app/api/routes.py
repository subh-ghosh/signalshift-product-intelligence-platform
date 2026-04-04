from fastapi import APIRouter, UploadFile, File, BackgroundTasks
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel
from typing import List
import pandas as pd
import os
import io

from app.services.csv_processor import process_uploaded_csv
from app.services.data_sync_service import DataSyncService

from fastapi.responses import FileResponse

router = APIRouter()

ml_service = None
sync_service = DataSyncService()


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
    if ml_service is None:
        return {"error": "ML service not initialized. Please upload data first."}
    result = ml_service.analyze_review(request.review)
    return result


# -----------------------------
# Analyze Multiple Reviews
# -----------------------------

@router.post("/analyze-batch")
def analyze_batch(request: BatchReviewRequest):
    if ml_service is None:
        return {"error": "ML service not initialized. Please upload data first."}
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
    if ml_service is None:
        return {"error": "ML service not initialized. Please upload data first."}
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
    try:
        if os.path.exists(uploaded):
            return pd.read_csv(uploaded)
        elif os.path.exists(cleaned):
            return pd.read_csv(cleaned)
    except Exception as e:
        print(f"Dashboard dataset missing or corrupted: {e}")
    return pd.DataFrame()





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
        metric_col = "mentions" # Default fallback

        if limit_months > 0:
            try:
                ts_df = pd.read_csv("data/processed/topic_timeseries.csv")
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
                ts_df = pd.read_csv("data/processed/topic_timeseries.csv")
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
            
            # Filter for negative issues (high severity) only
            if float(row.get("avg_severity", 0.0)) < 2.0:
                continue
                
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




@router.get("/dashboard/diagnostic-evidence")
def get_diagnostic_evidence(aspect: str = None, month: str = None, topic: str = None):
    """Returns grounded evidence reviews for a specific cross-section."""
    try:
        # Phase 62: Try to use enriched dataset first to enable rich badges/weights
        CLF_PATH = "data/processed/review_classifications.csv"
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