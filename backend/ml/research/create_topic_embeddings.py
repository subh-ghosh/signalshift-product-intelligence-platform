import pandas as pd
import pickle
from sentence_transformers import SentenceTransformer


print("Loading topic insights...")

df = pd.read_csv("data/processed/topic_analysis.csv")

topics = df["keywords"].astype(str).tolist()

print("Topics:", topics)


print("Loading embedding model...")

model = SentenceTransformer("all-MiniLM-L6-v2")


print("Creating embeddings...")

topic_embeddings = model.encode(topics)


data = {
    "topics": topics,
    "embeddings": topic_embeddings
}


print("Saving embeddings...")

with open("models/topic_embeddings.pkl", "wb") as f:
    pickle.dump(data, f)


print("Topic embeddings created successfully.")