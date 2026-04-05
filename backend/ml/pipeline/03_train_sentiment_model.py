import os
import joblib

from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report, accuracy_score
import importlib.util


BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA_PATH = os.path.join(BASE_DIR, "data", "training", "processed", "cleaned_all_combined.csv")
MODEL_DIR = os.path.join(BASE_DIR, "models")
STEP_02_PATH = os.path.join(os.path.dirname(__file__), "02_vectorization.py")

spec = importlib.util.spec_from_file_location("step_02_vectorization", STEP_02_PATH)
step_02 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(step_02)


def rating_to_sentiment(score):
    if score <= 2:
        return "negative"
    return "positive"


def load_cleaned_dataset(path=DATA_PATH):
    return step_02.load_cleaned_dataset(path)


def build_sentiment_labels(df):
    labeled_df = df.copy()
    labeled_df["sentiment"] = labeled_df["score"].apply(rating_to_sentiment)
    return labeled_df


def train_sentiment_pipeline(
    df,
    *,
    max_features=10000,
    ngram_range=(1, 2),
    test_size=0.2,
    random_state=42,
    model_kwargs=None,
):
    labeled_df = build_sentiment_labels(df)

    print("\nSentiment distribution:")
    print(labeled_df["sentiment"].value_counts())

    vectorizer, X = step_02.vectorize_reviews(
        labeled_df,
        max_features=max_features,
        ngram_range=ngram_range,
    )
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


def save_sentiment_artifacts(vectorizer, model, model_dir=MODEL_DIR):
    joblib.dump(model, os.path.join(model_dir, "sentiment_model.joblib"))
    step_02.save_vectorizer(vectorizer, model_dir)
    print("Sentiment model saved successfully.")


if __name__ == "__main__":
    print("Training mode: using curated training data only. Uploaded CSV files are inference-only.")
    dataset = load_cleaned_dataset()
    vectorizer, model, _ = train_sentiment_pipeline(dataset)
    save_sentiment_artifacts(vectorizer, model)
