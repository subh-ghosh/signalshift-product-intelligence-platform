from pipeline_common import (
    load_cleaned_dataset,
    fit_tfidf_vectorizer,
    save_vectorizer,
)


if __name__ == "__main__":
    dataset = load_cleaned_dataset()
    vectorizer, _ = fit_tfidf_vectorizer(dataset)
    save_vectorizer(vectorizer)
