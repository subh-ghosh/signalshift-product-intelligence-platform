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

TRAINING_PROCESSED_DIR = os.path.join("data", "training", "processed")
TESTING_PROCESSED_DIR = os.path.join("data", "testing", "processed")
TESTING_RAW_DIR = os.path.join("data", "testing", "raw")

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
    uploaded = os.path.join(TESTING_PROCESSED_DIR, "uploaded_reviews.csv")
    cleaned = os.path.join(TESTING_PROCESSED_DIR, "cleaned_reviews.csv")
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
def top_issues():
    try:
        topic_df = pd.read_csv(os.path.join(TESTING_PROCESSED_DIR, "topic_analysis.csv"))

        # Detect the label column
        label_col = "Topic Label" if "Topic Label" in topic_df.columns else "keywords"

        # Sorting logic - Default to mentions
        if "mentions" not in topic_df.columns:
            topic_df["mentions"] = 0 

        topic_df = topic_df.sort_values("mentions", ascending=False)
        issues = []
        for _, row in topic_df.iterrows():
            label = str(row.get(label_col, "Unknown Issue"))
            mentions = int(row.get("mentions", 0))
            
            # Filter for negative issues (high severity) only
            if float(row.get("avg_severity", 0.0)) < 2.0:
                continue
                
            if mentions == 0:
                continue

            issues.append({
                "issue": label,
                "keywords": label,
                "mentions": mentions,
                "avg_severity": round(float(row.get("avg_severity", 0.0)), 2)
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
def issue_reviews(issue: str):
    """
    Returns evidence reviews for a given issue category.
    Reads from review_classifications.csv (Phase 31).
    """
    import ast

    CLF_PATH = os.path.join(TESTING_PROCESSED_DIR, "review_classifications.csv")

    # ── Primary: review_classifications.csv ──────────────────────────────────
    if os.path.exists(CLF_PATH):
        try:
            clf_df = pd.read_csv(CLF_PATH)

            # Filter by category
            matched = clf_df[clf_df["category"].str.strip() == issue.strip()].copy()

            if not matched.empty:
                matched = matched.sort_values("confidence", ascending=False)
                
                seen = set()
                results = []
                for _, row in matched.iterrows():
                    txt = str(row["text"])
                    key = txt[:200]
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
                    "total_in_window": len(matched)
                }
        except Exception as e:
            print(f"[issue-reviews] clf fallback: {e}")

    # ── Fallback: pre-stored sample_reviews in topic_analysis.csv ───────────
    try:
        topic_df = pd.read_csv(os.path.join(TESTING_PROCESSED_DIR, "topic_analysis.csv"))
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
def dashboard_kpis():
    """Returns key metrics for the whole project dataset."""
    try:
        full_df = get_dashboard_dataset()
        if full_df.empty:
            return {"total_reviews": 0, "avg_rating": None, "positive_pct": 0, "active_issues": 0}

        total = len(full_df)
        avg_rating = round(float(full_df["score"].mean()), 2) if "score" in full_df.columns and total > 0 else None
        positive = int((full_df["sentiment"] == "positive").sum()) if "sentiment" in full_df.columns else 0
        positive_pct = round((positive / total) * 100, 1) if total > 0 else 0

        active_issues = 0
        try:
            topic_df = pd.read_csv(os.path.join(TESTING_PROCESSED_DIR, "topic_analysis.csv"))
            if not topic_df.empty and "mentions" in topic_df.columns:
                active_issues = int(topic_df["mentions"].fillna(0).gt(0).sum())
        except Exception:
            pass

        return {
            "total_reviews": total,
            "avg_rating": avg_rating,
            "positive_pct": positive_pct,
            "active_issues": active_issues,
            "window": "All Time",
            "deltas": None
        }
    except Exception as e:
        print(f"[kpis] error: {e}")
        return {"total_reviews": 0, "avg_rating": None, "positive_pct": 0, "active_issues": 0, "deltas": None}




@router.get("/dashboard/diagnostic-evidence")
def get_diagnostic_evidence(aspect: str = None, month: str = None, topic: str = None):
    """Returns grounded evidence reviews for a specific cross-section."""
    try:
        # Phase 62: Try to use enriched dataset first to enable rich badges/weights
        CLF_PATH = os.path.join(TESTING_PROCESSED_DIR, "review_classifications.csv")
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
        
        possible_columns = ["content", "review", "text", "comment", "review_text", "body"]
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
    """Inference-only analysis for uploaded/synced CSV data using pre-trained models."""
    try:
        reviews = df["content"].astype(str).tolist()
        
        # Inference only: never retrain models from uploaded CSV data.
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

        os.makedirs(TESTING_PROCESSED_DIR, exist_ok=True)
        df.to_csv(os.path.join(TESTING_PROCESSED_DIR, "uploaded_reviews.csv"), index=False)
        
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
    possible_columns = ["content", "review", "text", "comment", "review_text", "body"]
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
    
    # Offload inference-only analysis to the background.
    # Uploaded CSVs are for testing/analysis, never for model training.
    background_tasks.add_task(_process_reviews_job, df)

    return {
        "message": "Upload successful. AI Analysis started in the background.",
        "total_reviews": len(df)
    }
