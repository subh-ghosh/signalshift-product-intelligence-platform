import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer

# Load cleaned dataset
df = pd.read_csv("../../data/processed/cleaned_reviews.csv")

print("Dataset shape:", df.shape)

# Safety check
df = df.dropna(subset=["cleaned_content"])
df["cleaned_content"] = df["cleaned_content"].astype(str)

# Initialize TF-IDF vectorizer
vectorizer = TfidfVectorizer(
    max_features=10000,
    ngram_range=(1, 2)
)

print("Creating TF-IDF features...")

X = vectorizer.fit_transform(df["cleaned_content"])

print("TF-IDF matrix shape:", X.shape)