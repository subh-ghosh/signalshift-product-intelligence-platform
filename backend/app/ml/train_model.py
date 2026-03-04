import pandas as pd
import joblib

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report, accuracy_score


# Load cleaned dataset
df = pd.read_csv("../../data/processed/cleaned_reviews.csv")

print("Dataset loaded:", df.shape)

# Safety validation
df = df.dropna(subset=["cleaned_content"])
df["cleaned_content"] = df["cleaned_content"].astype(str)

print("Dataset after validation:", df.shape)


# Convert rating → sentiment
def rating_to_sentiment(score):

    if score <= 2:
        return "negative"
    else:
        return "positive"


df["sentiment"] = df["score"].apply(rating_to_sentiment)

print("\nSentiment distribution:")
print(df["sentiment"].value_counts())


# TF-IDF Vectorization
print("\nCreating TF-IDF features...")

vectorizer = TfidfVectorizer(
    max_features=10000,
    ngram_range=(1, 2)
)

X = vectorizer.fit_transform(df["cleaned_content"])
y = df["sentiment"]


# Train/Test split
X_train, X_test, y_train, y_test = train_test_split(
    X,
    y,
    test_size=0.2,
    random_state=42
)

print("\nTraining samples:", X_train.shape[0])
print("Test samples:", X_test.shape[0])


# Train model
print("\nTraining Logistic Regression model...")

model = LogisticRegression(max_iter=1000)

model.fit(X_train, y_train)


# Evaluate
y_pred = model.predict(X_test)

print("\nAccuracy:", accuracy_score(y_test, y_pred))

print("\nClassification Report:")
print(classification_report(y_test, y_pred))


# Save model
print("\nSaving model and vectorizer...")

joblib.dump(model, "../../models/sentiment_model.joblib")
joblib.dump(vectorizer, "../../models/tfidf_vectorizer.joblib")

print("Model saved successfully.")