import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report, f1_score
from scipy.sparse import hstack
import os

# Robust path detection
BASE_DIR = "/media/subh/Shared Storage/signalshift/backend"
DATA_PATH = os.path.join(BASE_DIR, "data/processed/cleaned_reviews.csv")

print("Step 5: Advanced Research - Feature Engineering & Class Imbalance")
print("Goal: Prove if adding review metadata and handling imbalance improves 'Negative' discovery.")

# 1. Load Data
df = pd.read_csv(DATA_PATH).dropna(subset=["cleaned_content", "content"])
df["sentiment_bit"] = df["score"].apply(lambda x: 1 if x >= 4 else 0)

# 2. Advanced Feature Engineering
print("\n[F] Engineering Metadata Features...")
df["review_length"] = df["content"].str.len()
df["exclamation_count"] = df["content"].str.count("!")
df["question_count"] = df["content"].str.count("\?")
# Scale features (Standard practice)
df["review_length"] = df["review_length"] / df["review_length"].max()
df["exclamation_count"] = df["exclamation_count"] / (df["exclamation_count"].max() + 1)

# 3. Train Test Split
X_text_raw, X_test_text_raw, X_meta_raw, X_test_meta_raw, y_train, y_test = train_test_split(
    df["cleaned_content"].astype(str),
    df[["review_length", "exclamation_count", "question_count"]],
    df["sentiment_bit"],
    test_size=0.2,
    random_state=42,
    stratify=df["sentiment_bit"]
)

# 4. Vectorization
vectorizer = TfidfVectorizer(max_features=5000, ngram_range=(1, 2))
X_train_tfidf = vectorizer.fit_transform(X_text_raw)
X_test_tfidf = vectorizer.transform(X_test_text_raw)

# 5. Benchmarking
def run_benchmark(name, X_tr, X_te, weights=None):
    print(f"\nEvaluating: {name}...")
    model = LogisticRegression(max_iter=1000, class_weight=weights)
    model.fit(X_tr, y_train)
    preds = model.predict(X_te)
    # Focus on F1-Score for the NEGATIVE class (0)
    report = classification_report(y_test, preds, output_dict=True)
    f1_neg = report["0"]["f1-score"]
    recall_neg = report["0"]["recall"]
    print(f"    - Negative F1: {f1_neg:.4f}")
    print(f"    - Negative Recall: {recall_neg:.4f}")
    return f1_neg, recall_neg

# Test A: Baseline (Text only)
f1_a, recall_a = run_benchmark("Baseline (Text only)", X_train_tfidf, X_test_tfidf)

# Test B: Text + Metadata (Feature Engineering)
X_train_combined = hstack([X_train_tfidf, X_meta_raw.values])
X_test_combined = hstack([X_test_tfidf, X_test_meta_raw.values])
f1_b, recall_b = run_benchmark("Text + Metadata Features", X_train_combined, X_test_combined)

# Test C: Balanced Weights (Handling Imbalance)
f1_c, recall_c = run_benchmark("Text only + Balanced Weights", X_train_tfidf, X_test_tfidf, weights='balanced')

# 6. Conclusion
print("\n--- Advanced Benchmark Summary ---")
print(f"Baseline Negative F1: {f1_a:.4f}")
print(f"Meta-Feature Improvements: {((f1_b/f1_a)-1)*100:.2f}%")
print(f"Class Balancing Recall Gain: {((recall_c/recall_a)-1)*100:.2f}%")

if recall_c > recall_a:
    print("\n[INSIGHT] Class Balancing significantly improved Negative Recall.")
    print("This means the model is now MUCH better at catching unhappy customers!")
