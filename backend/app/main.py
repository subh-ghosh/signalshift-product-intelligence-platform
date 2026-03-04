from fastapi import FastAPI
from pydantic import BaseModel
from typing import List

from app.services.ml_service import MLService


app = FastAPI(
    title="SignalShift API",
    description="AI-powered product feedback intelligence system",
    version="1.0"
)

# Load ML models once at startup
ml_service = MLService()


# -----------------------------
# Request Schemas
# -----------------------------

class ReviewRequest(BaseModel):
    review: str


class BatchReviewRequest(BaseModel):
    reviews: List[str]


# -----------------------------
# Health Check
# -----------------------------

@app.get("/")
def root():
    return {"message": "SignalShift API is running"}


@app.get("/health")
def health():
    return {"status": "healthy"}


# -----------------------------
# Analyze Single Review
# -----------------------------

@app.post("/analyze-review")
def analyze_review(request: ReviewRequest):

    result = ml_service.analyze_review(request.review)

    return result


# -----------------------------
# Analyze Multiple Reviews
# -----------------------------

@app.post("/analyze-batch")
def analyze_batch(request: BatchReviewRequest):

    results = []

    for review in request.reviews:
        result = ml_service.analyze_review(review)
        results.append(result)

    return {
        "total_reviews": len(results),
        "results": results
    }

@app.post("/detect-issues")
def detect_issues(request: BatchReviewRequest):

    issues = ml_service.detect_issues(request.reviews)

    return {
        "total_reviews": len(request.reviews),
        "top_issues": issues
    }