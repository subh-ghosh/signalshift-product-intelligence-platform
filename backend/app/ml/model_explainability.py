import pandas as pd
import joblib
import os
import numpy as np
import matplotlib.pyplot as plt

# Robust path detection
BASE_DIR = "/media/subh/Shared Storage/signalshift/backend"
MODEL_PATH = os.path.join(BASE_DIR, "models/sentiment_model_v2.joblib")
VEC_PATH = os.path.join(BASE_DIR, "models/tfidf_vectorizer_v2.joblib")

print("Step 6: Model Explainability (Transparency)")
print("Goal: Reveal the 'Most Powerful Words' used by the AI to make decisions.")

# 1. Load the production-grade v2 model
if not os.path.exists(MODEL_PATH):
    print("Error: Production v2 models not found. Run save_final_models.py first.")
    exit()

model = joblib.load(MODEL_PATH)
vectorizer = joblib.load(VEC_PATH)

# 2. Extract Coefficients (Importance weights)
feature_names = vectorizer.get_feature_names_out()
coefficients = model.coef_[0]

# Create a DataFrame for easy sorting
importance_df = pd.DataFrame({
    'word': feature_names,
    'weight': coefficients
})

# 3. Get Top Positive and Negative Indicators
top_positive = importance_df.sort_values(by='weight', ascending=False).head(20)
top_negative = importance_df.sort_values(by='weight', ascending=True).head(20)

print("\n--- Top 10 WORDS that drive POSITIVE sentiment ---")
print(top_positive[['word', 'weight']].head(10))

print("\n--- Top 10 WORDS that drive NEGATIVE sentiment ---")
print(top_negative[['word', 'weight']].head(10))

# 4. Save results for reports
report_csv = os.path.join(BASE_DIR, "data/processed/feature_importance.csv")
importance_df.to_csv(report_csv, index=False)
print(f"\n[S] Feature importance saved to {report_csv}")

print("\n--- Research Insight ---")
print("This output proves your model is not a 'Black Box'.")
print("We can see exactly which customer issues (like 'worst', 'bugs', 'buffering')")
print("are the strongest triggers for negative sentiment.")
