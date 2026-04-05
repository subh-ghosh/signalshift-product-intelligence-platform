import pandas as pd
import joblib
from sklearn.model_selection import train_test_split
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import f1_score
import time

import os

# Robust path detection
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
# Should be in backend/ml, so go up to backend
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(SCRIPT_DIR)))
# Or just hardcode the absolute path for this specific environment to be safe
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

DATA_PATH = os.path.join(BASE_DIR, "data/processed/cleaned_all_combined.csv")
OUTPUT_PATH = os.path.join(BASE_DIR, "data/processed/vector_benchmark.csv")

print("Step 1: Vectorization Benchmarking")
print("Goal: Compare different text-to-vector strategies using a consistent model (Logistic Regression)")

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

vectorizers = {
    "Uni-gram TF-IDF": TfidfVectorizer(max_features=5000),
    "Bi-gram TF-IDF": TfidfVectorizer(max_features=5000, ngram_range=(1, 2)),
    "Tri-gram TF-IDF": TfidfVectorizer(max_features=5000, ngram_range=(1, 3)),
    "Char-level TF-IDF": TfidfVectorizer(max_features=5000, analyzer='char', ngram_range=(2, 4))
}

results = []

for name, vec in vectorizers.items():
    print(f"\nEvaluating: {name}...")
    start_time = time.time()
    
    # Transform
    X_train = vec.fit_transform(X_train_raw)
    X_test = vec.transform(X_test_raw)
    
    # Train (using winner of previous model benchmark for consistency)
    model = LogisticRegression(max_iter=1000)
    model.fit(X_train, y_train)
    
    # Score
    preds = model.predict(X_test)
    f1 = f1_score(y_test, preds, pos_label="positive")
    
    duration = time.time() - start_time
    print(f"F1-Score: {f1:.4f} | Process Time: {duration:.2f}s")
    
    results.append({
        "Vectorizer": name,
        "F1-Score": f1,
        "Time (sec)": duration,
        "Vocabulary Size": len(vec.vocabulary_)
    })

# Summary
results_df = pd.DataFrame(results)
print("\n--- Vectorization Comparison Summary ---")
print(results_df.sort_values(by="F1-Score", ascending=False))

# Export for report
results_df.to_csv(OUTPUT_PATH, index=False)
