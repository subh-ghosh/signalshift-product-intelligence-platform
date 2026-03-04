import pandas as pd
import joblib


# -----------------------------
# Load cleaned dataset
# -----------------------------
print("Loading cleaned dataset...")

df = pd.read_csv("../../data/processed/cleaned_reviews.csv")

df = df.dropna(subset=["cleaned_content"])
df["cleaned_content"] = df["cleaned_content"].astype(str)

reviews = df["cleaned_content"].tolist()

print("Total reviews:", len(reviews))


# -----------------------------
# Load topic model
# -----------------------------
print("Loading topic model...")

topic_model = joblib.load("../../models/topic_model.joblib")


# -----------------------------
# Assign topics to reviews
# -----------------------------
print("Assigning topics to reviews...")

topics, probs = topic_model.transform(reviews)

df["topic"] = topics


# -----------------------------
# Load sentiment model
# -----------------------------
print("Loading sentiment model...")

sentiment_model = joblib.load("../../models/sentiment_model.joblib")
vectorizer = joblib.load("../../models/tfidf_vectorizer.joblib")


# -----------------------------
# Predict sentiment
# -----------------------------
print("Predicting sentiment...")

X = vectorizer.transform(df["cleaned_content"])

sentiments = sentiment_model.predict(X)

df["sentiment"] = sentiments


# -----------------------------
# Compute topic statistics
# -----------------------------
print("Computing topic statistics...")

topic_stats = []

topic_counts = df["topic"].value_counts()


for topic_id, count in topic_counts.items():

    # skip noise cluster
    if topic_id == -1:
        continue

    topic_reviews = df[df["topic"] == topic_id]

    negative = (topic_reviews["sentiment"] == "negative").sum()
    positive = (topic_reviews["sentiment"] == "positive").sum()

    neg_ratio = negative / len(topic_reviews)

    # Impact score
    impact_score = len(topic_reviews) * neg_ratio

    # Topic keywords
    topic_words = topic_model.get_topic(topic_id)

    keywords = [word for word, _ in topic_words[:5]]

    # Representative complaints
    sample_reviews = topic_reviews["content"].head(3).tolist()

    topic_stats.append({
        "topic_id": topic_id,
        "mentions": len(topic_reviews),
        "negative_reviews": negative,
        "positive_reviews": positive,
        "negative_ratio": round(neg_ratio, 2),
        "impact_score": round(impact_score, 2),
        "keywords": ", ".join(keywords),
        "sample_reviews": sample_reviews
    })


# -----------------------------
# Convert to dataframe
# -----------------------------
topic_df = pd.DataFrame(topic_stats)

topic_df = topic_df.sort_values(
    by="impact_score",
    ascending=False
)


# -----------------------------
# Show top issues
# -----------------------------
print("\nTop Product Issues:\n")

print(topic_df.head(10))


# -----------------------------
# Save results
# -----------------------------
topic_df.to_csv(
    "../../data/processed/topic_analysis.csv",
    index=False
)

print("\nTopic analysis saved successfully.")