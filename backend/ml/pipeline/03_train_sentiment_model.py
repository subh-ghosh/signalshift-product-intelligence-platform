import os

from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report, accuracy_score

from pipeline_common import (
    load_cleaned_dataset,
    load_vectorizer,
    save_sentiment_model,
)


def rating_to_sentiment(score):
    if score <= 2:
        return "negative"
    return "positive"


def build_sentiment_labels(df):
    labeled_df = df.copy()
    labeled_df["sentiment"] = labeled_df["score"].apply(rating_to_sentiment)
    return labeled_df


def train_sentiment_pipeline(
    df,
    *,
    vectorizer,
    test_size=0.2,
    random_state=42,
    model_kwargs=None,
):
    labeled_df = build_sentiment_labels(df)

    print("\nSentiment distribution:")
    print(labeled_df["sentiment"].value_counts())

    if vectorizer is None:
        raise ValueError("vectorizer is required. Load it via load_vectorizer() from step 02 artifacts.")

    print("\nTransforming reviews using existing TF-IDF vectorizer (from step 02)...")
    X = vectorizer.transform(labeled_df["cleaned_content"])
    y = labeled_df["sentiment"]

    if test_size and test_size > 0:
        X_train, X_test, y_train, y_test = train_test_split(
            X,
            y,
            test_size=test_size,
            random_state=random_state,
        )

        print("\nTraining samples:", X_train.shape[0])
        print("Test samples:", X_test.shape[0])
    else:
        X_train, y_train = X, y
        X_test = y_test = None
        print("\nTraining samples:", X_train.shape[0])
        print("Test samples: 0")

    print("\nTraining Logistic Regression model...")
    model = LogisticRegression(max_iter=1000, **(model_kwargs or {}))
    model.fit(X_train, y_train)

    metrics = None
    if X_test is not None:
        y_pred = model.predict(X_test)
        accuracy = accuracy_score(y_test, y_pred)
        report = classification_report(y_test, y_pred)

        print("\nAccuracy:", accuracy)
        print("\nClassification Report:")
        print(report)

        metrics = {"accuracy": accuracy, "classification_report": report}

    return vectorizer, model, metrics


def save_sentiment_artifacts(model):
    save_sentiment_model(model)


if __name__ == "__main__":
    print("Training mode: using curated training data only. Uploaded CSV files are inference-only.")
    dataset = load_cleaned_dataset()
    vectorizer = load_vectorizer()
    _, model, _ = train_sentiment_pipeline(dataset, vectorizer=vectorizer)
    save_sentiment_artifacts(model)
