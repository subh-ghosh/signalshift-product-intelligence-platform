"""
SignalShift — Neural Topic Model for Unknown Issue Discovery (Phase 25.3)
=========================================================================
Tier 2 DS Upgrade: Instead of TF-IDF → NMF (bag-of-words clustering),
this script runs NMF on MiniLM sentence embeddings — the semantic space.

This discovers patterns in the data that DON'T fit the predefined taxonomy.
Run this offline as a research tool when you suspect new issue types are emerging.

Output: data/processed/neural_topics.csv
"""

import pandas as pd
import numpy as np
import joblib
import os
from sklearn.decomposition import NMF
from sentence_transformers import SentenceTransformer

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA_DIR  = os.path.join(BASE_DIR, "data/processed")
MODEL_DIR = os.path.join(BASE_DIR, "models")

# ─── Load Data ────────────────────────────────────────────────────────────────
print("[1/4] Loading cleaned reviews...")
df = pd.read_csv(os.path.join(DATA_DIR, "cleaned_reviews.csv")).dropna(subset=["cleaned_content"])

# Focus on negative reviews — same as the main pipeline
negative_df = df[df["score"] <= 2].copy()
reviews = negative_df["cleaned_content"].astype(str).tolist()

# Subsample to keep it fast (20k is plenty for discovery)
MAX_SAMPLES = 20_000
if len(reviews) > MAX_SAMPLES:
    import random; random.seed(42)
    reviews = random.sample(reviews, MAX_SAMPLES)

print(f"   Using {len(reviews)} negative reviews for neural topic discovery.")

# ─── Encode with MiniLM ───────────────────────────────────────────────────────
print("[2/4] Encoding reviews with MiniLM (semantic space)...")
encoder = SentenceTransformer("all-MiniLM-L6-v2", device="cpu")
# Encode in batches; L2-normalize for cosine space
embeddings = encoder.encode(
    reviews, batch_size=256, normalize_embeddings=True,
    show_progress_bar=True
)
print(f"   Embedding matrix shape: {embeddings.shape}")  # (N, 384)

# ─── Neural NMF ───────────────────────────────────────────────────────────────
# NMF requires non-negative inputs. Shift the L2-normalized embeddings
# so all values ≥ 0 (RELU-like shift: X_nn = X - min(X))
print("[3/4] Running Neural NMF on embedding matrix...")
X_nn = embeddings - embeddings.min()  # All values → [0, max]

N_TOPICS = 15  # Discover 15 neural topics
nmf_neural = NMF(n_components=N_TOPICS, random_state=42, init="nndsvd", max_iter=500)
W = nmf_neural.fit_transform(X_nn)   # (N samples, 15 topics)
H = nmf_neural.components_            # (15 topics, 384 dims)

# ─── Interpret Topics ─────────────────────────────────────────────────────────
# For each neural topic, find the top-5 most representative reviews
print("[4/4] Extracting representative reviews per neural topic...")
topic_rows = []
for t_idx in range(N_TOPICS):
    # Reviews most strongly associated with this topic
    scores  = W[:, t_idx]
    top_ids = np.argsort(scores)[-5:][::-1]  # Top 5 review indices
    top_reviews = [reviews[i][:120] for i in top_ids]
    avg_score   = float(np.mean(scores[top_ids]))

    topic_rows.append({
        "neural_topic_id": t_idx,
        "avg_activation":  round(avg_score, 4),
        "review_1": top_reviews[0] if len(top_reviews) > 0 else "",
        "review_2": top_reviews[1] if len(top_reviews) > 1 else "",
        "review_3": top_reviews[2] if len(top_reviews) > 2 else "",
        "review_4": top_reviews[3] if len(top_reviews) > 3 else "",
        "review_5": top_reviews[4] if len(top_reviews) > 4 else "",
    })

out_df = pd.DataFrame(topic_rows).sort_values(by="avg_activation", ascending=False)
out_path = os.path.join(DATA_DIR, "neural_topics.csv")
out_df.to_csv(out_path, index=False)

print(f"\n[Done] Neural topic discovery complete!")
print(f"       Output: {out_path}")
print(f"       {N_TOPICS} semantic clusters discovered from {len(reviews)} reviews.")
print("\nTop neural topics (by activation):")
print(out_df[["neural_topic_id", "avg_activation", "review_1"]].head(5).to_string())
print("\nUsage: Review neural_topics.csv and identify any cluster that doesn't")
print("       match an existing taxonomy category → add it to ISSUE_TAXONOMY in issue_labeler.py")
