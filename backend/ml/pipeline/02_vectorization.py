import os
import joblib
import pandas as pd

from sklearn.feature_extraction.text import TfidfVectorizer


BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA_PATH = os.path.join(BASE_DIR, "data", "training", "processed", "cleaned_all_combined.csv")
MODEL_DIR = os.path.join(BASE_DIR, "models")


def ensure_training_dataset(path):
    normalized = os.path.abspath(path).lower()
    blocked_names = {
        "uploaded_reviews.csv",
        "review_classifications.csv",
        "topic_analysis.csv",
    }
    if os.path.basename(normalized) in blocked_names:
        raise ValueError(
            "Inference/output CSVs cannot be used for training. "
            "Use the curated training dataset such as cleaned_all_combined.csv."
        )


def load_cleaned_dataset(path=DATA_PATH):
    ensure_training_dataset(path)
    df = pd.read_csv(path)
    print("Dataset loaded:", df.shape)

    df = df.dropna(subset=["cleaned_content"]).copy()
    df["cleaned_content"] = df["cleaned_content"].astype(str)

    print("Dataset after validation:", df.shape)
    return df


def build_tfidf_vectorizer(*, max_features=10000, ngram_range=(1, 2)):
    return TfidfVectorizer(max_features=max_features, ngram_range=ngram_range)


def vectorize_reviews(df, *, max_features=10000, ngram_range=(1, 2)):
    print("\nCreating TF-IDF features...")
    vectorizer = build_tfidf_vectorizer(
        max_features=max_features,
        ngram_range=ngram_range,
    )
    X = vectorizer.fit_transform(df["cleaned_content"])
    print("TF-IDF matrix shape:", X.shape)
    return vectorizer, X


def save_vectorizer(vectorizer, model_dir=MODEL_DIR):
    print("\nSaving vectorizer...")
    joblib.dump(vectorizer, os.path.join(model_dir, "tfidf_vectorizer.joblib"))
    print("Vectorizer saved successfully.")


if __name__ == "__main__":
    dataset = load_cleaned_dataset()
    vectorizer, _ = vectorize_reviews(dataset)
    save_vectorizer(vectorizer)
