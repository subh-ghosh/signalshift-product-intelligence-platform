import heapq
import joblib
import os
import pickle
import time

import numpy as np
import pandas as pd
from sentence_transformers import SentenceTransformer

from ml.core.issue_labeler import _build_taxonomy_embeddings
import ml.core.issue_labeler as issue_labeler_module
from ml.core.spam_filter import is_valid_review
from ml.core.text_cleaner import clean_text


CONFIDENCE_THRESHOLD = 0.30
TOP_EVIDENCE_REVIEWS = 15
TESTING_PROCESSED_DIR = os.path.join("data", "testing", "processed")

SEVERITY_5_WORDS = {"scam", "fraud", "lawsuit", "legal", "stolen", "robbed", "cheat", "criminal", "hack", "hacked"}
SEVERITY_4_WORDS = {"terrible", "horrible", "worst", "useless", "disgusting", "outraged", "furious", "demand", "refund", "charged", "unauthorized"}
SEVERITY_3_WORDS = {"broken", "crash", "fail", "error", "bug", "fix", "annoying", "hate", "bad", "poor", "slow", "stuck"}


class MLService:
    def __init__(self):
        print("Loading ML models...")

        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        model_dir = os.path.join(base_dir, "models")

        self.sentiment_model = joblib.load(os.path.join(model_dir, "sentiment_model.joblib"))
        self.vectorizer = joblib.load(os.path.join(model_dir, "tfidf_vectorizer.joblib"))
        self.encoder = SentenceTransformer("all-MiniLM-L6-v2", device="cpu")

        self.taxonomy_labels, self.taxonomy_matrix = self._load_taxonomy_embeddings(model_dir)

        self.progress = {
            "processed": 0,
            "total": 0,
            "status": "idle",
            "eta_seconds": 0,
            "start_time": None,
        }
        self.should_stop = False

        print("ML models loaded successfully.")

    def _load_taxonomy_embeddings(self, model_dir):
        embeddings_path = os.path.join(model_dir, "topic_embeddings.pkl")
        if os.path.exists(embeddings_path):
            with open(embeddings_path, "rb") as handle:
                data = pickle.load(handle)
            labels = data.get("topics", [])
            embeddings = np.array(data.get("embeddings", []))
            if labels and embeddings.size:
                return labels, embeddings

        issue_labeler_module._encoder = self.encoder
        _build_taxonomy_embeddings()
        return issue_labeler_module._taxonomy_labels, issue_labeler_module._taxonomy_embeddings

    def _update_eta(self, processed, total, start_time):
        if processed == 0 or start_time is None:
            return 0

        elapsed = time.time() - start_time
        speed = processed / elapsed
        remaining = total - processed
        if speed > 0:
            return round(remaining / speed)
        return 0

    def stop_analysis(self):
        self.should_stop = True
        self.progress["status"] = "stopping"

    def predict_sentiment(self, review):
        cleaned = clean_text(review)
        vector = self.vectorizer.transform([cleaned])
        return self.sentiment_model.predict(vector)[0]

    def predict_sentiment_batch(self, reviews):
        self.should_stop = False
        total = len(reviews)
        self.progress["total"] = total
        self.progress["processed"] = 0
        self.progress["status"] = "sentiment"
        self.progress["start_time"] = time.time()

        sentiments = []
        batch_size = 512

        for i in range(0, total, batch_size):
            if self.should_stop:
                print(f"Sentiment analysis stopped at {i} reviews.")
                break

            batch = reviews[i:i + batch_size]
            try:
                cleaned_reviews = [clean_text(review) for review in batch]
                vectors = self.vectorizer.transform(cleaned_reviews)
                batch_sentiments = self.sentiment_model.predict(vectors)
                sentiments.extend(batch_sentiments.tolist())
            except Exception as exc:
                print(f"Error processing sentiment batch {i}: {exc}")
                sentiments.extend(["negative"] * len(batch))

            self.progress["processed"] = min(i + batch_size, total)
            self.progress["eta_seconds"] = self._update_eta(
                self.progress["processed"],
                total,
                self.progress["start_time"],
            )

        return sentiments

    def classify_issue(self, review):
        cleaned = clean_text(review)
        if not cleaned:
            return {"label": "General App Feedback", "confidence": 0.0}

        review_embedding = self.encoder.encode([cleaned], normalize_embeddings=True)[0]
        similarities = self.taxonomy_matrix.dot(review_embedding)
        best_index = int(np.argmax(similarities))
        confidence = float(similarities[best_index])

        label = (
            self.taxonomy_labels[best_index]
            if confidence >= CONFIDENCE_THRESHOLD
            else "General App Feedback"
        )
        return {"label": label, "confidence": round(confidence, 4)}

    def compute_severity(self, text):
        lowered = text.lower()
        words = set(lowered.split())

        score = 2.0
        if words & SEVERITY_5_WORDS:
            score += 2.5
        elif words & SEVERITY_4_WORDS:
            score += 1.5
        elif words & SEVERITY_3_WORDS:
            score += 0.5

        caps_ratio = sum(1 for char in text if char.isupper()) / max(len(text), 1)
        if caps_ratio > 0.3:
            score += 0.5

        score += min(text.count("!") * 0.2, 0.6)
        return min(round(score, 2), 5.0)

    def analyze_review(self, review):
        sentiment = self.predict_sentiment(review)
        issue = self.classify_issue(review) if sentiment == "negative" else {"label": None, "confidence": 0.0}

        return {
            "review": review,
            "sentiment": sentiment,
            "issue_label": issue["label"],
            "confidence": issue["confidence"],
            "severity": self.compute_severity(review) if sentiment == "negative" else None,
        }

    def detect_issues(self, reviews):
        issue_counter = {}

        for review in reviews:
            sentiment = self.predict_sentiment(review)
            if sentiment != "negative":
                continue

            issue = self.classify_issue(review)["label"]
            issue_counter[issue] = issue_counter.get(issue, 0) + 1

        sorted_issues = sorted(issue_counter.items(), key=lambda item: item[1], reverse=True)
        return [{"issue": issue, "mentions": count} for issue, count in sorted_issues[:10]]

    def generate_topic_analysis_cache(self, df):
        self.should_stop = False
        self.progress["status"] = "analyzing"

        if "sentiment" in df.columns:
            negative_df = df[df["sentiment"] == "negative"].copy()
        else:
            negative_df = df.copy()

        total_negative = len(negative_df)
        self.progress["total"] = total_negative
        self.progress["processed"] = 0
        self.progress["start_time"] = time.time()

        os.makedirs(TESTING_PROCESSED_DIR, exist_ok=True)

        if total_negative == 0:
            self._write_empty_outputs()
            self.progress["status"] = "idle"
            return

        mask = negative_df["content"].astype(str).apply(is_valid_review)
        valid_df = negative_df[mask].copy().reset_index(drop=True)

        reviews = valid_df["content"].astype(str).tolist()
        dates = self._extract_months(valid_df)
        versions = valid_df["appVersion"].astype(str).tolist() if "appVersion" in valid_df.columns else ["N/A"] * len(valid_df)
        upvotes = valid_df["thumbsUpCount"].fillna(0).astype(int).tolist() if "thumbsUpCount" in valid_df.columns else [0] * len(valid_df)

        total_valid = len(reviews)
        if total_valid == 0:
            self._write_empty_outputs()
            self.progress["status"] = "idle"
            return

        self.progress["total"] = total_valid

        topic_stats = {}
        review_classifications = []
        monthly_review_totals = {}

        batch_size = 64
        for start in range(0, total_valid, batch_size):
            if self.should_stop:
                print(f"Topic analysis stopped at {start} reviews.")
                break

            batch_reviews = reviews[start:start + batch_size]
            batch_dates = dates[start:start + batch_size]
            batch_versions = versions[start:start + batch_size]
            batch_upvotes = upvotes[start:start + batch_size]

            cleaned_reviews = [clean_text(review) for review in batch_reviews]
            review_embeddings = self.encoder.encode(
                cleaned_reviews,
                batch_size=64,
                normalize_embeddings=True,
                show_progress_bar=False,
            )

            similarity_matrix = np.dot(review_embeddings, self.taxonomy_matrix.T)
            best_category_ids = np.argmax(similarity_matrix, axis=1)
            best_scores = similarity_matrix[np.arange(len(batch_reviews)), best_category_ids]

            for index, review_text in enumerate(batch_reviews):
                confidence = float(best_scores[index])
                label = (
                    self.taxonomy_labels[best_category_ids[index]]
                    if confidence >= CONFIDENCE_THRESHOLD
                    else "General App Feedback"
                )
                severity = self.compute_severity(review_text)
                month = batch_dates[index]

                if label not in topic_stats:
                    topic_stats[label] = {
                        "mentions": 0,
                        "severity_total": 0.0,
                        "severity_count": 0,
                        "monthly_mentions": {},
                        "sample_reviews_heap": [],
                    }

                topic_stats[label]["mentions"] += 1
                topic_stats[label]["severity_total"] += severity
                topic_stats[label]["severity_count"] += 1

                if month not in ("NaT", "Unknown"):
                    topic_stats[label]["monthly_mentions"][month] = (
                        topic_stats[label]["monthly_mentions"].get(month, 0) + 1
                    )
                    monthly_review_totals[month] = monthly_review_totals.get(month, 0) + 1

                if len(review_text) > 40:
                    heap = topic_stats[label]["sample_reviews_heap"]
                    candidate = (confidence, review_text)
                    if len(heap) < 20:
                        heapq.heappush(heap, candidate)
                    elif confidence > heap[0][0]:
                        heapq.heapreplace(heap, candidate)

                review_classifications.append({
                    "text": review_text,
                    "category": label,
                    "date": "" if month == "NaT" else month,
                    "severity": severity,
                    "confidence": round(confidence, 4),
                    "app_version": batch_versions[index],
                    "upvotes": batch_upvotes[index],
                })

            self.progress["processed"] = min(total_valid, start + batch_size)
            self.progress["status"] = f"Analyzing topics... {self.progress['processed']}/{total_valid}"

        topic_rows = []

        for label, stats in sorted(topic_stats.items(), key=lambda item: item[1]["mentions"], reverse=True):
            avg_severity = round(stats["severity_total"] / max(stats["severity_count"], 1), 2)
            sample_reviews = self._deduplicate_reviews(stats["sample_reviews_heap"])

            topic_rows.append({
                "topic_id": label,
                "keywords": label,
                "label": label,
                "mentions": stats["mentions"],
                "avg_severity": avg_severity,
                "sample_reviews": sample_reviews,
            })

        pd.DataFrame(topic_rows).to_csv(os.path.join(TESTING_PROCESSED_DIR, "topic_analysis.csv"), index=False)
        pd.DataFrame(review_classifications).to_csv(os.path.join(TESTING_PROCESSED_DIR, "review_classifications.csv"), index=False)

        self.progress["status"] = "complete"
        print(f"Successfully generated topic analysis for {len(review_classifications)} negative reviews.")

    def _extract_months(self, df):
        date_col = "at" if "at" in df.columns else "date" if "date" in df.columns else None
        if not date_col:
            return ["Unknown"] * len(df)
        return pd.to_datetime(df[date_col], errors="coerce").dt.to_period("M").astype(str).tolist()

    def _deduplicate_reviews(self, sample_heap):
        candidates = [review for _, review in sorted(sample_heap, key=lambda item: item[0], reverse=True)]
        if not candidates:
            return []

        candidate_embeddings = self.encoder.encode(candidates, normalize_embeddings=True, show_progress_bar=False)
        kept_indices = []
        final_reviews = []

        for index, review_text in enumerate(candidates):
            if len(final_reviews) >= TOP_EVIDENCE_REVIEWS:
                break

            if kept_indices:
                max_similarity = max(
                    float(np.dot(candidate_embeddings[index], candidate_embeddings[kept_index]))
                    for kept_index in kept_indices
                )
                if max_similarity >= 0.85:
                    continue

            kept_indices.append(index)
            final_reviews.append(review_text)

        return final_reviews

    def _write_empty_outputs(self):
        pd.DataFrame(columns=["topic_id", "keywords", "label", "mentions", "avg_severity", "sample_reviews"]).to_csv(
            os.path.join(TESTING_PROCESSED_DIR, "topic_analysis.csv"),
            index=False,
        )
        pd.DataFrame(columns=["text", "category", "date", "severity", "confidence", "app_version", "upvotes"]).to_csv(
            os.path.join(TESTING_PROCESSED_DIR, "review_classifications.csv"),
            index=False,
        )
