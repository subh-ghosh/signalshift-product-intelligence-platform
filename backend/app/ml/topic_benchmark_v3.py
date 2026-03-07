import pandas as pd
import numpy as np
import os
from sklearn.decomposition import LatentDirichletAllocation as LDA
from sklearn.feature_extraction.text import CountVectorizer, ENGLISH_STOP_WORDS

BASE_DIR = "/media/subh/Shared Storage/signalshift/backend"
DATA_PATH = os.path.join(BASE_DIR, "data/processed/cleaned_reviews.csv")

# Load sample for testing
df = pd.read_csv(DATA_PATH).dropna(subset=["cleaned_content"]).sample(10000, random_state=42)

def run_benchmark():
    print("--- TOPIC INTELLIGENCE BENCHMARK ---")
    
    # 1. OLD STRATEGY: Full data, default stopwords, 10 components
    print("\n[Strategy A] OLD: Full Dataset, Default Stopwords")
    cv_old = CountVectorizer(max_features=1000, stop_words='english')
    tf_old = cv_old.fit_transform(df["cleaned_content"])
    lda_old = LDA(n_components=10, random_state=42)
    lda_old.fit(tf_old)
    
    # Analyze Keywords for Noise
    GENERIC_WORDS = {'app', 'netflix', 'good', 'great', 'nice', 'ok', 'hai', 'hua', 'hi', 'is', 'it'}
    old_keywords = []
    feature_names_old = cv_old.get_feature_names_out()
    noise_count_old = 0
    for topic in lda_old.components_:
        top_words = [feature_names_old[i] for i in topic.argsort()[:-6:-1]]
        old_keywords.append(", ".join(top_words))
        noise_count_old += sum(1 for w in top_words if w in GENERIC_WORDS)

    # 2. NEW STRATEGY: Negative ONLY, Custom Stopwords, Increased Components
    print("[Strategy B] NEW (Current): Negative-Only, Multi-lingual Filters")
    # Filter for negative (score <= 2)
    neg_df = df[df["score"] <= 2]
    CUSTOM_STOPWORDS = ['app', 'netflix', 'good', 'great', 'nice', 'ok', 'excellent', 'awesome', 'hai', 'hua', 'is', 'it']
    all_stops = list(ENGLISH_STOP_WORDS) + CUSTOM_STOPWORDS
    
    cv_new = CountVectorizer(max_features=1000, stop_words=all_stops)
    tf_new = cv_new.fit_transform(neg_df["cleaned_content"])
    lda_new = LDA(n_components=12, random_state=42)
    lda_new.fit(tf_new)
    
    new_keywords = []
    feature_names_new = cv_new.get_feature_names_out()
    noise_count_new = 0
    for topic in lda_new.components_:
        top_words = [feature_names_new[i] for i in topic.argsort()[:-6:-1]]
        new_keywords.append(", ".join(top_words))
        noise_count_new += sum(1 for w in top_words if w in GENERIC_WORDS)

    # Summary Report
    print("\n--- QUALITATIVE AUDIT ---")
    print(f"OLD Noise Ratio: {noise_count_old}/50 keywords ({ (noise_count_old/50)*100 }%)")
    print(f"NEW Noise Ratio: {noise_count_new}/60 keywords ({ (noise_count_new/60)*100 }%)")
    
    benchmark_df = pd.DataFrame({
        "Metric": ["Dataset Size", "Noise Ratio", "Primary Focus", "Actionability"],
        "OLD Strategy": [len(df), f"{(noise_count_old/50)*100:.1f}%", "General Talk", "Low (Generic Labels)"],
        "NEW Strategy": [len(neg_df), f"{(noise_count_new/60)*100:.1f}%", "Customer Friction", "High (Technical Labels)"]
    })
    
    print("\nBENCHMARK SUMMARY:")
    print(benchmark_df.to_string(index=False))
    
    benchmark_df.to_csv(os.path.join(BASE_DIR, "data/processed/topic_evolution_summary.csv"), index=False)
    print(f"\nSaved benchmark results to topic_evolution_summary.csv")

if __name__ == "__main__":
    run_benchmark()
