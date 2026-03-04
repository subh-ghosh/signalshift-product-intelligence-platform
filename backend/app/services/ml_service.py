import joblib
from ..ml.text_cleaner import clean_text


class MLService:

    def __init__(self):

        print("Loading ML models...")

        self.sentiment_model = joblib.load("models/sentiment_model.joblib")
        self.vectorizer = joblib.load("models/tfidf_vectorizer.joblib")
        self.topic_model = joblib.load("models/topic_model.joblib")

        print("ML models loaded successfully.")

    # -----------------------------
    # Sentiment Prediction
    # -----------------------------
    def predict_sentiment(self, review: str):

        cleaned = clean_text(review)
        vector = self.vectorizer.transform([cleaned])
        sentiment = self.sentiment_model.predict(vector)[0]

        return sentiment

    # -----------------------------
    # Topic Prediction
    # -----------------------------
    def predict_topic(self, review: str):

        cleaned = clean_text(review)
        topics, probs = self.topic_model.transform([cleaned])
        topic_id = int(topics[0])

        if topic_id == -1:
            return {
                "topic_id": -1,
                "keywords": ["general"]
            }

        topic_words = self.topic_model.get_topic(topic_id)
        keywords = [word for word, _ in topic_words[:5]]

        return {
            "topic_id": topic_id,
            "keywords": keywords
        }

    # -----------------------------
    # Full Analysis
    # -----------------------------
    def analyze_review(self, review: str):

        sentiment = self.predict_sentiment(review)
        topic_info = self.predict_topic(review)

        return {
            "review": review,
            "sentiment": sentiment,
            "topic_id": topic_info["topic_id"],
            "topic_keywords": topic_info["keywords"]
        }

    # -----------------------------
    # Issue Detection
    # -----------------------------
    def detect_issues(self, reviews):

        issue_counter = {}

        for review in reviews:

            result = self.analyze_review(review)
            topic_keywords = result["topic_keywords"]

            if topic_keywords:

                main_issue = topic_keywords[0]

                if main_issue not in issue_counter:
                    issue_counter[main_issue] = 0

                issue_counter[main_issue] += 1

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