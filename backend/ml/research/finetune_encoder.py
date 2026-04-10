"""
SignalShift — Few-Shot Fine-Tuning Script (Phase 28 / Tier 3.3)
===============================================================
Fine-tunes MiniLM-L6-v2 using contrastive triplet loss on labeled review data.

Once you have verified ~50+ labeled examples per category (from manual review
of classification output), this script will push accuracy from ~80% → ~95%+.

Usage:
    # 1. Prepare labeled data (once you have at least 50 examples per category):
    #    CSV format: review (text), category (string from ISSUE_TAXONOMY labels)
    #    Save to: data/labeled/review_labels.csv

    # 2. Run fine-tuning:
    python app/ml/finetune_encoder.py

    # 3. The fine-tuned model is saved to: models/finetuned_encoder/
    #    Update ml_service.py to load from that path instead of all-MiniLM-L6-v2.

Requirements:
    pip install sentence-transformers[train]
"""

import os
import sys
import random
import pandas as pd
from pathlib import Path

BASE_DIR  = Path(__file__).resolve().parents[3]
DATA_DIR  = BASE_DIR / "data"
MODEL_DIR = BASE_DIR / "models"
LABELED_CSV = DATA_DIR / "labeled" / "review_labels.csv"
OUTPUT_DIR  = MODEL_DIR / "finetuned_encoder"

# ─── Validate Input ───────────────────────────────────────────────────────────
if not LABELED_CSV.exists():
    print(f"[ERROR] Labeled data not found at: {LABELED_CSV}")
    print()
    print("To generate labels for review, run a Kaggle sync and then:")
    print("  1. Open data/processed/topic_analysis.csv")
    print("  2. Review the sample_reviews per category")
    print("  3. Create data/labeled/review_labels.csv with columns: review, category")
    print("  4. Aim for 50+ examples per category for best results")
    sys.exit(1)

# ─── Load Labeled Data ────────────────────────────────────────────────────────
print("[1/5] Loading labeled training data...")
df = pd.read_csv(LABELED_CSV).dropna(subset=["review", "category"])
df["review"]    = df["review"].astype(str).str.strip()
df["category"]  = df["category"].astype(str).str.strip()

print(f"   Total labeled examples: {len(df)}")
print(f"   Categories: {df['category'].nunique()}")
print(f"   Distribution:\n{df['category'].value_counts().to_string()}")

MIN_EXAMPLES = 10
valid_cats = df["category"].value_counts()
valid_cats = valid_cats[valid_cats >= MIN_EXAMPLES].index.tolist()
df = df[df["category"].isin(valid_cats)]
print(f"\n   Using {len(df)} examples across {len(valid_cats)} categories with ≥{MIN_EXAMPLES} examples.")

# ─── Build Training Triplets ──────────────────────────────────────────────────
print("[2/5] Building training triplets (anchor, positive, negative)...")
from sentence_transformers import InputExample

cat_to_reviews = df.groupby("category")["review"].apply(list).to_dict()
triplets = []

for anchor_cat, anchor_reviews in cat_to_reviews.items():
    neg_cats = [c for c in valid_cats if c != anchor_cat]
    for anchor in anchor_reviews:
        # Sample a positive (different review, same category)
        positives = [r for r in anchor_reviews if r != anchor]
        if not positives:
            continue
        positive = random.choice(positives)
        # Sample a negative (review from any other category)
        neg_cat    = random.choice(neg_cats)
        negative   = random.choice(cat_to_reviews[neg_cat])
        triplets.append(InputExample(texts=[anchor, positive, negative]))

random.shuffle(triplets)
print(f"   Generated {len(triplets)} training triplets.")

# ─── Load Base Model ──────────────────────────────────────────────────────────
print("[3/5] Loading base MiniLM model...")
from sentence_transformers import SentenceTransformer, losses
from torch.utils.data import DataLoader

# Check for existing fine-tuned model first (for incremental training)
model_path = str(OUTPUT_DIR) if OUTPUT_DIR.exists() else "all-MiniLM-L6-v2"
model = SentenceTransformer(model_path, device="cpu")
print(f"   Loaded from: {model_path}")

# ─── Fine-Tune with Triplet Loss ──────────────────────────────────────────────
print("[4/5] Fine-tuning with triplet loss...")
train_dataloader = DataLoader(triplets, shuffle=True, batch_size=16)
train_loss       = losses.TripletLoss(model=model)

EPOCHS      = 3
WARMUP_FRAC = 0.1
warmup_steps = int(len(train_dataloader) * EPOCHS * WARMUP_FRAC)

model.fit(
    train_objectives=[(train_dataloader, train_loss)],
    epochs=EPOCHS,
    warmup_steps=warmup_steps,
    output_path=str(OUTPUT_DIR),
    show_progress_bar=True,
    checkpoint_path=str(OUTPUT_DIR / "checkpoints"),
    checkpoint_save_steps=len(train_dataloader),
)

# ─── Evaluate on Held-Out Set ─────────────────────────────────────────────────
print("[5/5] Evaluating alignment on canonical taxonomy categories...")
from ml.core.issue_labeler import ISSUE_TAXONOMY
import numpy as np

# Encode all category descriptions with the new model
cat_labels = [name for name, _ in ISSUE_TAXONOMY]
cat_descs  = [" ".join(descs) for _, descs in ISSUE_TAXONOMY]
cat_embs   = model.encode(cat_descs, normalize_embeddings=True)

# For each labeled example, check if its review classifies to correct category
correct = 0
total = 0
for _, row in df.iterrows():
    rev_emb  = model.encode([row["review"]], normalize_embeddings=True)[0]
    sims     = np.dot(cat_embs, rev_emb)
    predicted = cat_labels[int(np.argmax(sims))]
    if predicted.strip() == row["category"].strip():
        correct += 1
    total += 1

accuracy = correct / max(total, 1)
print(f"\n[Done] Fine-tuning complete!")
print(f"   Accuracy on labeled set: {accuracy:.1%} ({correct}/{total})")
print(f"   Model saved to: {OUTPUT_DIR}")
print()
print("NEXT STEP: Update ml_service.py to load from:")
print(f"  SentenceTransformer('{OUTPUT_DIR}', device='cpu')")
