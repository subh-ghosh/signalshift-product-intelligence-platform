import pandas as pd
import os
import sys
from sklearn.model_selection import train_test_split
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import confusion_matrix, classification_report
import numpy as np

# Robust path detection
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA_PATH = os.path.join(BASE_DIR, "data/processed/cleaned_reviews.csv")

print("Step 12: Systematic Error Analysis (Under the Hood)")
print("Goal: Look at the EXACT reviews the AI got wrong to identify root causes.")

# 1. Load Data
df = pd.read_csv(DATA_PATH).dropna(subset=["cleaned_content"])
df["sentiment"] = df["score"].apply(lambda x: 1 if x >= 4 else 0)

# 2. Vectorization & Split
vectorizer = TfidfVectorizer(max_features=5000, ngram_range=(1, 2))
X = vectorizer.fit_transform(df["cleaned_content"].astype(str))
y = df["sentiment"]

X_train, X_test, y_train, y_test, indices_train, indices_test = train_test_split(
    X, y, df.index, test_size=0.2, random_state=42, stratify=y
)

# 3. Train Model
model = LogisticRegression(class_weight='balanced', max_iter=1000)
model.fit(X_train, y_train)
y_pred = model.predict(X_test)

# 4. Confusion Matrix
cm = confusion_matrix(y_test, y_pred)
print("\n--- Confusion Matrix ---")
print(f"True Negatives (Correct Complaints):  {cm[0][0]}")
print(f"False Positives (False Alarms):      {cm[0][1]}")
print(f"False Negatives (Missed Complaints):  {cm[1][0]}")
print(f"True Positives (Correct Praise):      {cm[1][1]}")

# 5. Extract specific failures
results_df = pd.DataFrame({
    'content': df.loc[indices_test, 'content'],
    'actual': y_test,
    'predicted': y_pred
})

# False Negatives (Most Dangerous: User was angry but AI said they were happy)
false_negatives = results_df[(results_df['actual'] == 0) & (results_df['predicted'] == 1)]

# False Positives (Noisy: User was happy but AI said they were angry)
false_positives = results_df[(results_df['actual'] == 1) & (results_df['predicted'] == 0)]

print("\n--- [X] False Negative Samples (Missed Issues) ---")
print("These are dangerous. The AI missed these complaints.")
for i, row in false_negatives.head(3).iterrows():
    print(f"\nReview: \"{row['content'][:150]}...\"")
    print(f"Actual: 0 (Negative) | Predicted: 1 (Positive)")

print("\n--- [!] False Positive Samples (False Alarms) ---")
print("These are noisy. The AI was too sensitive here.")
for i, row in false_positives.head(3).iterrows():
    print(f"\nReview: \"{row['content'][:150]}...\"")
    print(f"Actual: 1 (Positive) | Predicted: 0 (Negative)")

print("\n--- Research Insight ---")
print("By looking at these, we can see if the model fails on SARCASTIC reviews")
print("(e.g., 'Oh great, another bug') or VERY SHORT reviews.")
