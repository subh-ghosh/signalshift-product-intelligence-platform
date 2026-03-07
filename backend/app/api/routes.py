from fastapi import APIRouter, UploadFile, File, BackgroundTasks
from pydantic import BaseModel
from typing import List
import pandas as pd
import os

from app.services.csv_processor import process_uploaded_csv
from app.services.data_sync_service import DataSyncService
from app.services.report_service import ReportService
from app.services.alerting_service import AlertingService
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
def sentiment_distribution():
    df = get_dashboard_dataset()
    positive = (df["sentiment"] == "positive").sum()
    negative = (df["sentiment"] == "negative").sum()
    return {
        "positive": int(positive),
        "negative": int(negative)
    }


# -----------------------------
# TOP ISSUES
# -----------------------------

@router.get("/dashboard/top-issues")
def top_issues():
    from app.ml.issue_labeler import generate_issue_label
    try:
        topic_df = pd.read_csv("data/processed/topic_analysis.csv")
        issues = []
        top_10 = topic_df.head(10)
        for _, row in top_10.iterrows():
            keywords = str(row["keywords"])
            mentions = int(row["mentions"])
            label = generate_issue_label(keywords)
            issues.append({
                "issue": label,
                "keywords": keywords,
                "mentions": mentions
            })
        return issues
    except FileNotFoundError:
        return []


# -----------------------------
# TOP ASPECTS (ABSA)
# -----------------------------

@router.get("/dashboard/aspects")
def top_aspects():
    try:
        aspect_df = pd.read_csv("data/processed/aspect_analysis.csv")
        return aspect_df.to_dict(orient="records")
    except FileNotFoundError:
        return []

# -----------------------------
# AUTOMATION & REPORTING
# -----------------------------

@router.get("/dashboard/alerts")
async def get_alerts():
    """Returns any active threshold alerts."""
    return {"alerts": alerting_service.get_active_alerts()}

@router.get("/dashboard/topic-benchmark")
def get_topic_benchmark():
    """Returns the qualitative shift in intelligence after our core model upgrade."""
    try:
        df = pd.read_csv("data/processed/topic_evolution_summary.csv")
        return df.to_dict(orient="records")
    except FileNotFoundError:
        return []

@router.get("/dashboard/export-pdf")
async def export_report():
    """Generates and returns a branded PDF executive report."""
    report_path = report_service.generate_pdf_report()
    if not report_path or not os.path.exists(report_path):
        return {"error": "Failed to generate report"}
    
    return FileResponse(
        path=report_path,
        filename=f"SignalShift_Executive_Report_{pd.Timestamp.now().strftime('%Y%m%d')}.pdf",
        media_type="application/pdf"
    )

# -----------------------------
# REVIEWS FOR ISSUE
# -----------------------------

@router.get("/dashboard/issue-reviews")
def issue_reviews(issue: str):
    from app.ml.issue_labeler import generate_issue_label
    import ast
    try:
        topic_df = pd.read_csv("data/processed/topic_analysis.csv")
        matching_reviews = []
        for _, row in topic_df.iterrows():
            keywords = str(row["keywords"])
            label = generate_issue_label(keywords)
            if label == issue:
                try:
                    matching_reviews = ast.literal_eval(row["sample_reviews"])
                except Exception:
                    rev_string = str(row["sample_reviews"]).strip('[]')
                    matching_reviews = [r.strip(" '\"") for r in rev_string.split("', '")]
                break
        return {
            "issue": issue,
            "reviews": matching_reviews[:20]
        }
    except FileNotFoundError:
        return {
            "issue": issue,
            "reviews": []
        }

# -----------------------------
# REVIEWS LIST
# -----------------------------

@router.get("/dashboard/reviews")
def reviews():
    df = get_dashboard_dataset()
    return df.head(50).to_dict(orient="records")


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