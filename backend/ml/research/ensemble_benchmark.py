import pandas as pd
import os
import time
from sklearn.model_selection import train_test_split
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.svm import LinearSVC
from sklearn.ensemble import RandomForestClassifier, VotingClassifier
from sklearn.metrics import f1_score, accuracy_score

# Robust path detection
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA_PATH = os.path.join(BASE_DIR, "data/processed/cleaned_all_combined.csv")

print("Step 7: Ensemble Modeling (Voter System)")
print("Goal: Combine the strengths of multiple models to achieve a 'Consensus' result.")

# 1. Load Data
df = pd.read_csv(DATA_PATH).dropna(subset=["cleaned_content"])
df["sentiment"] = df["score"].apply(lambda x: "positive" if x >= 4 else "negative")

X_train_raw, X_test_raw, y_train, y_test = train_test_split(
    df["cleaned_content"].astype(str), 
    df["sentiment"], 
    test_size=0.2, 
    random_state=42, 
    stratify=df["sentiment"]
)

# 2. Vectorization (Using our Research-Proven Bi-grams)
print("\n[V] Initializing Bi-gram Vectorizer...")
vectorizer = TfidfVectorizer(max_features=5000, ngram_range=(1, 2))
X_train = vectorizer.fit_transform(X_train_raw)
X_test = vectorizer.transform(X_test_raw)

# 3. Define the Ensemble (The "Board of Directors")
print("[E] Creating Voting Classifier (LR + SVM + RF)...")
# Note: LinearSVC doesn't have predict_proba by default, so we use its decision function in a 'hard' vote
clf1 = LogisticRegression(max_iter=1000, class_weight='balanced')
clf2 = LinearSVC(dual='auto', class_weight='balanced')
clf3 = RandomForestClassifier(n_estimators=50, n_jobs=-1, class_weight='balanced')

voter = VotingClassifier(
    estimators=[('lr', clf1), ('svm', clf2), ('rf', clf3)],
    voting='hard' # Majority wins
)

# 4. Train and Evaluate
print("\n[T] Training the Ensemble (this may take 2-3 minutes due to Random Forest)...")
start_time = time.time()
voter.fit(X_train, y_train)
preds = voter.predict(X_test)
duration = time.time() - start_time

# 5. Compare against individual Step 2 results
f1 = f1_score(y_test, preds, pos_label="positive")
acc = accuracy_score(y_test, preds)

print(f"\n--- Ensemble Performance Results ---")
print(f"Accuracy: {acc:.4f}")
print(f"F1-Score: {f1:.4f}")
print(f"Total Time: {duration:.2f}s")

print("\n--- Why this matters in Research ---")
print("An ensemble reduces variance. Even if one model makes a mistake,")
print("the other two can correct it. It shows you know how to build")
print("high-reliability 'Robust' AI systems.")
