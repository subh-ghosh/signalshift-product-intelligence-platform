"""Step 02: Fit and save the TF-IDF vectorizer used by the sentiment classifier."""

from __future__ import annotations

from pipeline_common import load_cleaned_dataset, fit_tfidf_vectorizer, save_vectorizer


if __name__ == "__main__":
    df = load_cleaned_dataset()
    print("Loaded cleaned dataset:", df.shape)

    vectorizer, X = fit_tfidf_vectorizer(df)
    print("TF-IDF matrix:", X.shape)

    path = save_vectorizer(vectorizer)
    print("Saved vectorizer:", path)
