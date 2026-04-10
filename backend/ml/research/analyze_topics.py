import pandas as pd
import joblib


# -----------------------------
# Load cleaned dataset
# -----------------------------
print("Loading cleaned dataset...")

df = pd.read_csv("data/processed/cleaned_reviews.csv")

df = df.dropna(subset=["cleaned_content"])
df["cleaned_content"] = df["cleaned_content"].astype(str)

reviews = df["cleaned_content"].tolist()

print("Total reviews:", len(reviews))


# -----------------------------
# Load topic model
# -----------------------------
print("Loading topic model...")

topic_model = joblib.load("models/topic_model.joblib")


# -----------------------------
# Predict sentiment and filter
# -----------------------------
print("Getting sentiments to filter for negative reviews...")
sentiment_model = joblib.load("models/sentiment_model.joblib")
vectorizer = joblib.load("models/tfidf_vectorizer.joblib")

X = vectorizer.transform(df["cleaned_content"])
df["sentiment"] = sentiment_model.predict(X)

# KEEP ONLY NEGATIVE REVIEWS
negative_df = df[df["sentiment"] == "negative"].copy()
negative_reviews = negative_df["cleaned_content"].tolist()
print(f"Total NEGATIVE reviews for topic analysis: {len(negative_reviews)}")


# -----------------------------
# Assign topics to negative reviews
# -----------------------------
print("Assigning topics to negative reviews...")

topics, probs = topic_model.transform(negative_reviews)
negative_df["topic"] = topics

print("Computing topic statistics...")

topic_stats = []

topic_counts = negative_df["topic"].value_counts()


for topic_id, count in topic_counts.items():

    # skip noise cluster
    if topic_id == -1:
        continue

    topic_reviews = negative_df[negative_df["topic"] == topic_id]

    negative = len(topic_reviews)
    positive = 0
    neg_ratio = 1.0
    impact_score = negative

    # Topic keywords
    topic_words = topic_model.get_topic(topic_id)

    keywords = [word for word, _ in topic_words[:5]]

    # Representative complaints
    sample_reviews = topic_reviews["content"].head(3).tolist()

    topic_stats.append({
        "topic_id": topic_id,
        "mentions": negative,
        "negative_reviews": negative,
        "positive_reviews": positive,
        "negative_ratio": neg_ratio,
        "impact_score": impact_score,
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
    "data/processed/topic_analysis.csv",
    index=False
)

print("\nTopic analysis saved successfully.")