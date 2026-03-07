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

        # ── PHASE 24 SETUP: Pre-build taxonomy category embeddings ────────────
        # We import here to reuse the singleton that's already cached
        from app.ml.issue_labeler import (
            _build_taxonomy_embeddings, _taxonomy_embeddings, _taxonomy_labels,
            ISSUE_TAXONOMY, _encoder as _il_encoder
        )
        import app.ml.issue_labeler as il_module
        # Inject the already-loaded encoder so we don't load it twice
        il_module._encoder = self.encoder
        _build_taxonomy_embeddings()
        # Pull the computed centroids into local vars for speed
        taxonomy_matrix = il_module._taxonomy_embeddings  # (n_cats, 384)
        taxonomy_labels = il_module._taxonomy_labels       # list[str]
        CONFIDENCE_THRESHOLD = 0.30  # Reviews below this → General App Feedback
        # ─────────────────────────────────────────────────────────────────────

        batch_size = 64  # Smaller batches: SBERT encode per batch
        for i in range(0, total_valid, batch_size):
            if self.should_stop:
                print(f"Topic analysis stopped at {i} reviews.")
                break

            try:
                batch_reviews = reviews[i:i + batch_size]
                batch_dates = dates[i:i + batch_size]

                # ── NMF: kept for ASPECT detection only ───────────────────────
                X_batch_nmf = self.nmf_vectorizer.transform(batch_reviews)
                W_batch = self.nmf_model.transform(X_batch_nmf)

                # ── PHASE 24.1: Direct Per-Review Semantic Classification ──────
                # Encode all reviews in batch at once (vectorized for speed)
                review_embeddings = self.encoder.encode(
                    batch_reviews, batch_size=64, normalize_embeddings=True, show_progress_bar=False
                )
                # (batch, 384) @ (384, n_cats) → (batch, n_cats)
                sim_matrix = np.dot(review_embeddings, taxonomy_matrix.T)
                best_cat_ids = np.argmax(sim_matrix, axis=1)
                best_scores  = sim_matrix[np.arange(len(batch_reviews)), best_cat_ids]

                for j in range(len(batch_reviews)):
                    # ── PHASE 24.3: Confidence Threshold Routing ──────────────
                    confidence = float(best_scores[j])
                    canonical_label = (
                        taxonomy_labels[best_cat_ids[j]]
                        if confidence >= CONFIDENCE_THRESHOLD
                        else "General App Feedback"
                    )

                    # Track Aspects for ABSA using NMF signal
                    aspects = self.analyze_aspects(batch_reviews[j])
                    for aspect in aspects:
                        aspect_stats[aspect] += 1

                    if canonical_label not in topic_stats:
                        topic_stats[canonical_label] = {
                            "keywords": canonical_label,
                            "mentions": 0,
                            "monthly_mentions": {},
                            "sample_reviews_heap": []  # (confidence, text)
                        }

                    topic_stats[canonical_label]["mentions"] += 1

                    # Track timeseries (Phase 16) — keyed by canonical label
                    month_str = batch_dates[j]
                    if month_str != "NaT":
                        topic_stats[canonical_label]["monthly_mentions"][month_str] = (
                            topic_stats[canonical_label]["monthly_mentions"].get(month_str, 0) + 1
                        )

                    # Evidence collection — keep top reviews by confidence score
                    review_text = str(batch_reviews[j])
                    if len(review_text) > 40:
                        heap = topic_stats[canonical_label]["sample_reviews_heap"]
                        if len(heap) < 20:
                            heapq.heappush(heap, (confidence, review_text))
                        elif confidence > heap[0][0]:
                            heapq.heapreplace(heap, (confidence, review_text))

            except Exception as e:
                print(f"Error processing topic batch {i}: {e}")

            # Update progress
            self.progress["processed"] = min(total_valid, i + batch_size)
            self.progress["status"] = f"Analyzing topics... {self.progress['processed']}/{total_valid}"

        # ── PHASE 24.2: EVIDENCE RE-RANKING + NEAR-DUPLICATE DEDUPLICATION ──────
        # topic_stats is already keyed by canonical label — no merging needed.
        # For each category: re-rank by label alignment, then deduplicate.
        print("[Phase 24] Running evidence deduplication and re-ranking...")
        results = []
        for canonical_label, data in topic_stats.items():
            candidates = [r[1] for r in data["sample_reviews_heap"]]

            if not candidates:
                results.append({
                    "topic_id": canonical_label,
                    "keywords": canonical_label,
                    "label": canonical_label,
                    "mentions": data["mentions"],
                    "sample_reviews": []
                })
                continue

            # Re-rank candidates against the canonical label for best alignment
            label_emb = self.encoder.encode([canonical_label], normalize_embeddings=True)
            cand_embs = self.encoder.encode(candidates, normalize_embeddings=True)
            sims      = np.dot(cand_embs, label_emb.T).flatten()
            ranked    = sorted(zip(sims, candidates), key=lambda x: x[0], reverse=True)

            # ── PHASE 24.2: Near-Duplicate Deduplication ────────────────────
            # Remove reviews that are too semantically similar to each other.
            DEDUP_THRESHOLD = 0.85
            kept_embs = []
            final_reviews = []
            for score, text in ranked:
                if len(final_reviews) >= 15:
                    break
                if kept_embs:
                    # Compute similarity of this review to all already-kept reviews
                    candidate_emb = cand_embs[candidates.index(text)]
                    kept_matrix   = np.array(kept_embs)
                    max_sim       = float(np.max(np.dot(kept_matrix, candidate_emb)))
                    if max_sim >= DEDUP_THRESHOLD:
                        continue  # Skip near-duplicate
                kept_embs.append(cand_embs[candidates.index(text)])
                final_reviews.append(text)
            # ────────────────────────────────────────────────────────────────

            results.append({
                "topic_id": canonical_label,
                "keywords": canonical_label,
                "label": canonical_label,
                "mentions": data["mentions"],
                "sample_reviews": final_reviews
            })

        # Export core topic clusters — already canonical, no Phase 23 merge needed
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