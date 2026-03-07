import pandas as pd
import joblib
import os
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.decomposition import LatentDirichletAllocation as LDA

# Robust path detection
BASE_DIR = "/media/subh/Shared Storage/signalshift/backend"
DATA_PATH = os.path.join(BASE_DIR, "data/processed/cleaned_reviews.csv")
MODEL_DIR = os.path.join(BASE_DIR, "models")

print("Step 4: Finalizing Production Models")
print("Goal: Retrain the winners of our research phase on the FULL 191k dataset.")

# 1. Load Full Data
df = pd.read_csv(DATA_PATH).dropna(subset=["cleaned_content"])
X_full = df["cleaned_content"].astype(str)
y_full = df["score"].apply(lambda x: "positive" if x >= 4 else "negative")

# 2. Train Optimized Vectorizer (Step 1 Winner: Bi-grams)
print("\n[1/3] Training Production Bi-gram TF-IDF Vectorizer...")
vectorizer = TfidfVectorizer(max_features=10000, ngram_range=(1, 2))
X_vectorized = vectorizer.fit_transform(X_full)

# 3. Train Optimized Sentiment Model (Step 2 & 5 Winner: Balanced Logistic Regression)
print("[2/3] Training Production Sentiment Model (Logistic Regression)...")
# We use the research-proven 'balanced' weights to catch 10% more negative reviews
# and C=1.0 which was found to be optimal in Step 8 Tuning.
model = LogisticRegression(max_iter=1000, class_weight='balanced', C=1.0)
model.fit(X_vectorized, y_full)

# 4. Train Optimized Topic Model (Step 3 Winner: LDA)
print("[3/3] Training Production Topic Model (LDA)...")
# Note: For LDA, we need to pass standard word counts, not TF-IDF
from sklearn.feature_extraction.text import CountVectorizer
tf_vectorizer = CountVectorizer(max_features=5000, stop_words='english')
tf_full = tf_vectorizer.fit_transform(X_full)
lda = LDA(n_components=10, random_state=42)
lda.fit(tf_full)

# 5. Save Final Artifacts
print("\n[S] Saving production models to /models directory...")
joblib.dump(vectorizer, os.path.join(MODEL_DIR, "tfidf_vectorizer_v2.joblib"))
joblib.dump(model, os.path.join(MODEL_DIR, "sentiment_model_v2.joblib"))
joblib.dump(lda, os.path.join(MODEL_DIR, "lda_model.joblib"))
joblib.dump(tf_vectorizer, os.path.join(MODEL_DIR, "count_vectorizer.joblib"))

print("\nSuccess! Systems are ready for production upgrade.")
