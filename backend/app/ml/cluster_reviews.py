import pandas as pd
from sentence_transformers import SentenceTransformer
from bertopic import BERTopic
import joblib


# -----------------------------
# Load cleaned dataset and filter
# -----------------------------
print("Loading cleaned dataset...")

df = pd.read_csv("data/processed/cleaned_reviews.csv")

df = df.dropna(subset=["cleaned_content"])
df["cleaned_content"] = df["cleaned_content"].astype(str)

print(f"Total reviews in dataset: {len(df)}")

print("Loading sentiment models to filter for negative reviews...")
sentiment_model = joblib.load("models/sentiment_model.joblib")
vectorizer = joblib.load("models/tfidf_vectorizer.joblib")

print("Filtering for negative reviews...")
X = vectorizer.transform(df["cleaned_content"])
df["sentiment"] = sentiment_model.predict(X)

negative_df = df[df["sentiment"] == "negative"]
reviews = negative_df["cleaned_content"].tolist()

print(f"Total NEGATIVE reviews for training: {len(reviews)}")


# -----------------------------
# Load embedding model
# -----------------------------
print("Loading sentence transformer model...")

embedding_model = SentenceTransformer("all-MiniLM-L6-v2")


# -----------------------------
# Create BERTopic model
# -----------------------------
print("Initializing BERTopic...")

topic_model = BERTopic(
    embedding_model=embedding_model,
    verbose=True
)


# -----------------------------
# Fit topic model
# -----------------------------
print("Training topic model...")

topics, probs = topic_model.fit_transform(reviews)


# -----------------------------
# Show discovered topics
# -----------------------------
print("\nTop Topics Discovered:\n")

topic_info = topic_model.get_topic_info()

print(topic_info.head(15))


# -----------------------------
# Save topic model
# -----------------------------
print("\nSaving topic model...")

joblib.dump(topic_model, "models/topic_model.joblib")

print("Topic model saved successfully.")