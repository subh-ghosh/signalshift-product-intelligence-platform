"""Fine-tune SignalShift sentence encoder with triplet loss.

Usage (from backend/):
    python ml/pipeline/04_finetune_encoder.py \
        --input data/training/labeled/review_labels.csv \
        --output models/finetuned_encoder

Expected CSV schema (case-insensitive aliases supported):
- text column: review | text | content
- label column: category | label | issue_label

This script is optional and only needed when enough labeled data exists.

If --input is missing, the script can auto-generate it from:
    data/testing/processed/review_classifications.csv
"""

from __future__ import annotations

import argparse
import json
import random
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, classification_report, f1_score
from sklearn.model_selection import train_test_split
from sentence_transformers import InputExample, SentenceTransformer, losses
from sentence_transformers.evaluation import TripletEvaluator
from torch.utils.data import DataLoader

from ml.core.issue_labeler import ISSUE_TAXONOMY


DEFAULT_BASE_MODEL = "all-MiniLM-L6-v2"
DEFAULT_INPUT = "data/training/labeled/review_labels.csv"
DEFAULT_BOOTSTRAP_SOURCE = "data/testing/processed/review_classifications.csv"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fine-tune SentenceTransformer with triplet loss")
    parser.add_argument(
        "--input",
        default=DEFAULT_INPUT,
        help=f"Labeled CSV path (default: {DEFAULT_INPUT})",
    )
    parser.add_argument(
        "--output",
        default="models/finetuned_encoder",
        help="Directory to save fine-tuned model (default: models/finetuned_encoder)",
    )
    parser.add_argument(
        "--base-model",
        default=DEFAULT_BASE_MODEL,
        help=f"SentenceTransformer base model (default: {DEFAULT_BASE_MODEL})",
    )
    parser.add_argument("--epochs", type=int, default=3, help="Training epochs (default: 3)")
    parser.add_argument("--batch-size", type=int, default=32, help="Batch size (default: 32)")
    parser.add_argument(
        "--min-per-class",
        type=int,
        default=15,
        help="Minimum examples per class required to keep class (default: 15)",
    )
    parser.add_argument(
        "--max-triplets-per-class",
        type=int,
        default=500,
        help="Cap generated triplets per class (default: 500)",
    )
    parser.add_argument(
        "--eval-split",
        type=float,
        default=0.1,
        help="Triplet holdout ratio for evaluation [0, 0.5) (default: 0.1)",
    )
    parser.add_argument("--seed", type=int, default=42, help="Random seed (default: 42)")
    parser.add_argument(
        "--bootstrap-source",
        default=DEFAULT_BOOTSTRAP_SOURCE,
        help=(
            "Source CSV used to auto-generate --input when missing "
            f"(default: {DEFAULT_BOOTSTRAP_SOURCE})"
        ),
    )
    parser.add_argument(
        "--bootstrap-min-confidence",
        type=float,
        default=0.65,
        help="Minimum confidence for auto-generated labels (default: 0.65)",
    )
    parser.add_argument(
        "--bootstrap-max-per-class",
        type=int,
        default=300,
        help="Max auto-generated rows per class (default: 300)",
    )
    parser.add_argument(
        "--min-total-rows",
        type=int,
        default=120,
        help="Minimum labeled rows required to continue (default: 120)",
    )
    parser.add_argument(
        "--min-classes",
        type=int,
        default=6,
        help="Minimum distinct classes required to continue (default: 6)",
    )
    parser.add_argument(
        "--holdout-ratio",
        type=float,
        default=0.2,
        help="Holdout ratio for before/after evaluation [0.05, 0.4] (default: 0.2)",
    )
    return parser.parse_args()


def _resolve_column(columns: Iterable[str], candidates: list[str]) -> str | None:
    lookup = {c.lower().strip(): c for c in columns}
    for candidate in candidates:
        if candidate in lookup:
            return lookup[candidate]
    return None


def load_labeled_data(csv_path: Path, min_per_class: int) -> pd.DataFrame:
    if not csv_path.exists():
        raise FileNotFoundError(f"Labeled dataset not found: {csv_path}")

    df = pd.read_csv(csv_path)
    text_col = _resolve_column(df.columns, ["review", "text", "content"])
    label_col = _resolve_column(df.columns, ["category", "label", "issue_label"])

    if text_col is None or label_col is None:
        raise ValueError(
            "CSV must contain text and label columns. "
            "Accepted text: review/text/content; accepted label: category/label/issue_label."
        )

    cleaned = df[[text_col, label_col]].copy()
    cleaned.columns = ["text", "label"]
    cleaned["text"] = cleaned["text"].astype(str).str.strip()
    cleaned["label"] = cleaned["label"].astype(str).str.strip()
    cleaned = cleaned[(cleaned["text"] != "") & (cleaned["label"] != "")]

    counts = cleaned["label"].value_counts()
    kept_labels = counts[counts >= min_per_class].index
    cleaned = cleaned[cleaned["label"].isin(kept_labels)].reset_index(drop=True)

    if cleaned.empty:
        raise ValueError(
            "No classes left after min-per-class filter. "
            "Lower --min-per-class or provide more labeled data."
        )

    if cleaned["label"].nunique() < 2:
        raise ValueError("At least 2 classes are required for triplet training.")

    return cleaned


def bootstrap_labeled_data(
    *,
    output_csv: Path,
    source_csv: Path,
    min_confidence: float,
    max_per_class: int,
    seed: int,
) -> int:
    """Generate review_labels.csv from review_classifications.csv.

    Returns number of generated rows.
    """
    if not source_csv.exists():
        raise FileNotFoundError(
            "Could not auto-generate labels because bootstrap source is missing: "
            f"{source_csv}. Run ingestion/analysis first or provide --input manually."
        )

    raw = pd.read_csv(source_csv)
    text_col = _resolve_column(raw.columns, ["text", "content", "review"])
    label_col = _resolve_column(raw.columns, ["category", "label", "issue_label"])
    conf_col = _resolve_column(raw.columns, ["confidence", "score"])

    if text_col is None or label_col is None or conf_col is None:
        raise ValueError(
            "Bootstrap source must contain text, label, and confidence columns. "
            "Expected text: text/content/review; label: category/label/issue_label; "
            "confidence: confidence/score."
        )

    df = raw[[text_col, label_col, conf_col]].copy()
    df.columns = ["review", "category", "confidence"]
    df["review"] = df["review"].astype(str).str.strip()
    df["category"] = df["category"].astype(str).str.strip()
    df["confidence"] = pd.to_numeric(df["confidence"], errors="coerce")

    df = df[(df["review"] != "") & (df["category"] != "") & (df["confidence"].notna())]
    df = df[df["category"] != "General App Feedback"]
    df = df[df["confidence"] >= float(min_confidence)]

    if df.empty:
        raise ValueError(
            "Bootstrap source had no rows after filtering. "
            "Lower --bootstrap-min-confidence or provide manual labeled data."
        )

    df = df.sort_values("confidence", ascending=False)
    sampled = (
        df.groupby("category", group_keys=False)
        .head(int(max_per_class))
        .sample(frac=1.0, random_state=seed)
        .reset_index(drop=True)
    )

    output_csv.parent.mkdir(parents=True, exist_ok=True)
    sampled[["review", "category"]].to_csv(output_csv, index=False)
    return int(len(sampled))


def build_triplets(df: pd.DataFrame, seed: int, max_triplets_per_class: int) -> list[InputExample]:
    rng = random.Random(seed)
    groups = {label: rows["text"].tolist() for label, rows in df.groupby("label")}
    labels = list(groups.keys())

    triplets: list[InputExample] = []
    for label in labels:
        positives = groups[label]
        negatives_pool = [item for other in labels if other != label for item in groups[other]]

        if len(positives) < 2 or not negatives_pool:
            continue

        class_triplets = 0
        for anchor in positives:
            if class_triplets >= max_triplets_per_class:
                break

            pos_candidates = [p for p in positives if p != anchor]
            if not pos_candidates:
                continue

            positive = rng.choice(pos_candidates)
            negative = rng.choice(negatives_pool)
            triplets.append(InputExample(texts=[anchor, positive, negative]))
            class_triplets += 1

    if not triplets:
        raise ValueError("Failed to generate triplets from labeled data.")

    rng.shuffle(triplets)
    return triplets


def split_triplets(triplets: list[InputExample], eval_split: float) -> tuple[list[InputExample], list[InputExample]]:
    if eval_split <= 0:
        return triplets, []
    if eval_split >= 0.5:
        raise ValueError("--eval-split must be < 0.5")

    split_idx = max(1, int(len(triplets) * (1 - eval_split)))
    train = triplets[:split_idx]
    val = triplets[split_idx:]

    if len(train) < 4:
        raise ValueError("Not enough training triplets after split. Reduce --eval-split.")

    return train, val


def category_coverage(df: pd.DataFrame) -> dict[str, int]:
    known = {label for label, _ in ISSUE_TAXONOMY}
    counts = df["label"].value_counts().to_dict()
    coverage = {label: int(counts.get(label, 0)) for label in sorted(known)}
    return coverage


def validate_dataset_quality(df: pd.DataFrame, *, min_total_rows: int, min_classes: int) -> None:
    total_rows = int(len(df))
    class_count = int(df["label"].nunique())
    if total_rows < int(min_total_rows):
        raise ValueError(
            f"Labeled dataset too small: {total_rows} rows < required {min_total_rows}."
        )
    if class_count < int(min_classes):
        raise ValueError(
            f"Insufficient class diversity: {class_count} classes < required {min_classes}."
        )


def _normalize_rows(v: np.ndarray) -> np.ndarray:
    denom = np.linalg.norm(v, axis=1, keepdims=True)
    denom[denom == 0] = 1.0
    return v / denom


def evaluate_encoder_with_centroids(
    model: SentenceTransformer,
    train_df: pd.DataFrame,
    test_df: pd.DataFrame,
) -> dict:
    # Encode and normalize train/test vectors
    train_emb = model.encode(train_df["text"].tolist(), normalize_embeddings=True, show_progress_bar=False)
    test_emb = model.encode(test_df["text"].tolist(), normalize_embeddings=True, show_progress_bar=False)

    # Build normalized centroids per class from training fold
    centroids = {}
    for label, group in train_df.groupby("label"):
        idx = group.index.to_numpy()
        vec = np.asarray(train_emb)[idx]
        centroid = vec.mean(axis=0)
        norm = np.linalg.norm(centroid)
        if norm > 0:
            centroid = centroid / norm
        centroids[label] = centroid

    labels = sorted(centroids.keys())
    centroid_matrix = np.vstack([centroids[lbl] for lbl in labels])
    centroid_matrix = _normalize_rows(centroid_matrix)

    sims = np.asarray(test_emb).dot(centroid_matrix.T)
    pred_idx = np.argmax(sims, axis=1)
    y_pred = [labels[i] for i in pred_idx]
    y_true = test_df["label"].tolist()

    return {
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "f1_macro": float(f1_score(y_true, y_pred, average="macro", zero_division=0)),
        "f1_weighted": float(f1_score(y_true, y_pred, average="weighted", zero_division=0)),
        "classification_report": classification_report(y_true, y_pred, output_dict=True, zero_division=0),
        "n_test": int(len(test_df)),
    }


def main() -> int:
    args = parse_args()
    random.seed(args.seed)

    input_path = Path(args.input)
    output_path = Path(args.output)
    bootstrap_source = Path(args.bootstrap_source)

    if not input_path.exists():
        print(f"[finetune] Labeled CSV not found at {input_path}. Attempting auto-generation...")
        generated = bootstrap_labeled_data(
            output_csv=input_path,
            source_csv=bootstrap_source,
            min_confidence=args.bootstrap_min_confidence,
            max_per_class=args.bootstrap_max_per_class,
            seed=args.seed,
        )
        print(
            "[finetune] Auto-generated labeled dataset: "
            f"{input_path} ({generated} rows) from {bootstrap_source}"
        )

    print("[finetune] Loading labeled dataset...")
    labeled_df = load_labeled_data(input_path, min_per_class=args.min_per_class)
    validate_dataset_quality(
        labeled_df,
        min_total_rows=args.min_total_rows,
        min_classes=args.min_classes,
    )

    if not (0.05 <= float(args.holdout_ratio) <= 0.4):
        raise ValueError("--holdout-ratio must be between 0.05 and 0.4")

    print(
        f"[finetune] Loaded {len(labeled_df)} rows across "
        f"{labeled_df['label'].nunique()} classes"
    )

    eval_train_df, eval_test_df = train_test_split(
        labeled_df,
        test_size=float(args.holdout_ratio),
        random_state=args.seed,
        stratify=labeled_df["label"],
    )

    print(f"[finetune] Loading baseline encoder: {args.base_model}")
    baseline_model = SentenceTransformer(args.base_model, device="cpu")
    baseline_eval = evaluate_encoder_with_centroids(baseline_model, eval_train_df, eval_test_df)
    print(
        "[finetune] Baseline holdout metrics: "
        f"acc={baseline_eval['accuracy']:.4f}, f1_macro={baseline_eval['f1_macro']:.4f}"
    )

    print("[finetune] Building triplets...")
    triplets = build_triplets(
        labeled_df,
        seed=args.seed,
        max_triplets_per_class=args.max_triplets_per_class,
    )
    train_triplets, val_triplets = split_triplets(triplets, args.eval_split)

    print(
        f"[finetune] Triplets: total={len(triplets)}, "
        f"train={len(train_triplets)}, val={len(val_triplets)}"
    )

    print(f"[finetune] Loading trainable encoder: {args.base_model}")
    model = SentenceTransformer(args.base_model, device="cpu")

    train_loader = DataLoader(train_triplets, shuffle=True, batch_size=args.batch_size)
    train_loss = losses.TripletLoss(model=model)

    evaluator = None
    if val_triplets:
        anchors = [t.texts[0] for t in val_triplets]
        positives = [t.texts[1] for t in val_triplets]
        negatives = [t.texts[2] for t in val_triplets]
        evaluator = TripletEvaluator(
            anchors=anchors,
            positives=positives,
            negatives=negatives,
            name="val",
        )

    warmup_steps = max(10, int(len(train_loader) * args.epochs * 0.1))

    print("[finetune] Training...")
    model.fit(
        train_objectives=[(train_loader, train_loss)],
        evaluator=evaluator,
        epochs=args.epochs,
        warmup_steps=warmup_steps,
        show_progress_bar=True,
    )

    output_path.mkdir(parents=True, exist_ok=True)
    model.save(str(output_path))

    finetuned_eval = evaluate_encoder_with_centroids(model, eval_train_df, eval_test_df)
    print(
        "[finetune] Fine-tuned holdout metrics: "
        f"acc={finetuned_eval['accuracy']:.4f}, f1_macro={finetuned_eval['f1_macro']:.4f}"
    )

    eval_report = {
        "baseline": baseline_eval,
        "finetuned": finetuned_eval,
        "delta": {
            "accuracy": float(finetuned_eval["accuracy"] - baseline_eval["accuracy"]),
            "f1_macro": float(finetuned_eval["f1_macro"] - baseline_eval["f1_macro"]),
            "f1_weighted": float(finetuned_eval["f1_weighted"] - baseline_eval["f1_weighted"]),
        },
    }
    (output_path / "evaluation_report.json").write_text(
        json.dumps(eval_report, indent=2), encoding="utf-8"
    )

    metadata = {
        "base_model": args.base_model,
        "epochs": args.epochs,
        "batch_size": args.batch_size,
        "seed": args.seed,
        "input": str(input_path),
        "total_rows": int(len(labeled_df)),
        "classes": int(labeled_df["label"].nunique()),
        "triplets_total": int(len(triplets)),
        "triplets_train": int(len(train_triplets)),
        "triplets_val": int(len(val_triplets)),
        "holdout_ratio": float(args.holdout_ratio),
        "holdout_rows": int(len(eval_test_df)),
        "coverage": category_coverage(labeled_df),
    }
    (output_path / "training_metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")

    print(f"[finetune] Saved fine-tuned model to: {output_path}")
    print(f"[finetune] Metadata: {output_path / 'training_metadata.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
