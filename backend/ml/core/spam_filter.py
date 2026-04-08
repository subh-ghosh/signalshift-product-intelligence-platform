import re
from langdetect import detect, LangDetectException, DetectorFactory


# Make langdetect deterministic across runs
DetectorFactory.seed = 0


_USELESS_PATTERNS = [
    re.compile(r"^very good( app)?\.?$"),
    re.compile(r"^very bad( app)?\.?$"),
    re.compile(r"^(really )?nice app\.?$"),
    re.compile(r"^worst app ever\.?$"),
    re.compile(r"^i love this app\.?$"),
    re.compile(r"^worse than before\.?$"),
]

_EXCESS_CHAR_REPEAT_RE = re.compile(r"(.)\1{4,}")

def is_valid_review(text: str) -> bool:
    """
    Data Quality Filter: Returns True if the review is high-quality and should be 
    included in topic modeling. Returns False if it is spam, too short, or junk.
    """
    if not isinstance(text, str):
        return False
        
    text = text.strip()
    
    # 0. Language Barrier (Phase 14.3)
    # Ensure only English reviews enter the model to prevent TF-IDF fracturing
    try:
        if detect(text) != 'en':
            return False
    except LangDetectException:
        # If language detector fails (usually due to no recognizable words), drop it
        return False
        
    # 1. Length Heuristics
    if len(text) < 15: # Too short to establish a meaningful topic cluster
        return False
        
    words = text.split()
    if len(words) < 3: # Must contain at least a simple subject-verb-object thought
        return False

    # 2. Generic/Useless Single-Thought Filters
    # These often pass length checks but add 0 value to the mathematical clusters
    text_lower = text.lower()
    for pattern in _USELESS_PATTERNS:
        if pattern.match(text_lower):
            return False

    # 3. Entropy / Repetitiveness Check (Keyboard Smashes)
    # E.g., "aaaaaaaaa", "hfjdkfhdjkf", "good good good good"
    
    # Check for excessive character repetition (e.g., "woooooooow")
    if _EXCESS_CHAR_REPEAT_RE.search(text_lower):
        return False
        
    # Check for excessive word repetition 
    # If the same word makes up more than 50% of a review, it's likely spam
    if len(words) > 4:
        word_counts = {}
        for w in words:
            word_counts[w.lower()] = word_counts.get(w.lower(), 0) + 1
            
        max_word_ratio = max(word_counts.values()) / len(words)
        if max_word_ratio > 0.5:
            return False

    return True

