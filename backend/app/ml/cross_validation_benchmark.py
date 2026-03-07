import pandas as pd
import os
import numpy as np
from sklearn.model_selection import StratifiedKFold, cross_val_score
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression

# Robust path detection
BASE_DIR = "/media/subh/Shared Storage/signalshift/backend"
DATA_PATH = os.path.join(BASE_DIR, "data/processed/cleaned_reviews.csv")

print("Step 9: K-Fold Cross-Validation (The Robustness Test)")
print("Goal: Prove that our 91% F1-Score is stable and not a result of a 'lucky' data split.")

# 1. Load Data
df = pd.read_csv(DATA_PATH).dropna(subset=["cleaned_content"])
df["sentiment"] = df["score"].apply(lambda x: 1 if x >= 4 else 0)

# Using 30k samples for a robust yet reasonably fast 5-fold CV
df_sample = df.sample(30000, random_state=42)
X_text = df_sample["cleaned_content"].astype(str)
y = df_sample["sentiment"]

# 2. Vectorization
print("\n[V] Initializing Production Bi-gram Vectorizer...")
vectorizer = TfidfVectorizer(max_features=5000, ngram_range=(1, 2))
X = vectorizer.fit_transform(X_text)

# 3. Define the Model (Using our optimized settings)
model = LogisticRegression(max_iter=1000, class_weight='balanced', C=1.0)

# 4. Perform 5-Fold Cross-Validation
print(f"[C] Running 5-Fold Stratified Cross-Validation on 30k reviews...")
print("    (The data is split into 5 parts, and we test 5 times...)")

# We use StratifiedKFold to ensure each fold has the same ratio of pos/neg reviews
skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
scores = cross_val_score(model, X, y, cv=skf, scoring='f1')

# 5. Output Results
print("\n--- Cross-Validation Results ---")
for i, score in enumerate(scores):
    print(f"Fold {i+1} F1-Score: {score:.4f}")

print("-" * 30)
print(f"MEAN F1-SCORE: {np.mean(scores):.4f}")
print(f"STANDARD DEVIATION: {np.std(scores):.4f}")

print("\n--- Research Insight ---")
if np.std(scores) < 0.01:
    print("SUCCESS: The low standard deviation proves your model is extremely STABLE.")
    print("This means the model will perform reliably on any new reviews it sees.")
else:
    print("NOTICE: There is some variance in performance. We might need more data or better cleaning.")
