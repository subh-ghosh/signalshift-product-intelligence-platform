import pandas as pd
import joblib
import os
import time
from sklearn.model_selection import train_test_split
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.svm import LinearSVC
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import f1_score, accuracy_score, classification_report

# Robust path detection
BASE_DIR = "/media/subh/Shared Storage/signalshift/backend"
DATA_PATH = os.path.join(BASE_DIR, "data/processed/cleaned_reviews.csv")
OUTPUT_PATH = os.path.join(BASE_DIR, "data/processed/model_benchmark_step2.csv")

print("Step 2: Advanced Classifier Benchmarking")
print("Goal: Test 'Better Models' using the winning Bi-gram TF-IDF strategy.")

# Load data
df = pd.read_csv(DATA_PATH).dropna(subset=["cleaned_content"])
df["sentiment"] = df["score"].apply(lambda x: "positive" if x >= 4 else "negative")

X_train_raw, X_test_raw, y_train, y_test = train_test_split(
    df["cleaned_content"].astype(str), 
    df["sentiment"], 
    test_size=0.2, 
    random_state=42, 
    stratify=df["sentiment"]
)

# 1. Winning Vectorizer from Step 1
print("\n[V] Initializing Bi-gram TF-IDF Vectorizer...")
vectorizer = TfidfVectorizer(max_features=10000, ngram_range=(1, 2))
X_train = vectorizer.fit_transform(X_train_raw)
X_test = vectorizer.transform(X_test_raw)

# 2. Models to Benchmark
models = {
    "Logistic Regression": LogisticRegression(max_iter=1000, C=1.0),
    "Linear SVM": LinearSVC(dual='auto', C=1.0),
    "Random Forest": RandomForestClassifier(n_estimators=100, n_jobs=-1, verbose=0),
}

results = []

for name, model in models.items():
    print(f"\n[M] Training {name}...")
    start_time = time.time()
    
    model.fit(X_train, y_train)
    preds = model.predict(X_test)
    
    f1 = f1_score(y_test, preds, pos_label="positive")
    acc = accuracy_score(y_test, preds)
    duration = time.time() - start_time
    
    print(f"    - Accuracy: {acc:.4f}")
    print(f"    - F1-Score: {f1:.4f}")
    print(f"    - Time: {duration:.2f}s")
    
    results.append({
        "Model": name,
        "F1-Score": f1,
        "Accuracy": acc,
        "Time (sec)": duration
    })

# Summary
results_df = pd.DataFrame(results)
print("\n--- Model Comparison Summary (on Bi-gram TF-IDF) ---")
print(results_df.sort_values(by="F1-Score", ascending=False))

# Export results
results_df.to_csv(OUTPUT_PATH, index=False)
print(f"\nResults saved to {OUTPUT_PATH}")
