import re
import spacy

# Load spaCy model once, aggressively disabling heavy pipelines for speed
nlp = spacy.load("en_core_web_sm", disable=["ner", "parser", "textcat", "custom"])


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
    text = re.sub(r"http\S+|www\S+", "", text)

    # Remove special characters and numbers
    text = re.sub(r"[^a-zA-Z\s]", "", text)

    doc = nlp(text)

    tokens = []

    for token in doc:
        if not token.is_stop and not token.is_punct and not token.is_space:
            tokens.append(token.lemma_)

    return " ".join(tokens)