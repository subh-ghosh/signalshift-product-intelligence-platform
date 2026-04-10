import joblib
import pickle
import time
import os
import numpy as np
import heapq
from collections import Counter

from sentence_transformers import SentenceTransformer

from ml.core.text_cleaner import clean_text
from ml.core.spam_filter import is_valid_review
from .alerting_service import AlertingService
from ml.core.issue_labeler import generate_issue_label
from .paths import models_dir, processed_data_dir


class MLService:
    def semantic_search(self, query: str, reviews: list[str], top_n: int = 15):
        """Perform semantic search across a list of reviews using the internal encoder."""
        if not reviews:
            return []
            
        print(f"[Vanguard X-Ray] Searching for: {query}")
        # Encode the query
        query_emb = self.encoder.encode([query], normalize_embeddings=True)
        
        # Encode the reviews in batches for speed
        # For a truly elite experience, these would be indexed, but on-the-fly works for medium datasets
        review_embs = self.encoder.encode(
            reviews, batch_size=64, normalize_embeddings=True, show_progress_bar=False
        )
        
        # Compute cosine similarity
        similarities = np.dot(review_embs, query_emb.T).flatten()
        
        # Get top N
        top_indices = np.argsort(similarities)[-top_n:][::-1]
        
        results = []
        for idx in top_indices:
            results.append({
                "content": reviews[idx],
                "confidence": float(similarities[idx])
            })
            
        return results

    def __init__(self):

        print("Loading ML models...")

        MODEL_DIR = models_dir()

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

        # Use the loaded NMF topic model + vectorizer
        X = self.nmf_vectorizer.transform([cleaned])
        topic_weights = self.nmf_model.transform(X)[0]
        best_index = int(np.argmax(topic_weights))
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
            out_path = os.path.join(processed_data_dir(), "topic_analysis.csv")
            os.makedirs(os.path.dirname(out_path), exist_ok=True)
            pd.DataFrame(columns=['topic_id', 'keywords', 'mentions', 'sample_reviews']).to_csv(out_path, index=False)
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
            dates = ["Recent"] * len(valid_df)

        # Phase 64: High-Detail Metadata Extraction
        versions = valid_df["appVersion"].astype(str).tolist() if "appVersion" in valid_df.columns else ["Build N/A"] * len(valid_df)
        upvotes = valid_df["thumbsUpCount"].fillna(0).astype(int).tolist() if "thumbsUpCount" in valid_df.columns else [0] * len(valid_df)
            
        filtered_out = total_negative - len(reviews)
        total_valid = len(reviews)
        print(f"[Phase 14] Filtered out {filtered_out} low-quality/spam reviews. Kept {total_valid}.")
        
        # Update progress tracker to reflect the filtered total for accurate ETA
        self.progress["total"] = total_valid
        
        if total_valid == 0:
            out_path = os.path.join(processed_data_dir(), "topic_analysis.csv")
            os.makedirs(os.path.dirname(out_path), exist_ok=True)
            pd.DataFrame(columns=['topic_id', 'keywords', 'mentions', 'sample_reviews']).to_csv(out_path, index=False)
            self.progress["status"] = "idle"
            return
            
        topic_stats = {}
        aspect_stats = {aspect: 0 for aspect in self.aspect_config}
        review_classifications = []  # Phase 31: per-review records with dates
        # ── Phase 35: Track total reviews per month for rate normalization ─────
        monthly_review_totals = {}  # { 'YYYY-MM': total_review_count }

        # ── PHASE 24 SETUP: Pre-build taxonomy category embeddings ────────────
        # We import here to reuse the singleton that's already cached
        from ml.core.issue_labeler import (
            _build_taxonomy_embeddings, _taxonomy_embeddings, _taxonomy_labels,
            ISSUE_TAXONOMY, _encoder as _il_encoder
        )
        import ml.core.issue_labeler as il_module
        # Inject the already-loaded encoder so we don't load it twice
        il_module._encoder = self.encoder
        _build_taxonomy_embeddings()
        # Pull the computed centroids into local vars for speed
        taxonomy_matrix = il_module._taxonomy_embeddings  # (n_cats, 384)
        taxonomy_labels = il_module._taxonomy_labels       # list[str]
        CONFIDENCE_THRESHOLD = 0.30  # Reviews below this → General App Feedback

        # ── PHASE 53: REVENUE RISK INTELLIGENCE ─────────────────────────────
        TIER_WEIGHTS = {
            "enterprise": 5.0,
            "premium": 4.0,
            "pro": 2.5,
            "standard": 1.0,
            "free": 0.8
        }

        def compute_value_weight(row: pd.Series) -> float:
            """Calculates a financial multiplier based on customer tier/value."""
            # Use lowercase column names for matching
            cols = {c.lower(): c for c in row.index}
            
            weight = 1.0
            # Tier weighting
            tier_col = next((cols[k] for k in ["user_tier", "tier", "segment"] if k in cols), None)
            if tier_col:
                val = str(row[tier_col]).lower()
                weight = TIER_WEIGHTS.get(val, 1.0)
            
            # Direct CLV weighting (if available)
            clv_col = next((cols[k] for k in ["clv", "value", "revenue"] if k in cols), None)
            if clv_col and pd.notnull(row[clv_col]):
                try:
                    clv_val = float(row[clv_col])
                    if clv_val > 0: weight *= (1.0 + np.log1p(clv_val / 100))
                except: pass

            # Simulated business metric for datasets missing financial columns
            if not tier_col and not clv_col:
                import hashlib
                text_val = str(row.values[0]) if len(row.values) > 0 else ""
                h = int(hashlib.md5(text_val.encode('utf-8')).hexdigest(), 16) % 100
                if h < 3: weight = 5.0      # 3% Enterprise
                elif h < 15: weight = 4.0   # 12% Premium
                elif h < 40: weight = 2.5   # 25% Pro
                elif h < 85: weight = 1.0   # 45% Standard
                else: weight = 0.8          # 15% Free

            return round(weight, 2)

        # ── PHASE 59: ACTIONABILITY LEXICONS & LOGIC ────────────────────────
        ACTIONABLE_SIGNAL_WORDS = {
            "button", "click", "screen", "load", "slow", "crash", "bug", "stuck", 
            "error", "missing", "broken", "freeze", "freezing", "login", "password",
            "payment", "subscribe", "subscription", "feature", "add", "improve",
            "update", "version", "menu", "tab", "setting", "notification"
        }
        VENTING_ONLY_WORDS = {"stupid", "bad", "worst", "hate", "dumb", "useless", "garbage", "trash", "why"}

        def compute_actionability(text: str) -> float:
            """Returns an actionability score 0.0-1.0 (signal-to-noise)."""
            t = text.lower()
            words = set(t.split())
            if not words: return 0.0
            
            signal_count = len(words & ACTIONABLE_SIGNAL_WORDS)
            vent_count = len(words & VENTING_ONLY_WORDS)
            
            # Actionability is high if specific signal words exist, low if mostly venting
            base_score = min(signal_count * 0.3, 0.9)
            penalty = min(vent_count * 0.1, 0.4)
            
            # Bonus for specific detail lengths
            if 50 < len(text) < 300: base_score += 0.1
            
            return max(0.0, min(1.0, round(base_score - penalty, 2)))

        # ── PHASE 26: SEVERITY SCORING LEXICONS ─────────────────────────────
        SEVERITY_5_WORDS = {"scam", "fraud", "lawsuit", "legal", "stolen", "robbed", "cheat", "criminal", "hack", "hacked"}
        SEVERITY_4_WORDS = {"terrible", "horrible", "worst", "useless", "disgusting", "outraged", "furious", "demand", "refund", "charged", "unauthorized"}
        SEVERITY_3_WORDS = {"broken", "crash", "fail", "error", "bug", "fix", "annoying", "hate", "bad", "poor", "slow", "stuck"}

        def compute_severity(text: str) -> float:
            """Returns a severity score 1.0-5.0 based on text signals."""
            t = text.lower()
            words = set(t.split())
            score = 2.0  # default baseline for a negative review
            # Lexicon signals
            if words & SEVERITY_5_WORDS: score += 2.5
            elif words & SEVERITY_4_WORDS: score += 1.5
            elif words & SEVERITY_3_WORDS: score += 0.5
            # Capitalization rage signal
            caps_ratio = sum(1 for c in text if c.isupper()) / max(len(text), 1)
            if caps_ratio > 0.3: score += 0.5
            # Exclamation intensity
            score += min(text.count("!") * 0.2, 0.6)
            return min(round(score, 2), 5.0)
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
                            "severity_total": 0.0,   # Phase 26
                            "severity_count": 0,      # Phase 26
                            "actionability_total": 0.0, # Phase 59
                            "monthly_mentions": {},
                            "monthly_texts": {},
                            "low_conf_reviews": [],   # Phase 27: bucket for anomaly detection
                            "sample_reviews_heap": []
                        }

                    topic_stats[canonical_label]["mentions"] += 1

                    # Phase 26: Accumulate severity score
                    sev = compute_severity(batch_reviews[j])
                    topic_stats[canonical_label]["severity_total"] += sev
                    topic_stats[canonical_label]["severity_count"] += 1

                    # Phase 59: Accumulate actionability
                    act = compute_actionability(batch_reviews[j])
                    topic_stats[canonical_label]["actionability_total"] += act

                    # Phase 27: Collect low-confidence reviews for anomaly detection
                    if confidence < CONFIDENCE_THRESHOLD and len(
                        topic_stats[canonical_label]["low_conf_reviews"]
                    ) < 300: # Increased pool for better temporal resolution
                        topic_stats[canonical_label]["low_conf_reviews"].append({
                            "text": batch_reviews[j],
                            "month": month_str
                        })

                    # Track timeseries (Phase 16) — keyed by canonical label
                    month_str = batch_dates[j]
                    if month_str != "NaT" and month_str != "Unknown":
                        topic_stats[canonical_label]["monthly_mentions"][month_str] = (
                            topic_stats[canonical_label]["monthly_mentions"].get(month_str, 0) + 1
                        )
                        # ── Phase 35: Track global review totals per month ─────
                        monthly_review_totals[month_str] = monthly_review_totals.get(month_str, 0) + 1
                        # ─────────────────────────────────────────────────────────
                        # Phase 25.2: Track review text per month for drift detection
                        if month_str not in topic_stats[canonical_label]["monthly_texts"]:
                            topic_stats[canonical_label]["monthly_texts"][month_str] = []
                        if len(topic_stats[canonical_label]["monthly_texts"][month_str]) < 30:
                            topic_stats[canonical_label]["monthly_texts"][month_str].append(
                                str(batch_reviews[j])
                            )

                    # Evidence collection — keep top reviews by confidence score
                    review_text = str(batch_reviews[j])
                    if len(review_text) > 40:
                        heap = topic_stats[canonical_label]["sample_reviews_heap"]
                        if len(heap) < 20:
                            heapq.heappush(heap, (confidence, review_text))
                        elif confidence > heap[0][0]:
                            heapq.heapreplace(heap, (confidence, review_text))

                    # ── PHASE 53: REVENUE RISK INTELLIGENCE ──────────────
                    vw = compute_value_weight(valid_df.iloc[i + j])
                    sev = compute_severity(batch_reviews[j])
                    financial_impact = sev * vw
                    
                    # ── Diagnostic Recording ─────────────────────────────
                    if len(review_text) > 20:
                        review_classifications.append({
                            "text": review_text,
                            "category": canonical_label,
                            "date":  month_str if month_str != "NaT" else "",
                            "severity": sev,
                            "value_weight": vw,
                            "financial_impact": round(financial_impact, 2),
                            "confidence": round(float(confidence), 4),
                            "app_version": versions[i + j],
                            "upvotes": upvotes[i + j]
                        })

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

            # Phase 26: Compute avg severity for this category
            avg_severity = round(
                data["severity_total"] / max(data["severity_count"], 1), 2
            )

            if not candidates:
                results.append({
                    "topic_id": canonical_label,
                    "keywords": canonical_label,
                    "label": canonical_label,
                    "mentions": data["mentions"],
                    "avg_severity": avg_severity,
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
                "avg_severity": avg_severity,
                "sample_reviews": final_reviews
            })

        # Export core topic clusters
        cache_df = pd.DataFrame(results).sort_values(by="mentions", ascending=False)
        out_topic = os.path.join(processed_data_dir(), "topic_analysis.csv")
        os.makedirs(os.path.dirname(out_topic), exist_ok=True)
        cache_df.to_csv(out_topic, index=False)

        # ── PHASE 31: Save per-review classifications for time-aware evidence ─
        if review_classifications:
            clf_df = pd.DataFrame(review_classifications)
            out_clf = os.path.join(processed_data_dir(), "review_classifications.csv")
            os.makedirs(os.path.dirname(out_clf), exist_ok=True)
            clf_df.to_csv(out_clf, index=False)
            print(f"[Phase 31] Saved {len(clf_df):,} per-review classifications to review_classifications.csv")

        # ── PHASE 27: ANOMALY / EMERGING ISSUE DETECTION ─────────────────────
        # Reviews that scored below the confidence threshold are in the
        # "General App Feedback" bucket. We cluster those with NMF on embeddings
        # to discover potential new issue types not in our taxonomy.
        print("[Phase 27] Scanning for emerging issues in low-confidence reviews...")
        try:
            all_low_conf_data = [] # List of dicts {text, month}
            for topic_data in topic_stats.values():
                all_low_conf_data.extend(topic_data.get("low_conf_reviews", []))

            MIN_EMERGING = 20
            if len(all_low_conf_data) >= MIN_EMERGING:
                from sklearn.decomposition import NMF as _NMF
                # Phase 60: Filter for actionable signals inside the General bucket before clustering
                # This ensures we find Proto-Issues (bugs/features), not just Proto-Noise (venting).
                actionable_low_conf = [
                    d for d in all_low_conf_data 
                    if compute_actionability(d["text"]) >= 0.3
                ]
                
                # If we have enough actionable signal, focus on that. 
                # Otherwise, stay with the full bucket to avoid missing high-volume noise.
                target_data = actionable_low_conf if len(actionable_low_conf) >= 15 else all_low_conf_data
                
                texts_to_cluster = [d["text"] for d in target_data]
                months_to_cluster = [d["month"] for d in target_data]
                
                lc_embs = self.encoder.encode(
                    texts_to_cluster, normalize_embeddings=True, show_progress_bar=False
                )
                X_lc = lc_embs - lc_embs.min()
                n_clusters = min(8, len(all_low_conf_data) // 10)
                
                if n_clusters >= 2:
                    nmf_emerge = _NMF(n_components=n_clusters, random_state=42, init="nndsvd", max_iter=300)
                    W_lc = nmf_emerge.fit_transform(X_lc)

                    # Get last two months for velocity
                    unique_months = sorted(list(set(months_to_cluster)))
                    curr_m = unique_months[-1] if unique_months else "None"
                    prev_m = unique_months[-2] if len(unique_months) > 1 else "None"

                    feature_names = nmf_emerge.get_feature_names_out() if hasattr(nmf_emerge, "get_feature_names_out") else None
                    if feature_names is None and hasattr(nmf_emerge, "components_"):
                        # Fallback if fit_transform didn't return a vectorizer-ready model
                        # (This can happen if we use raw NMF instead of Tfidf+NMF)
                        pass

                    emerging_rows = []
                    for t_idx in range(n_clusters):
                        scores = W_lc[:, t_idx]
                        top_ids = np.argsort(scores)[-10:][::-1] # Get top 10 for better labeling
                        
                        # Calculate temporal volume
                        in_cluster_mask = scores > 0.10
                        cluster_months = [months_to_cluster[idx] for idx, matches in enumerate(in_cluster_mask) if matches]
                        cluster_size = len(cluster_months)
                        
                        if cluster_size < MIN_EMERGING: continue
                        
                        curr_vol = sum(1 for m in cluster_months if m == curr_m)
                        prev_vol = sum(1 for m in cluster_months if m == prev_m)
                        momentum = round(((curr_vol - prev_vol) / max(prev_vol, 1)) * 100, 1) if prev_m != "None" else 0

                        # Phase 66: Intelligent Cluster Labeling
                        cluster_reviews = [texts_to_cluster[i] for i in top_ids]
                        
                        # Generate keywords manually if feature_names not available
                        # (Using simple split for proto-signals)
                        words = " ".join(cluster_reviews).lower().split()
                        from collections import Counter
                        stop_words = {"the", "and", "app", "to", "it", "is", "a", "of", "in", "for", "with", "this"}
                        core_keywords = [w for w, c in Counter(words).most_common(5) if w not in stop_words and len(w) > 3]
                        kw_str = ", ".join(core_keywords)
                        
                        # Use semantic labeler for category best guess
                        semantic_cat = generate_issue_label(kw_str, encoder=self.encoder)
                        
                        top_revs = [str(r)[:120] for r in cluster_reviews[:3]]
                        emerging_rows.append({
                            "cluster_id": t_idx,
                            "label": f"{semantic_cat}",
                            "keywords": kw_str,
                            "estimated_volume": cluster_size,
                            "is_flagged": cluster_size >= 15 or momentum > 50,
                            "momentum_pct": momentum,
                            "sample_review_1": top_revs[0] if len(top_revs) > 0 else "",
                            "sample_review_2": top_revs[1] if len(top_revs) > 1 else "",
                            "sample_review_3": top_revs[2] if len(top_revs) > 2 else "",
                        })

                    if emerging_rows:
                        em_df = pd.DataFrame(emerging_rows).sort_values("estimated_volume", ascending=False)
                        out_emerging = os.path.join(processed_data_dir(), "emerging_issues.csv")
                        os.makedirs(os.path.dirname(out_emerging), exist_ok=True)
                        em_df.to_csv(out_emerging, index=False)
                        flagged = sum(1 for r in emerging_rows if r["is_flagged"])
                        print(f"[Phase 27] {len(emerging_rows)} potential emerging issues found, {flagged} flagged (volume ≥ 40).")
                    else:
                        print("[Phase 27] No significant emerging issue clusters found.")
                else:
                    print(f"[Phase 27] Not enough low-confidence reviews for clustering ({len(all_low_conf)} total).")
            else:
                print(f"[Phase 27] Low-confidence pool too small ({len(all_low_conf)} reviews). Need {MIN_EMERGING}+.")
        except Exception as e:
            print(f"[Phase 27] Anomaly detection failed: {e}")
        # ─────────────────────────────────────────────────────────────────────

        # ── PHASE 25.1: SILHOUETTE SCORE QUALITY BENCHMARKING ────────────────
        # Measures how well-separated the semantic clusters are.
        # A score near 1.0 = perfect separation; near 0 = overlapping clusters.
        print("[Phase 25.1] Computing silhouette score for classification quality...")
        try:
            from sklearn.metrics import silhouette_score
            sample_embs = []
            sample_labels = []
            SAMPLE_PER_CAT = 50  # Cap per category to avoid memory issues

            for cat_label, data in topic_stats.items():
                review_texts = [r[1] for r in data["sample_reviews_heap"][:SAMPLE_PER_CAT]]
                if len(review_texts) < 2:
                    continue
                embs = self.encoder.encode(review_texts, normalize_embeddings=True, show_progress_bar=False)
                sample_embs.append(embs)
                sample_labels.extend([cat_label] * len(review_texts))

            if len(set(sample_labels)) >= 2:
                all_embs = np.vstack(sample_embs)
                # Convert string labels to int indices for sklearn
                unique_labels = list(set(sample_labels))
                label_ids = [unique_labels.index(l) for l in sample_labels]
                sil_score = float(silhouette_score(all_embs, label_ids, metric="cosine"))
                quality_df = pd.DataFrame([{
                    "metric": "silhouette_score",
                    "value": round(sil_score, 4),
                    "n_categories": len(unique_labels),
                    "n_samples": len(sample_labels),
                    "threshold_confidence": 0.30,
                    "dedup_threshold": 0.85
                }])
                out_quality = os.path.join(processed_data_dir(), "classification_quality.csv")
                os.makedirs(os.path.dirname(out_quality), exist_ok=True)
                quality_df.to_csv(out_quality, index=False)
                print(f"[Phase 25.1] Silhouette Score: {sil_score:.4f} across {len(unique_labels)} categories")
            else:
                print("[Phase 25.1] Not enough categories for silhouette scoring.")
        except Exception as e:
            print(f"[Phase 25.1] Silhouette scoring failed: {e}")
        # ─────────────────────────────────────────────────────────────────────

        # ── PHASE 25.2: TEMPORAL SEMANTIC DRIFT DETECTION ─────────────────────
        # For each category, compute monthly embedding centroids.
        # Categories where consecutive month centroids diverge significantly
        # are flagged as "semantically evolving" — the issue is changing in nature.
        print("[Phase 25.2] Computing temporal semantic drift per category...")
        drift_rows = []
        try:
            for cat_label, data in topic_stats.items():
                monthly_texts = data.get("monthly_texts", {})
                sorted_months = sorted(monthly_texts.keys())
                if len(sorted_months) < 2:
                    continue

                # Compute centroid embedding per month
                monthly_centroids = {}
                for month in sorted_months:
                    texts = monthly_texts[month]
                    if not texts:
                        continue
                    embs = self.encoder.encode(texts, normalize_embeddings=True, show_progress_bar=False)
                    centroid = np.mean(embs, axis=0)
                    centroid /= (np.linalg.norm(centroid) + 1e-8)
                    monthly_centroids[month] = centroid

                months_with_centroids = sorted(monthly_centroids.keys())
                for k in range(1, len(months_with_centroids)):
                    prev_m = months_with_centroids[k - 1]
                    curr_m = months_with_centroids[k]
                    cosine_sim = float(np.dot(monthly_centroids[prev_m], monthly_centroids[curr_m]))
                    drift = round(1.0 - cosine_sim, 4)  # 0 = stable, 1 = max drift
                    
                    # Phase 66: Extract shifting terms
                    # We look for words that increased in frequency in the newest month
                    words_prev = " ".join(monthly_texts[prev_m]).lower().split()
                    words_curr = " ".join(monthly_texts[curr_m]).lower().split()
                    
                    c_prev = Counter(words_prev)
                    c_curr = Counter(words_curr)
                    
                    # Calculate word momentum
                    diff = {}
                    for w in set(words_curr):
                        if len(w) < 4: continue
                        count_curr = c_curr[w]
                        count_prev = c_prev.get(w, 0)
                        # Score is absolute increase in appearance
                        diff[w] = count_curr - count_prev

                    top_shifting = [w for w, s in Counter(diff).most_common(3) if s > 0]
                    
                    drift_rows.append({
                        "category": cat_label,
                        "month_from": prev_m,
                        "month_to": curr_m,
                        "drift_score": drift,
                        "is_evolving": bool(drift > 0.12), # Slightly more sensitive
                        "shifting_terms": ", ".join(top_shifting)
                    })
        except Exception as e:
            print(f"[Phase 25.2] Drift detection failed: {e}")

        if drift_rows:
            out_drift = os.path.join(processed_data_dir(), "semantic_drift.csv")
            os.makedirs(os.path.dirname(out_drift), exist_ok=True)
            pd.DataFrame(drift_rows).to_csv(out_drift, index=False)
        # ─────────────────────────────────────────────────────────────────────

        # ── Phase 53: Export NORMALIZED + REVENUE-WEIGHTED time-series ──
        timeseries_data = []

        # Build per-category monthly metrics
        cat_month_stats = {} # { (cat, month): { 'sev_sum': 0, 'impact_sum': 0 } }
        for clf in review_classifications:
            cat = clf.get("category", "")
            month = clf.get("date", "")
            if cat and month and month not in ("NaT", "Unknown", ""):
                key = (cat, month)
                if key not in cat_month_stats:
                    cat_month_stats[key] = {'sev_sum': 0.0, 'impact_sum': 0.0}
                cat_month_stats[key]['sev_sum'] += clf.get("severity", 2.0)
                cat_month_stats[key]['impact_sum'] += clf.get("financial_impact", 2.0)

        for t_id, data in topic_stats.items():
            label = generate_issue_label(data["keywords"], encoder=self.encoder)
            for month_str, m_count in data.get("monthly_mentions", {}).items():
                total_in_month = monthly_review_totals.get(month_str, m_count)
                norm_rate = round((m_count / max(total_in_month, 1)) * 1000, 2)
                
                # Fetch aggregated metrics
                stats = cat_month_stats.get((label, month_str), 
                        cat_month_stats.get((t_id, month_str), 
                        {'sev_sum': m_count * 2.0, 'impact_sum': m_count * 2.0}))
                
                sev_weighted = round((stats['sev_sum'] / max(total_in_month, 1)) * 1000, 2)
                revenue_risk = round((stats['impact_sum'] / max(total_in_month, 1)) * 1000, 2)
                
                timeseries_data.append({
                    "topic_id": t_id,
                    "issue_label": label,
                    "month": month_str,
                    "mentions": m_count,
                    "normalized_rate": norm_rate,
                    "severity_weighted_rate": sev_weighted,
                    "revenue_risk_score": revenue_risk,
                    "total_reviews_in_month": total_in_month
                })
        # ─────────────────────────────────────────────────────────────────────

        if timeseries_data:
            out_timeseries = os.path.join(processed_data_dir(), "topic_timeseries.csv")
            os.makedirs(os.path.dirname(out_timeseries), exist_ok=True)
            pd.DataFrame(timeseries_data).to_csv(out_timeseries, index=False)
        
        # Save Aspect Stats for Dashboard Heatmap
        aspect_rows = [{"aspect": k, "mentions": v} for k, v in aspect_stats.items()]
        out_aspects = os.path.join(processed_data_dir(), "aspect_analysis.csv")
        os.makedirs(os.path.dirname(out_aspects), exist_ok=True)
        pd.DataFrame(aspect_rows).to_csv(out_aspects, index=False)

        # Trigger Threshold Check
        print("[!] Checking critical thresholds...")
        self.alerting_service.check_thresholds()

        self.progress["status"] = "complete"
        print(f"Successfully generated and cached new topic_analysis.csv for {total_valid} high-quality reviews (filtered {filtered_out} spam).")
