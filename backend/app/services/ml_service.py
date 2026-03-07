import joblib
import pickle
import time
import os
import numpy as np
import heapq

from sentence_transformers import SentenceTransformer

from app.ml.text_cleaner import clean_text
from app.ml.spam_filter import is_valid_review
from app.ml.dynamic_cluster_service import DynamicClusteringService
from .alerting_service import AlertingService
from app.ml.issue_labeler import generate_issue_label


class MLService:

    def __init__(self):

        print("Loading ML models...")

        # Robust path detection
        BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        MODEL_DIR = os.path.join(BASE_DIR, "models")

        # sentiment model v2 (Bi-gram optimized)
        self.sentiment_model = joblib.load(os.path.join(MODEL_DIR, "sentiment_model_v2.joblib"))

        # tfidf vectorizer v2
        self.vectorizer = joblib.load(os.path.join(MODEL_DIR, "tfidf_vectorizer_v2.joblib"))

        print("Loading SOTA Topic Model (Dynamic Embeddings Pipeline)...")
        # Initialize Phase 15 Dynamic HDBSCAN-based Service
        self.dynamic_cluster_service = DynamicClusteringService()
        
        # Progress tracking for large uploads
        self.progress = {
            "processed": 0, 
            "total": 0, 
            "status": "idle",
            "eta_seconds": 0,
            "start_time": None
        }
        self.should_stop = False

        # Aspect-Based Sentiment Analysis (ABSA) Logic
        # These categories allow B2B customers to see WHY people are unhappy
        self.aspect_config = {
            "Performance/Technical": ["crash", "lag", "buffer", "freeze", "slow", "loading", "error", "bug"],
            "Content/Library": ["movie", "show", "series", "selection", "episodes", "watch", "boring"],
            "UI/UX Experience": ["interface", "design", "navigation", "button", "screen", "search", "easy"],
            "Pricing/Subscription": ["expensive", "price", "money", "subscription", "plan", "cancel", "worth"],
        }
        
        self.alerting_service = AlertingService()
        
        print("ML models loaded successfully.")

    def _update_eta(self, processed, total, start_time):
        """Calculates estimated seconds remaining based on processing speed"""
        if processed == 0 or start_time is None:
            return 0
        
        elapsed = time.time() - start_time
        speed = processed / elapsed  # items per second
        remaining = total - processed
        
        if speed > 0:
            return round(remaining / speed)
        return 0

    def stop_analysis(self):
        """Signals the background job to stop early"""
        self.should_stop = True
        self.progress["status"] = "stopping"

    # -------------------------
    # Sentiment
    # -------------------------

    def predict_sentiment(self, review):

        cleaned = clean_text(review)

        vector = self.vectorizer.transform([cleaned])

        sentiment = self.sentiment_model.predict(vector)[0]

        return sentiment

    def predict_sentiment_batch(self, reviews):
        """Vectorized sentiment prediction for large batches with progress tracking"""
        self.should_stop = False
        total = len(reviews)
        self.progress["total"] = total
        self.progress["processed"] = 0
        self.progress["status"] = "sentiment"
        self.progress["start_time"] = time.time()
        self.should_stop = False
        
        sentiments = []
        batch_size = 512  # Sentiment is faster, use larger batches
        
        for i in range(0, total, batch_size):
            if self.should_stop:
                print(f"Sentiment analysis stopped at {i} reviews.")
                break
                
            try:
                batch = reviews[i:i + batch_size]
                cleaned_reviews = [clean_text(r) for r in batch]
                vectors = self.vectorizer.transform(cleaned_reviews)
                batch_sentiments = self.sentiment_model.predict(vectors)
                sentiments.extend(batch_sentiments.tolist())
            except Exception as e:
                print(f"Error processing sentiment batch {i}: {e}")
                # Fill with neutral or error label if batch fails
                sentiments.extend(["neutral"] * len(batch))
            
            self.progress["processed"] = min(i + batch_size, total)
            self.progress["eta_seconds"] = self._update_eta(
                self.progress["processed"], 
                total, 
                self.progress["start_time"]
            )
            
        return sentiments

    # -------------------------
    # Topic detection
    # -------------------------

    def predict_topic(self, review):
        # Deprecated for single reviews in Phase 15 (HDBSCAN requires dense groups)
        return {
            "topic_id": 0,
            "keywords": "General Issues"
        }

    # -------------------------
    # Aspect Detection (ABSA)
    # -------------------------

    def analyze_aspects(self, review):
        """Identifies specific business areas mentioned in the review"""
        text = review.lower()
        detected = []
        
        for aspect, keywords in self.aspect_config.items():
            if any(word in text for word in keywords):
                detected.append(aspect)
                
        return detected if detected else ["General"]

    # -------------------------
    # Full analysis
    # -------------------------

    def analyze_review(self, review):

        sentiment = self.predict_sentiment(review)
        topic_info = self.predict_topic(review)
        aspects = self.analyze_aspects(review)

        return {
            "review": review,
            "sentiment": sentiment,
            "topic_id": topic_info["topic_id"],
            "topic_keywords": topic_info["keywords"],
            "aspects": aspects
        }

    # -------------------------
    # Issue detection for batch
    # -------------------------

    def detect_issues(self, reviews):

        issue_counter = {}

        for review in reviews:

            result = self.analyze_review(review)

            issue = result["topic_keywords"]

            issue_counter[issue] = issue_counter.get(issue, 0) + 1

        sorted_issues = sorted(
            issue_counter.items(),
            key=lambda x: x[1],
            reverse=True
        )

        issues = []

        for issue, count in sorted_issues[:10]:

            issues.append({
                "issue": issue,
                "mentions": count
            })

        return issues
        
    # -------------------------
    # Dashboard Cache Generation
    # -------------------------
    
    def generate_topic_analysis_cache(self, df):
        """
        Runs batch inference on a newly uploaded dataset's negative reviews
        using vectorized batch encoding for high performance.
        """
        import pandas as pd
        self.should_stop = False
        
        self.progress["status"] = "analyzing"
        
        # Only analyze negative sentiment
        if "sentiment" in df.columns:
            negative_df = df[df["sentiment"] == "negative"].copy()
        else:
            negative_df = df.copy()
            
        total_negative = len(negative_df)
        
        # We NO LONGER reset total/processed here, to keep the master 
        # UI progress bar completely stable at 100% (e.g. 17,969 total)
        self.progress["start_time"] = time.time()
            
        if total_negative == 0:
            pd.DataFrame(columns=['topic_id', 'keywords', 'mentions', 'sample_reviews']).to_csv("data/processed/topic_analysis.csv", index=False)
            self.progress["status"] = "idle"
            return
            
        raw_reviews = negative_df["content"].astype(str).tolist()
        
        # PRE-PROCESSING (Phase 14): Filter out spam/junk before NLP
        print(f"[Phase 14] Pre-processing {total_negative} negative reviews for data quality...")
        reviews = [r for r in raw_reviews if is_valid_review(r)]
        filtered_out = total_negative - len(reviews)
        total_valid = len(reviews)
        print(f"[Phase 14] Filtered out {filtered_out} low-quality/spam reviews. Kept {total_valid}.")
        
        if total_valid == 0:
            pd.DataFrame(columns=['topic_id', 'keywords', 'mentions', 'sample_reviews']).to_csv("data/processed/topic_analysis.csv", index=False)
            self.progress["status"] = "idle"
            return
            
        aspect_stats = {aspect: 0 for aspect in self.aspect_config.keys()}
        aspect_stats["General"] = 0
        
        # Track Aspects independently for the Heatmap logic
        for r in reviews:
            aspects = self.analyze_aspects(r)
            for aspect in aspects:
                aspect_stats[aspect] += 1
                
        # PHASE 15: CPU Performance Downsampling
        import random
        if len(reviews) > 15000:
            print(f"[Phase 15] Downsampling from {len(reviews)} to 15,000 to drastically speed up CPU Embedding...")
            sample_reviews = random.sample(reviews, 15000)
            multiplier = len(reviews) / 15000
        else:
            sample_reviews = reviews
            multiplier = 1.0

        # Single Call Semantic Density Extraction
        # It now streams embedding progress directly to the UI dynamically!
        results = self.dynamic_cluster_service.extract_dynamic_topics(sample_reviews, self.progress)
        
        # Ensure progress finishes visually when complete
        self.progress["processed"] = self.progress.get("total", total_valid)
        self.progress["eta_seconds"] = 0 
        self.progress["status"] = "Generating Dashboard Assets..."

        # Add human readable labels and linearly scale mentions back up to true volume
        final_results = []
        for r in results:
            r["label"] = generate_issue_label(r["keywords"])
            r["mentions"] = int(r["mentions"] * multiplier) # Scale up to represent true 147k volume
            final_results.append(r)
            
        cache_df = pd.DataFrame(final_results).sort_values(by="mentions", ascending=False)
        cache_df.to_csv("data/processed/topic_analysis.csv", index=False)
        
        # Save Aspect Stats for Dashboard Heatmap
        aspect_rows = [{"aspect": k, "mentions": v} for k, v in aspect_stats.items()]
        pd.DataFrame(aspect_rows).to_csv("data/processed/aspect_analysis.csv", index=False)


        # Trigger Threshold Check
        print("[!] Checking critical thresholds...")
        self.alerting_service.check_thresholds()

        self.progress["status"] = "complete"
        print(f"Successfully generated and cached new topic_analysis.csv for {total_valid} high-quality reviews (filtered {filtered_out} spam).")