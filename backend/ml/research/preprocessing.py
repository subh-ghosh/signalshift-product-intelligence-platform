import pandas as pd

from text_cleaner import clean_text


def load_and_clean_data(path: str):

    df = pd.read_csv(path)

    # Remove missing reviews
    df = df.dropna(subset=["content"])

    # Remove empty strings
    df = df[df["content"].str.strip() != ""]

    df = df.reset_index(drop=True)

    return df


if __name__ == "__main__":

    df = load_and_clean_data("../../data/raw/reviews.csv")

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

    df.to_csv("../../data/processed/cleaned_reviews.csv", index=False)

    print("Saved cleaned dataset.")