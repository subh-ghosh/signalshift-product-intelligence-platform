import joblib
import pickle
import numpy as np

from sentence_transformers import SentenceTransformer

from app.ml.text_cleaner import clean_text


class MLService:

    def __init__(self):

        print("Loading ML models...")

        # sentiment model
        self.sentiment_model = joblib.load("models/sentiment_model.joblib")

        # tfidf vectorizer
        self.vectorizer = joblib.load("models/tfidf_vectorizer.joblib")

        print("Loading embedding model...")

        self.embedding_model = SentenceTransformer("all-MiniLM-L6-v2")

        print("Loading topic embeddings...")

        with open("models/topic_embeddings.pkl", "rb") as f:
            data = pickle.load(f)

        self.topics = data["topics"]
        self.topic_embeddings = data["embeddings"]

        print("ML models loaded successfully.")

    # -------------------------
    # Sentiment
    # -------------------------

    def predict_sentiment(self, review):

        cleaned = clean_text(review)

        vector = self.vectorizer.transform([cleaned])

        sentiment = self.sentiment_model.predict(vector)[0]

        return sentiment

    # -------------------------
    # Topic detection
    # -------------------------

    def predict_topic(self, review):

        cleaned = clean_text(review)
        review_embedding = self.embedding_model.encode([cleaned])[0]

        similarities = np.dot(self.topic_embeddings, review_embedding) / (
            np.linalg.norm(self.topic_embeddings, axis=1) * np.linalg.norm(review_embedding)
        )

        best_index = int(np.argmax(similarities))

        topic = self.topics[best_index]

        return {
            "topic_id": best_index,
            "keywords": topic
        }

    # -------------------------
    # Full analysis
    # -------------------------

    def analyze_review(self, review):

        sentiment = self.predict_sentiment(review)

        topic_info = self.predict_topic(review)

        return {
            "review": review,
            "sentiment": sentiment,
            "topic_id": topic_info["topic_id"],
            "topic_keywords": topic_info["keywords"]
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