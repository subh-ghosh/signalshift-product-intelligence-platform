import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pandas as pd

from core.text_cleaner import clean_text


BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RAW_DATA_PATH = os.path.join(BASE_DIR, "data", "training", "raw", "all_combined.csv")
PROCESSED_DATA_PATH = os.path.join(BASE_DIR, "data", "training", "processed", "cleaned_all_combined.csv")


def load_and_clean_data(path: str):

    df = pd.read_csv(path)

    # Remove missing reviews
    df = df.dropna(subset=["content"])

    # Remove empty strings
    df = df[df["content"].str.strip() != ""]

    df = df.reset_index(drop=True)

    return df


if __name__ == "__main__":

    df = load_and_clean_data(RAW_DATA_PATH)

    print("Cleaning full dataset...")

    total_rows = len(df)

    cleaned_texts = []

    for i, text in enumerate(df["content"]):

        cleaned = clean_text(text)

        cleaned_texts.append(cleaned)

        if (i + 1) % 5000 == 0:
            progress = ((i + 1) / total_rows) * 100
            print(f"Processed {i + 1}/{total_rows} rows ({progress:.2f}%)")

    df["cleaned_content"] = cleaned_texts

    # Remove rows that became empty after cleaning
    df = df[df["cleaned_content"].str.strip() != ""]

    df = df.dropna(subset=["cleaned_content"])

    df["cleaned_content"] = df["cleaned_content"].astype(str)

    df = df.reset_index(drop=True)

    print("Final dataset shape:", df.shape)

    os.makedirs(os.path.dirname(PROCESSED_DATA_PATH), exist_ok=True)
    df.to_csv(PROCESSED_DATA_PATH, index=False)

    print("Saved cleaned dataset.")
