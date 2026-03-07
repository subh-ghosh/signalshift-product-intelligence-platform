import re

def is_valid_review(text: str) -> bool:
    """
    Data Quality Filter: Returns True if the review is high-quality and should be 
    included in topic modeling. Returns False if it is spam, too short, or junk.
    """
    if not isinstance(text, str):
        return False
        
    text = text.strip()
    
    # 1. Length Heuristics
    if len(text) < 15: # Too short to establish a meaningful topic cluster
        return False
        
    words = text.split()
    if len(words) < 3: # Must contain at least a simple subject-verb-object thought
        return False

    # 2. Generic/Useless Single-Thought Filters
    # These often pass length checks but add 0 value to the mathematical clusters
    useless_patterns = [
        r"^very good( app)?\.?$",
        r"^very bad( app)?\.?$",
        r"^(really )?nice app\.?$",
        r"^worst app ever\.?$",
        r"^i love this app\.?$",
        r"^worse than before\.?$"
    ]
    text_lower = text.lower()
    for p in useless_patterns:
        if re.match(p, text_lower):
            return False

    # 3. Entropy / Repetitiveness Check (Keyboard Smashes)
    # E.g., "aaaaaaaaa", "hfjdkfhdjkf", "good good good good"
    
    # Check for excessive character repetition (e.g., "woooooooow")
    if re.search(r"(.)\1{4,}", text_lower): 
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

