import os

import joblib
import pandas as pd
from sklearn.decomposition import NMF
from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS, TfidfVectorizer


BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TRAINING_CLEAN_CSV = os.path.join(
    BASE_DIR, "data", "training", "processed", "cleaned_all_combined.csv"
)
MODEL_DIR = os.path.join(BASE_DIR, "models")


if __name__ == "__main__":
    print("\n[03] Training production topic model (TF-IDF + NMF)...")

    if not os.path.exists(TRAINING_CLEAN_CSV):
        raise FileNotFoundError(
            f"Cleaned training dataset not found: {TRAINING_CLEAN_CSV}. "
            "Run 01_preprocessing.py first."
        )

    df = pd.read_csv(TRAINING_CLEAN_CSV)
    if "cleaned_content" not in df.columns:
        raise ValueError("Expected column 'cleaned_content' in cleaned training CSV.")
    if "score" not in df.columns:
        raise ValueError("Expected column 'score' in cleaned training CSV.")

    df = df.dropna(subset=["cleaned_content", "score"]).copy()

    # NMF topics are trained only on negative reviews to focus on issues.
    negative_text = df[df["score"] <= 2]["cleaned_content"].astype(str).str.lower()
    if negative_text.empty:
        raise ValueError(
            "No negative reviews found (score <= 2). Cannot train NMF topic model."
        )

    custom_stop_words = list(
        ENGLISH_STOP_WORDS.union(
            {
                "app",
                "netflix",
                "good",
                "bad",
                "great",
                "excellent",
                "nice",
                "ok",
                "awesome",
                "hai",
                "hua",
                "hi",
                "bhai",
                "yaar",
                "kya",
                "ko",
                "ki",
                "he",
                "it",
                "very",
                "is",
                "application",
                "working",
                "work",
                "use",
                "using",
                "like",
                "love",
                "really",
                "amazing",
                "super",
                "useful",
                "best",
                "worst",
                "better",
                "quality",
                "time",
                "just",
                "don",
                "t",
                "s",
                "can",
                "ve",
                "re",
                "m",
                "want",
                "let",
                "the",
                "an",
                "this",
                "phone",
                "mobile",
                "update",
            }
        )
    )

    print("Vectorizing negative reviews for NMF...")
    nmf_vectorizer = TfidfVectorizer(
        max_df=0.95,
        min_df=2,
        stop_words=custom_stop_words,
    )
    X_nmf = nmf_vectorizer.fit_transform(negative_text)
    print("NMF TF-IDF matrix shape:", X_nmf.shape)

    print("Fitting NMF...")
    nmf = NMF(n_components=30, random_state=42, init="nndsvd")
    nmf.fit(X_nmf)

    os.makedirs(MODEL_DIR, exist_ok=True)

    nmf_model_path = os.path.join(MODEL_DIR, "nmf_model.joblib")
    nmf_vectorizer_path = os.path.join(MODEL_DIR, "nmf_vectorizer.joblib")

    joblib.dump(nmf, nmf_model_path)
    joblib.dump(nmf_vectorizer, nmf_vectorizer_path)

    print("\nSaved NMF artifacts:")
    print("-", nmf_model_path)
    print("-", nmf_vectorizer_path)
