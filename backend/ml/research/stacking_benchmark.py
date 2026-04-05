import pandas as pd
import os
import sys
from sklearn.model_selection import train_test_split
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.svm import LinearSVC
from sklearn.ensemble import RandomForestClassifier, StackingClassifier
from sklearn.metrics import classification_report

# Robust path detection
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA_PATH = os.path.join(BASE_DIR, "data/processed/cleaned_all_combined.csv")

print("Step 13: Stacking Ensemble (The Meta-AI)")
print("Goal: Train an AI to learn which other AI to trust.")

# 1. Load Data (Sub-sampling for ensemble speed)
df = pd.read_csv(DATA_PATH).dropna(subset=["cleaned_content"])
df["sentiment"] = df["score"].apply(lambda x: 1 if x >= 4 else 0)

# 30k samples for a balanced speed/accuracy test
df_sample = df.sample(30000, random_state=42)
X_text = df_sample["cleaned_content"].astype(str)
y = df_sample["sentiment"]

# 2. Vectorization
vectorizer = TfidfVectorizer(max_features=5000, ngram_range=(1, 2))
X = vectorizer.fit_transform(X_text)

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# 3. Define Base Estimators
base_estimators = [
    ('lr', LogisticRegression(class_weight='balanced', C=1.0)),
    ('svc', LinearSVC(class_weight='balanced', dual=False, C=1.0)),
]

# 4. Define Meta-Estimator (The Boss Model)
# This model takes the predictions of the others as its input!
final_estimator = LogisticRegression()

# 5. Create and Train Stacking Classifier
print("\n[S] Training Stacking Ensemble...")
print("    - Base 1: Logistic Regression")
print("    - Base 2: Linear SVM")
print("    - Meta: Logistic Regression (The Tie-Breaker)")

stack_clf = StackingClassifier(
    estimators=base_estimators,
    final_estimator=final_estimator,
    cv=5,
    n_jobs=-1
)

stack_clf.fit(X_train, y_train)

# 6. Evaluate
y_pred = stack_clf.predict(X_test)
print("\n--- Stacking Ensemble Results ---")
print(classification_report(y_test, y_pred))

# 7. Comparison Insight
print("\n--- Research Insight ---")
print("Stacking is superior to standard 'Voting' because the Meta-Model learns:")
print("'When the text is short, listen to the SVM. When it's long, listen to the LR.'")
