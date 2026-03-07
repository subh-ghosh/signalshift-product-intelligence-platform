import pandas as pd
import os
from sklearn.model_selection import train_test_split, GridSearchCV
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report

# Robust path detection
BASE_DIR = "/media/subh/Shared Storage/signalshift/backend"
DATA_PATH = os.path.join(BASE_DIR, "data/processed/cleaned_reviews.csv")

print("Step 8: Hyperparameter Tuning (The Search for the Optimum)")
print("Goal: Use GridSearchCV to scientifically find the best 'C' parameter.")

# 1. Load Data (Sub-sampling for speed during grid search)
df = pd.read_csv(DATA_PATH).dropna(subset=["cleaned_content"])
df["sentiment"] = df["score"].apply(lambda x: 1 if x >= 4 else 0)

# We use 20k samples for tuning to keep it fast but accurate
df_sample = df.sample(20000, random_state=42)
X_text = df_sample["cleaned_content"].astype(str)
y = df_sample["sentiment"]

# 2. Vectorization
vectorizer = TfidfVectorizer(max_features=5000, ngram_range=(1, 2))
X = vectorizer.fit_transform(X_text)

# 3. Define Hyperparameter Grid
# C = Inverse of regularization strength (smaller values = stronger regularization)
param_grid = {
    'C': [0.1, 1, 10, 100],
    'penalty': ['l2'],
    'solver': ['liblinear', 'lbfgs']
}

# 4. Run Grid Search
print("\n[G] Running Grid Search 5-Fold Cross-Validation...")
print("    (Testing 8 different combinations...)")
grid = GridSearchCV(
    LogisticRegression(max_iter=1000, class_weight='balanced'),
    param_grid,
    cv=5,
    scoring='f1', # Focus on F1 score
    verbose=1,
    n_jobs=-1
)

grid.fit(X, y)

# 5. Results
print("\n--- Hyperparameter Results ---")
print(f"Best Parameters: {grid.best_params_}")
print(f"Best F1-Score: {grid.best_score_:.4f}")

# 6. Final verification on those params
best_clf = grid.best_estimator_
print("\n[INSIGHT] If the best C is 10 or 100, the model wants to 'trust' the data more.")
print("If the best C is 0.1, it wants to 'generalize' more to avoid overfitting.")
