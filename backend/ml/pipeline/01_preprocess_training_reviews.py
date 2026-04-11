"""Step 01: Clean + normalize the curated training dataset.

Input:
  backend/data/training/raw/all_combined.csv

Output:
  backend/data/training/processed/cleaned_all_combined.csv
"""

from __future__ import annotations

import os
import sys

import pandas as pd

from pipeline_common import load_raw_dataset, save_cleaned_dataset


# Ensure `backend/` is on sys.path so `import ml.*` works when running as a script.
BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from ml.core.text_cleaner import clean_text


def preprocess(df: pd.DataFrame) -> pd.DataFrame:
    df = df.dropna(subset=["content"]).copy()
    df = df[df["content"].astype(str).str.strip() != ""]
    df = df.reset_index(drop=True)

    cleaned = []
    total = len(df)
    for idx, text in enumerate(df["content"].astype(str)):
        if idx % 5000 == 0 and idx > 0:
            print(f"  cleaned {idx:,}/{total:,}")
        cleaned.append(clean_text(text))

    df["cleaned_content"] = cleaned
    df = df[df["cleaned_content"].str.strip() != ""]
    df = df.reset_index(drop=True)
    return df


if __name__ == "__main__":
    raw_df = load_raw_dataset()
    print("Loaded raw training dataset:", raw_df.shape)

    cleaned_df = preprocess(raw_df)
    print("Cleaned training dataset:", cleaned_df.shape)

    out_path = save_cleaned_dataset(cleaned_df)
    print("Saved:", out_path)
