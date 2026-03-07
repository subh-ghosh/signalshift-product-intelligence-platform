def generate_issue_label(keywords: str) -> str:
    """
    Auto-generates a clean dashboard title by filtering out generic noise 
    and selecting the most descriptive technical/business terms.
    """
    if not isinstance(keywords, str) or not keywords.strip():
        return "General Platform Feedback"

    # Keywords from LDA/NMF come in as "word1, word2, word3"
    words = [w.strip().lower() for w in keywords.split(",")]
    
    # Noise words that clutter titles but add no value
    STOP_LABELS = {
        "app", "netflix", "good", "bad", "great", "excellent", "nice", "ok", "awesome", 
        "hai", "hua", "hi", "bhai", "yaar", "kya", "ko", "ki", "he", "it", "very", "is",
        "application", "working", "work", "use", "using", "like", "love", "really",
        "amazing", "super", "useful", "best", "worst", "better", "quality", "time", "hai",
        "just", "don", "t", "s", "can", "ve", "re", "m", "want", "let", "the", "an", "this"
    }
    
    # Filter the keywords
    filtered = [w for w in words if w not in STOP_LABELS]
    
    if len(filtered) >= 2:
        # Example: "buffering", "login" -> "Buffering & Login Issues"
        return f"{filtered[0].capitalize()} & {filtered[1].capitalize()} Issues"
    elif len(filtered) == 1:
        # Example: "payment" -> "Payment Related Issues"
        return f"{filtered[0].capitalize()} Related Issues"
    
    # Absolute fallback using original words if everything was filtered
    primary = words[0].capitalize() if words else "System"
    return f"{primary} Performance Feedback"