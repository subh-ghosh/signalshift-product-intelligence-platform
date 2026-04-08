import re
from functools import lru_cache


_URL_RE = re.compile(r"http\S+|www\S+")
_NON_ALPHA_RE = re.compile(r"[^a-zA-Z\s]")


@lru_cache(maxsize=1)
def _get_nlp():
    """Return a spaCy NLP pipeline if available.

    Tries `en_core_web_sm` first (best quality). If the model isn't installed,
    falls back to `spacy.blank('en')` so the backend can still run.
    """
    try:
        import spacy
    except Exception:
        return None

    try:
        # Disable heavier components for speed.
        return spacy.load("en_core_web_sm", disable=["ner", "parser", "textcat"])
    except Exception:
        try:
            return spacy.blank("en")
        except Exception:
            return None


def clean_text(text) -> str:
    """
    Clean and normalize text for ML processing. Handles NaN/float inputs.
    """
    if not isinstance(text, str):
        text = str(text) if text is not None else ""
    
    if not text.strip():
        return ""

    text = text.lower()

    # Remove URLs
    text = _URL_RE.sub("", text)

    # Remove special characters and numbers
    text = _NON_ALPHA_RE.sub("", text)

    nlp = _get_nlp()
    if nlp is None:
        # Minimal fallback: collapse whitespace and return.
        return " ".join(text.split())

    doc = nlp(text)

    tokens = []

    for token in doc:
        if not token.is_stop and not token.is_punct and not token.is_space:
            lemma = getattr(token, "lemma_", "") or token.text
            tokens.append(lemma)

    return " ".join(tokens)