"""Step 04: Create semantic issue taxonomy embeddings.

This produces a lightweight artifact used for semantic issue labeling.
"""

from __future__ import annotations

import os
import pickle
import sys

import numpy as np
from sentence_transformers import SentenceTransformer


# Ensure `backend/` is on sys.path so `import ml.*` works when running as a script.
BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from ml.core.issue_labeler import ISSUE_TAXONOMY


MODEL_PATH = os.path.join(BACKEND_DIR, "models", "topic_embeddings.pkl")


def build_issue_embedding_artifacts() -> dict:
    topics: list[str] = []
    embeddings: list[np.ndarray] = []

    model = SentenceTransformer("all-MiniLM-L6-v2", device="cpu")
    for label, descriptions in ISSUE_TAXONOMY:
        desc_embeddings = model.encode(descriptions)
        centroid = np.mean(desc_embeddings, axis=0)
        centroid /= (np.linalg.norm(centroid) + 1e-8)
        topics.append(label)
        embeddings.append(centroid)

    return {"topics": topics, "embeddings": np.array(embeddings)}


def save_issue_embeddings(data: dict, path: str = MODEL_PATH) -> str:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as handle:
        pickle.dump(data, handle)
    return path


if __name__ == "__main__":
    artifacts = build_issue_embedding_artifacts()
    out_path = save_issue_embeddings(artifacts)
    print("Saved:", out_path)
import os
import pickle
import sys

import numpy as np
from sentence_transformers import SentenceTransformer

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.issue_labeler import ISSUE_TAXONOMY


BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MODEL_PATH = os.path.join(BASE_DIR, "models", "topic_embeddings.pkl")


def build_issue_embedding_artifacts():
    print("Loading semantic issue taxonomy...")

    topics = []
    embeddings = []

    model = SentenceTransformer("all-MiniLM-L6-v2", device="cpu")

    for label, descriptions in ISSUE_TAXONOMY:
        desc_embeddings = model.encode(descriptions)
        centroid = np.mean(desc_embeddings, axis=0)
        centroid /= np.linalg.norm(centroid)
        topics.append(label)
        embeddings.append(centroid)

    return {
        "topics": topics,
        "embeddings": np.array(embeddings),
    }


def save_issue_embeddings(data, path=MODEL_PATH):
    print("Saving semantic issue embeddings...")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as handle:
        pickle.dump(data, handle)
    print("Issue embeddings created successfully.")


if __name__ == "__main__":
    save_issue_embeddings(build_issue_embedding_artifacts())
