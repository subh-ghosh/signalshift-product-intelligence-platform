import pandas as pd
import torch
from transformers import pipeline
from sklearn.metrics import f1_score, accuracy_score, classification_report
import time
import os

# Robust path detection
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA_PATH = os.path.join(BASE_DIR, "data/processed/cleaned_all_combined.csv")

print("Step 2.5: Transformer (BERT) vs. ML Baseline")
print("Goal: Prove that Contextual Embeddings outperform traditional TF-IDF.")

# 1. Load Data
df = pd.read_csv(DATA_PATH).dropna(subset=["content"]) # Use raw content for BERT
df["sentiment_true"] = df["score"].apply(lambda x: "POSITIVE" if x >= 4 else "NEGATIVE")

# For Transformer benchmark, we use a sample of 2000 reviews 
# (Processing 191k via BERT on a local CPU/mid-range GPU would take hours)
sample_size = 2000
df_sample = df.sample(sample_size, random_state=42)

print(f"\n[D] Sampling {sample_size} reviews for scientific comparison...")

# 2. Initialize Transformer (DistilBERT is faster and highly accurate)
print("[T] Loading DistilBERT Sentiment Pipeline...")

# FORCE CPU: Your GTX 1050 (sm_61) is not compatible with the default torch kernels (sm_70+).
# Since 2000 reviews is manageable on CPU, we will force CPU for stability.
device = -1 
print("    - Forcing CPU mode for compatibility with GTX 1050.")

classifier = pipeline(
    "sentiment-analysis", 
    model="distilbert-base-uncased-finetuned-sst-2-english",
    device=device
)

# 3. Inference
print("\n[I] Running BERT Inference...")
start_time = time.time()

# Process in chunks to avoid memory issues
reviews = df_sample["content"].astype(str).tolist()
# Truncate reviews to 512 tokens (BERT limit)
reviews = [r[:512] for r in reviews]

raw_preds = []
batch_size = 32
for i in range(0, len(reviews), batch_size):
    batch = reviews[i:i + batch_size]
    outputs = classifier(batch)
    raw_preds.extend([o['label'] for o in outputs])

duration = time.time() - start_time

# 4. Evaluation
y_true = df_sample["sentiment_true"].tolist()
y_pred = raw_preds

acc = accuracy_score(y_true, y_pred)
f1 = f1_score(y_true, y_pred, pos_label="POSITIVE")

print(f"\n--- BERT Performance (N={sample_size}) ---")
print(f"Accuracy: {acc:.4f}")
print(f"F1-Score: {f1:.4f}")
print(f"Total Time: {duration:.2f}s (Avg: {duration/sample_size:.4f}s per review)")

print("\n--- Summary ---")
print("Classic ML Baseline F1: ~0.91")
if f1 > 0.91:
    print(f"TRANSFORMER WIN: BERT improved performance by {((f1/0.91)-1)*100:.2f}%")
else:
    print("TRANSFORMER DRAW: Baseline remains very strong on this specific dataset.")
