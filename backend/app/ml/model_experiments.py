import pandas as pd
import joblib
import os

from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score

from sklearn.linear_model import LogisticRegression
from sklearn.naive_bayes import MultinomialNB
from sklearn.svm import LinearSVC
from sklearn.ensemble import RandomForestClassifier

# Ensure we are in the right relative path if run from project root or ml dir
DATA_PATH = "../../data/processed/cleaned_reviews.csv"
VECTORIZER_PATH = "../../models/tfidf_vectorizer.joblib"
OUTPUT_PATH = "../../data/processed/model_comparison.csv"

# Fallback for different working directories
if not os.path.exists(DATA_PATH):
    DATA_PATH = "data/processed/cleaned_reviews.csv"
    VECTORIZER_PATH = "models/tfidf_vectorizer.joblib"
    OUTPUT_PATH = "data/processed/model_comparison.csv"

print("Loading dataset...")
df = pd.read_csv(DATA_PATH)
df = df.dropna(subset=["cleaned_content"])
df["cleaned_content"] = df["cleaned_content"].astype(str)

print("Dataset size:", df.shape)

# -----------------------------
# Sentiment Labels
# -----------------------------

def label_sentiment(score):
    if score >= 4:
        return "positive"
    else:
        return "negative"

df["sentiment"] = df["score"].apply(label_sentiment)

print("\nSentiment distribution:")
print(df["sentiment"].value_counts())

# -----------------------------
# Load Vectorizer
# -----------------------------

print("\nLoading TF-IDF vectorizer...")
vectorizer = joblib.load(VECTORIZER_PATH)
X = vectorizer.transform(df["cleaned_content"])
y = df["sentiment"]

# -----------------------------
# Train Test Split
# -----------------------------

X_train, X_test, y_train, y_test = train_test_split(
    X,
    y,
    test_size=0.2,
    random_state=42,
    stratify=y
)

print("\nTraining samples:", X_train.shape[0])
print("Test samples:", X_test.shape[0])

# -----------------------------
# Models to Compare
# -----------------------------

models = {
    "Logistic Regression": LogisticRegression(max_iter=1000),
    "Naive Bayes": MultinomialNB(),
    "Linear SVM": LinearSVC(dual='auto'), # Standard for large datasets
    "Random Forest": RandomForestClassifier(n_estimators=100, n_jobs=-1) # parallel processing
}

results = []

# -----------------------------
# Train and Evaluate
# -----------------------------

for name, model in models.items():
    print(f"\nTraining {name}...")
    model.fit(X_train, y_train)
    preds = model.predict(X_test)

    accuracy = accuracy_score(y_test, preds)
    precision = precision_score(y_test, preds, pos_label="positive")
    recall = recall_score(y_test, preds, pos_label="positive")
    f1 = f1_score(y_test, preds, pos_label="positive")

    results.append({
        "model": name,
        "accuracy": accuracy,
        "precision": precision,
        "recall": recall,
        "f1_score": f1
    })

# -----------------------------
# Results
# -----------------------------

results_df = pd.DataFrame(results)
print("\nModel Comparison Results:")
print(results_df)

# -----------------------------
# Save Results
# -----------------------------

results_df.to_csv(OUTPUT_PATH, index=False)
print(f"\nResults saved to {OUTPUT_PATH}")
