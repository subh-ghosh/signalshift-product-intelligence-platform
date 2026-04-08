"""Load/compute semantic taxonomy embeddings for issue classification."""

from __future__ import annotations

import os
import pickle

import numpy as np

from ml.core.issue_labeler import _build_taxonomy_embeddings
import ml.core.issue_labeler as issue_labeler_module


def load_taxonomy_embeddings(model_dir: str, *, encoder):
    """Load taxonomy label embeddings from disk, or compute in-memory fallback.

    Returns:
        (labels, embedding_matrix)
    """
    embeddings_path = os.path.join(model_dir, "topic_embeddings.pkl")
    if os.path.exists(embeddings_path):
        with open(embeddings_path, "rb") as handle:
            data = pickle.load(handle)
        labels = data.get("topics", [])
        embeddings = np.array(data.get("embeddings", []))
        if labels and embeddings.size:
            return labels, embeddings

    # Fallback: compute from ISSUE_TAXONOMY via ml.core.issue_labeler
    issue_labeler_module._encoder = encoder
    _build_taxonomy_embeddings()
    return issue_labeler_module._taxonomy_labels, issue_labeler_module._taxonomy_embeddings
