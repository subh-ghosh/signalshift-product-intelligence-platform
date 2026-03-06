from fastapi import APIRouter, UploadFile, File
from pydantic import BaseModel
from typing import List
import pandas as pd
import os

from app.services.csv_processor import process_uploaded_csv

router = APIRouter()

ml_service = None


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

    df = get_dashboard_dataset()

    if "sentiment" in df.columns:
        df = df[df["sentiment"] == "negative"]

    issue_counter = {}
    keyword_map = {}

    reviews = df["content"].astype(str).tolist()

    for review in reviews:

        result = ml_service.analyze_review(review)

        keywords = result["topic_keywords"]

        label = generate_issue_label(keywords)

        issue_counter[label] = issue_counter.get(label, 0) + 1

        keyword_map[label] = keywords


    sorted_issues = sorted(
        issue_counter.items(),
        key=lambda x: x[1],
        reverse=True
    )

    issues = []

    for issue, count in sorted_issues[:10]:

        issues.append({
            "issue": issue,
            "keywords": keyword_map[issue],
            "mentions": count
        })

    return issues

# -----------------------------
# REVIEWS FOR ISSUE
# -----------------------------

@router.get("/dashboard/issue-reviews")
def issue_reviews(issue: str):

    from app.ml.issue_labeler import generate_issue_label

    df = get_dashboard_dataset()

    if "sentiment" in df.columns:
        df = df[df["sentiment"] == "negative"]

    matching_reviews = []
    
    reviews = df["content"].astype(str).tolist()
    
    for review in reviews:
        result = ml_service.analyze_review(review)
        label = generate_issue_label(result["topic_keywords"])
        if label == issue:
            matching_reviews.append(review)
            if len(matching_reviews) >= 20: 
                break

    return {
        "issue": issue,
        "reviews": matching_reviews
    }

# -----------------------------
# REVIEWS LIST
# -----------------------------

@router.get("/dashboard/reviews")
def reviews():

    df = get_dashboard_dataset()

    return df.head(50).to_dict(orient="records")


# -----------------------------
# Upload Reviews CSV
# -----------------------------

@router.post("/upload-reviews")
async def upload_reviews(file: UploadFile = File(...)):

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

    reviews = df[review_column].astype(str).tolist()

    sentiments = []

    for r in reviews:
        sentiment = ml_service.predict_sentiment(r)
        sentiments.append(sentiment)

    df["content"] = reviews
    df["sentiment"] = sentiments
    df["cleaned_content"] = df["content"].str.lower()

    os.makedirs("data/processed", exist_ok=True)

    df.to_csv("data/processed/uploaded_reviews.csv", index=False)

    return {
        "message": "Reviews uploaded and processed",
        "total_reviews": len(df)
    }