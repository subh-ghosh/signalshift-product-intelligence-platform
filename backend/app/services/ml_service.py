import joblib
import pickle
import time
import os
import numpy as np
import heapq

from sentence_transformers import SentenceTransformer

from app.ml.text_cleaner import clean_text
from app.ml.spam_filter import is_valid_review
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

        print("Loading topic model (NMF Precision Upgrade)...")

        self.nmf_model = joblib.load(os.path.join(MODEL_DIR, "nmf_model.joblib"))
        self.nmf_vectorizer = joblib.load(os.path.join(MODEL_DIR, "nmf_vectorizer.joblib"))

        # Pre-extract keywords for each NMF topic
        self.topic_keywords = []
        feature_names = self.nmf_vectorizer.get_feature_names_out()
        for topic_idx, topic in enumerate(self.nmf_model.components_):
            top_words = [feature_names[i] for i in topic.argsort()[:-6:-1]]
            self.topic_keywords.append(", ".join(top_words))
        
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
        
        print("Loading SentenceTransformer (Dynamic Alignment Engine)...")
        # Lightweight but accurate model for semantic similarity reranking
        # FORCING CPU to avoid CUDA capability sm_61 errors on this machine
        self.encoder = SentenceTransformer('all-MiniLM-L6-v2', device='cpu')
        
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

        cleaned = clean_text(review)
        
        # Use LDA instead of embeddings
        counts = self.count_vectorizer.transform([cleaned])
        topic_probs = self.lda_model.transform(counts)[0]
        
        best_index = int(np.argmax(topic_probs))
        keywords = self.topic_keywords[best_index]

        return {
            "topic_id": best_index,
            "keywords": keywords
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
        self.progress["total"] = total_negative
        self.progress["processed"] = 0
        self.progress["start_time"] = time.time()
            
        if total_negative == 0:
            pd.DataFrame(columns=['topic_id', 'keywords', 'mentions', 'sample_reviews']).to_csv("data/processed/topic_analysis.csv", index=False)
            self.progress["status"] = "idle"
            return
            
        raw_reviews = negative_df["content"].astype(str).tolist()
        
        # PRE-PROCESSING (Phase 14): Filter out spam/junk before NLP
        print(f"[Phase 14] Pre-processing {total_negative} negative reviews for data quality...")
        # Create a boolean mask for valid reviews to preserve dataframe structure
        mask = negative_df["content"].astype(str).apply(is_valid_review)
        valid_df = negative_df[mask].copy()
        
        reviews = valid_df["content"].astype(str).tolist()
        
        # Track dates for Phase 16 Time-Series
        date_col = 'at' if 'at' in valid_df.columns else 'date' if 'date' in valid_df.columns else None
        if date_col:
            dates = pd.to_datetime(valid_df[date_col], errors="coerce").dt.to_period("M").astype(str).tolist()
        else:
            dates = ["Unknown"] * len(reviews)
            
        filtered_out = total_negative - len(reviews)
        total_valid = len(reviews)
        print(f"[Phase 14] Filtered out {filtered_out} low-quality/spam reviews. Kept {total_valid}.")
        
        # Update progress tracker to reflect the filtered total for accurate ETA
        self.progress["total"] = total_valid
        
        if total_valid == 0:
            pd.DataFrame(columns=['topic_id', 'keywords', 'mentions', 'sample_reviews']).to_csv("data/processed/topic_analysis.csv", index=False)
            self.progress["status"] = "idle"
            return
            
        topic_stats = {}
        aspect_stats = {aspect: 0 for aspect in self.aspect_config.keys()}
        aspect_stats["General"] = 0
        
        batch_size = 512 # LDA is much faster than BERT
        for i in range(0, total_valid, batch_size):
            if self.should_stop:
                print(f"Topic analysis stopped at {i} reviews.")
                break
                
            try:
                batch_reviews = reviews[i:i + batch_size]
                batch_dates = dates[i:i + batch_size]
                
                cleaned_batch = [clean_text(r) for r in batch_reviews]
                
                # Vector-based Topic Discovery (NMF)
                # This gives us a score for how well a review fits each topic
                X_batch_nmf = self.nmf_vectorizer.transform(batch_reviews)
                print(f"DEBUG: Batch {i} vectorized. Shape: {X_batch_nmf.shape}")
                
                W_batch = self.nmf_model.transform(X_batch_nmf)
                print(f"DEBUG: Batch {i} transformed by NMF. Shape: {W_batch.shape}")

                for j in range(len(batch_reviews)):
                    # Get the most relevant topic ID
                    dist = W_batch[j]
                    if np.max(dist) < 0.05:  # Dynamic Threshold (Phase 14.2): Only accept confident matches
                        continue
                        
                    t_id = int(np.argmax(dist))
                    semantic_score = dist[t_id]
                    keywords = self.topic_keywords[t_id]
                    
                    # Track Aspects for ABSA
                    aspects = self.analyze_aspects(batch_reviews[j])
                    for aspect in aspects:
                        aspect_stats[aspect] += 1

                    if t_id not in topic_stats:
                        topic_stats[t_id] = {
                            "keywords": keywords,
                            "mentions": 0,
                            "monthly_mentions": {},
                            "sample_reviews_heap": [] # (score, text)
                        }
                        
                    topic_stats[t_id]["mentions"] += 1
                    
                    # Track timeseries (Phase 16)
                    month_str = batch_dates[j]
                    if month_str != "NaT":
                        topic_stats[t_id]["monthly_mentions"][month_str] = topic_stats[t_id]["monthly_mentions"].get(month_str, 0) + 1
                    
                    # SEMANTIC EVIDENCE SELECTOR (Phase 12)
                    # We keep only the top 15 reviews with the highest semantic scores
                    review_text = str(batch_reviews[j])
                    if len(review_text) > 40:
                        # Use a min-heap to keep the top 15 results
                        if len(topic_stats[t_id]["sample_reviews_heap"]) < 15:
                            heapq.heappush(topic_stats[t_id]["sample_reviews_heap"], (semantic_score, review_text))
                        elif semantic_score > topic_stats[t_id]["sample_reviews_heap"][0][0]:
                            heapq.heapreplace(topic_stats[t_id]["sample_reviews_heap"], (semantic_score, review_text))

            except Exception as e:
                print(f"Error processing topic batch {i}: {e}")
            
            # Update progress
            self.progress["processed"] = min(total_valid, (i + batch_size))
            self.progress["status"] = f"Analyzing topics... {self.progress['processed']}/{total_valid}"

        # SEMANTIC RERANKING STAGE (Phase 13)
        # We now have the mathematical top candidates. 
        # We will use SentenceBERT to align them with human-readable labels.
        results = []
        for t_id, data in topic_stats.items():
            label = generate_issue_label(data["keywords"], encoder=self.encoder)
            candidates = [r[1] for r in data["sample_reviews_heap"]]
            
            if not candidates:
                results.append({
                    "topic_id": t_id,
                    "keywords": data["keywords"],
                    "label": label,
                    "mentions": data["mentions"],
                    "sample_reviews": []
                })
                continue

            # Calculate similarity between the Label and the candidate Reviews
            label_embedding = self.encoder.encode([label])
            review_embeddings = self.encoder.encode(candidates)
            
            # Simple Cosine Similarity (Dot product for normalized vectors)
            similarities = np.dot(review_embeddings, label_embedding.T).flatten()
            
            # Pair reviews with their alignment score and sort
            reranked = sorted(zip(similarities, candidates), key=lambda x: x[0], reverse=True)
            aligned_reviews = [r[1] for r in reranked[:15]] # Top 15 best aligned

            results.append({
                "topic_id": t_id,
                "keywords": data["keywords"],
                "label": label,
                "mentions": data["mentions"],
                "sample_reviews": aligned_reviews
            })
            
        # Export core topic clusters
        cache_df = pd.DataFrame(results).sort_values(by="mentions", ascending=False)
        cache_df.to_csv("data/processed/topic_analysis.csv", index=False)
        
        # Export time-series trending data (Phase 16)
        timeseries_data = []
        for t_id, data in topic_stats.items():
            label = generate_issue_label(data["keywords"], encoder=self.encoder)
            for month_str, m_count in data.get("monthly_mentions", {}).items():
                timeseries_data.append({
                    "topic_id": t_id,
                    "issue_label": label,
                    "month": month_str,
                    "mentions": m_count
                })
        
        if timeseries_data:
            pd.DataFrame(timeseries_data).to_csv("data/processed/topic_timeseries.csv", index=False)
        
        # Save Aspect Stats for Dashboard Heatmap
        aspect_rows = [{"aspect": k, "mentions": v} for k, v in aspect_stats.items()]
        pd.DataFrame(aspect_rows).to_csv("data/processed/aspect_analysis.csv", index=False)

        # Trigger Threshold Check
        print("[!] Checking critical thresholds...")
        self.alerting_service.check_thresholds()

        self.progress["status"] = "complete"
        print(f"Successfully generated and cached new topic_analysis.csv for {total_valid} high-quality reviews (filtered {filtered_out} spam).")