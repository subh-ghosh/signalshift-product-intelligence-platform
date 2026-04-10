import pandas as pd
import joblib
import os
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.decomposition import LatentDirichletAllocation as LDA

# Robust path detection
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
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

# 4. Train Optimized Topic Model (NMF Precision Upgrade)
print("[3/3] Training Production Topic Model (NMF)...")
# FIX: Filter for negative reviews to ensure "Issues" are the priority
negative_df = df[df["score"] <= 2]
negative_text = negative_df["cleaned_content"].astype(str)

# CUSTOM STOPWORDS to clean up the clusters
CUSTOM_STOPWORDS = [
    'app', 'netflix', 'good', 'great', 'nice', 'ok', 'excellent', 'awesome', 
    'amazing', 'super', 'useful', 'best', 'worst', 'better', 'quality', 'hai', 
    'hua', 'hi', 'bhai', 'yaar', 'kya', 'ko', 'ki', 'he', 'it', 'very', 'is', 
    'really', 'love', 'like', 'work', 'working', 'use', 'using', 'application',
    'just', 'don', 't', 's', 'can', 've', 're', 'm'
]
from sklearn.feature_extraction.text import TfidfVectorizer, ENGLISH_STOP_WORDS
from sklearn.decomposition import NMF
# all_stops = list(ENGLISH_STOP_WORDS) + CUSTOM_STOPWORDS # This line is removed as custom_stop_words is defined below.

# 2. Extract TF-IDF features for NMF Topic Discovery
# We only want to discover topics from NEGATIVE reviews to find ISSUES
# Assuming 'processed_df' is 'df' and 'sentiment' can be derived from 'score'
# and 'content' is 'cleaned_content'
negative_text = df[df['score'] <= 2]['cleaned_content'].astype(str).str.lower()


# True Vectorizer Stop-Words (Phase 14.1)
# These words are now mathematically ignored by the clustering engine
custom_stop_words = list(ENGLISH_STOP_WORDS.union({
    "app", "netflix", "good", "bad", "great", "excellent", "nice", "ok", "awesome",
    "hai", "hua", "hi", "bhai", "yaar", "kya", "ko", "ki", "he", "it", "very", "is",
    "application", "working", "work", "use", "using", "like", "love", "really",
    "amazing", "super", "useful", "best", "worst", "better", "quality", "time", "hai",
    "just", "don", "t", "s", "can", "ve", "re", "m", "want", "let", "the", "an", "this",
    "phone", "mobile", "update"
}))

nmf_vectorizer = TfidfVectorizer(max_df=0.95, min_df=2, stop_words=custom_stop_words)
X_nmf = nmf_vectorizer.fit_transform(negative_text)

# NMF is mathematically more stable for short reviews than LDA
# Increase granularity (n=30) for maximum precision (Phase 14)
nmf = NMF(n_components=30, random_state=42, init='nndsvd')
nmf.fit(X_nmf)

# 5. Save Final Artifacts
print("\n[S] Saving production models to /models directory...")
joblib.dump(vectorizer, os.path.join(MODEL_DIR, "tfidf_vectorizer_v2.joblib"))
joblib.dump(model, os.path.join(MODEL_DIR, "sentiment_model_v2.joblib"))
joblib.dump(nmf, os.path.join(MODEL_DIR, "nmf_model.joblib"))
joblib.dump(nmf_vectorizer, os.path.join(MODEL_DIR, "nmf_vectorizer.joblib"))

print("\nSuccess! Systems are ready for production upgrade.")
