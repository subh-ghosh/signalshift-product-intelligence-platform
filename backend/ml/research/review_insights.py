import pandas as pd
import joblib
from collections import Counter


print("Loading dataset...")

df = pd.read_csv("../../data/processed/cleaned_reviews.csv")

df = df.dropna(subset=["cleaned_content"])
df["cleaned_content"] = df["cleaned_content"].astype(str)

print("Total reviews:", len(df))


# -----------------------------
# Load Models
# -----------------------------

print("Loading models...")

sentiment_model = joblib.load("../../models/sentiment_model.joblib")
vectorizer = joblib.load("../../models/tfidf_vectorizer.joblib")
topic_model = joblib.load("../../models/topic_model.joblib")


# -----------------------------
# Sentiment Prediction
# -----------------------------

print("Predicting sentiment...")

X = vectorizer.transform(df["cleaned_content"])
df["sentiment"] = sentiment_model.predict(X)


# -----------------------------
# Topic Prediction
# -----------------------------

print("Predicting topics...")

topics, probs = topic_model.transform(df["cleaned_content"].tolist())

df["topic"] = topics


# -----------------------------
# Sentiment Distribution
# -----------------------------

print("\nSentiment Distribution")

sentiment_counts = df["sentiment"].value_counts()

print(sentiment_counts)


# -----------------------------
# Topic Frequency
# -----------------------------

print("\nTop Topics")

topic_counts = df["topic"].value_counts().head(10)

print(topic_counts)


# -----------------------------
# Topic Keywords
# -----------------------------

print("\nTopic Keywords")

topic_info = []

for topic_id in topic_counts.index:

    if topic_id == -1:
        continue

    words = topic_model.get_topic(topic_id)

    keywords = [word for word, _ in words[:5]]

    topic_info.append({
        "topic_id": topic_id,
        "keywords": ", ".join(keywords),
        "mentions": int(topic_counts[topic_id])
    })


topic_df = pd.DataFrame(topic_info)

print(topic_df)


# -----------------------------
# Topic Sentiment Analysis
# -----------------------------

print("\nTopic Sentiment Analysis")

topic_sentiment = df.groupby(["topic", "sentiment"]).size().unstack(fill_value=0)

print(topic_sentiment.head(10))


# -----------------------------
# Save Insights
# -----------------------------

print("\nSaving insights...")

topic_df.to_csv("../../data/processed/topic_insights.csv", index=False)
topic_sentiment.to_csv("../../data/processed/topic_sentiment.csv")

print("Insights saved successfully.")