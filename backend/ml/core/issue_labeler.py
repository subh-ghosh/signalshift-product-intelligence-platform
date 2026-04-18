"""
SignalShift Semantic Issue Labeler — Phase 22
=============================================
Replaces the old rule-based keyword concatenator with a zero-shot
semantic classifier using MiniLM cosine similarity.

The ISSUE_TAXONOMY is deliberately app-agnostic so SignalShift 
can scale to any mobile/SaaS/streaming application without retraining.
"""

import numpy as np

# ─────────────────────────────────────────────────────────────────────────────
# UNIVERSAL APP-AGNOSTIC ISSUE TAXONOMY
# Each entry: (canonical_label, list of natural-language description phrases)
# The descriptions are what the model uses to compute embeddings, NOT regex.
# To extend for a new app or vertical, add/edit entries in this list.
# ─────────────────────────────────────────────────────────────────────────────
ISSUE_TAXONOMY = [
    (
        "Subscription & Billing",
        [
            "payment failed auto charge subscription money",
            "cancel subscription refund billing plan pay",
            "charged money price expensive pay for feature",
            "forced to pay subscription auto-renew daily monthly fee",
            "pay money watch free premium upsell",
        ]
    ),
    (
        "App Crash & Launch Failure",
        [
            "app crashes keeps closing not opening",
            "cannot open app stuck loading screen",
            "app won't launch keeps crashing",
            "force close reinstall uninstall freezing",
        ]
    ),
    (
        "Video & Streaming Playback",
        [
            "video buffering not playing loading slowly",
            "streaming quality bad pixelated lag",
            "playback error can't watch video content",
            "video freezes keeps buffering poor quality",
        ]
    ),
    (
        "Account & Login",
        [
            "login sign in problem account access",
            "password reset forgot email cannot login",
            "account blocked banned suspended unable access",
            "google facebook sign in login failed",
        ]
    ),
    (
        "Customer Support",
        [
            "support team unhelpful no response",
            "customer service terrible experience bad attitude",
            "no help from support ticket ignored",
            "useless support waste of time response",
        ]
    ),
    (
        "Performance & Speed",
        [
            "app slow lagging unresponsive freezing",
            "takes long time load performance issue",
            "sluggish response lag spike high memory",
            "app not responding hanging slow startup",
        ]
    ),
    (
        "Content & Features",
        [
            "missing feature content not available library",
            "removed content show movie not found",
            "feature request missing functionality wish list",
            "content library quality selection poor",
        ]
    ),
    (
        "Notifications & Spam",
        [
            "too many notifications spam unwanted alerts",
            "notification settings don't work constant alerts",
            "spam messages annoying push notifications",
            "notification permission opt-out can't disable",
        ]
    ),
    (
        "UI & Navigation",
        [
            "confusing navigation interface design bad",
            "hard to find menu button location unclear",
            "user interface ugly layout poor design",
            "search not working result wrong filter broken",
        ]
    ),
    (
        "Bugs & Technical Errors",
        [
            "bug error glitch technical problem",
            "app not working broken feature error code",
            "software bug unexpected behavior malfunction",
            "error message keeps appearing not fixed",
        ]
    ),
    (
        "Privacy & Security",
        [
            "data privacy security personal information",
            "account hacked unauthorized access breach",
            "privacy settings permissions data collection concern",
            "security vulnerability exposed data leak",
        ]
    ),
    (
        "Download & Offline",
        [
            "download not working offline mode saves",
            "cannot download content for offline use",
            "download fails incomplete file storage",
            "offline content expired removed unavailable",
        ]
    ),
]

# Pre-computed embeddings (populated lazily on first call)
_taxonomy_embeddings = None
_taxonomy_labels = None
_encoder = None


def _get_encoder():
    """Lazily import and return the SentenceTransformer encoder."""
    global _encoder
    if _encoder is None:
        from sentence_transformers import SentenceTransformer
        _encoder = SentenceTransformer('all-MiniLM-L6-v2', device='cpu')
    return _encoder


def _build_taxonomy_embeddings():
    """
    Pre-compute the mean embedding for each canonical category.
    This is called once and cached for the process lifetime.
    """
    global _taxonomy_embeddings, _taxonomy_labels
    if _taxonomy_embeddings is not None:
        return

    encoder = _get_encoder()
    labels = []
    embeddings = []

    for label, descriptions in ISSUE_TAXONOMY:
        desc_embeddings = encoder.encode(descriptions)
        # Mean-pool the 2-4 description embeddings for a robust centroid
        centroid = np.mean(desc_embeddings, axis=0)
        centroid /= np.linalg.norm(centroid)  # L2-normalize
        labels.append(label)
        embeddings.append(centroid)

    _taxonomy_labels = labels
    _taxonomy_embeddings = np.array(embeddings)  # (n_categories, 384)


def generate_issue_label(keywords: str, encoder=None) -> str:
    """
    Semantic zero-shot issue labeler.

    Replaces the old rule-based keyword-concatenation approach.
    
    Args:
        keywords: Comma-separated NMF top keywords for a topic cluster.
                  e.g. "open, viber, close, messenger, browser"
        encoder:  Optional pre-loaded SentenceTransformer to avoid
                  re-loading the model (pass ml_service.encoder for speed).
    
    Returns:
        A canonical, app-agnostic issue label from ISSUE_TAXONOMY.
        e.g. "App Crash & Launch Failure"
    """
    if not isinstance(keywords, str) or not keywords.strip():
        return "General App Feedback"

    # Use supplied encoder (from ml_service.encoder) to skip re-loading.
    # If encoder instance changes (e.g., base -> fine-tuned), rebuild taxonomy centroids
    # so query and taxonomy vectors live in the same embedding space.
    global _encoder, _taxonomy_embeddings, _taxonomy_labels
    if encoder is not None and _encoder is not encoder:
        _encoder = encoder
        _taxonomy_embeddings = None
        _taxonomy_labels = None

    # Build taxonomy embeddings lazily (or rebuild if encoder changed)
    _build_taxonomy_embeddings()

    enc = _get_encoder()

    # Encode the raw NMF keyword string as-is
    query_embedding = enc.encode([keywords])[0]
    query_embedding = query_embedding / np.linalg.norm(query_embedding)

    # Cosine similarity = dot product of L2-normalized vectors
    similarities = _taxonomy_embeddings.dot(query_embedding)
    best_idx = int(np.argmax(similarities))
    best_score = float(similarities[best_idx])

    # Fallback if nothing is confidently matched
    if best_score < 0.15:
        return "General App Feedback"

    return _taxonomy_labels[best_idx]