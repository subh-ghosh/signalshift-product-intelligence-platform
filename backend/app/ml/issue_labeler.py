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
    
    # ELITE SEMANTIC MAPPING (Phase 12)
    # Map common technical words to professional business categories
    SEMANTIC_MAP = {
        "buffer": "Playback",
        "playback": "Streaming",
        "slow": "Performance",
        "crash": "Stability",
        "freeze": "Interface",
        "login": "Auth/Login",
        "account": "Profile Management",
        "payment": "Billing",
        "subscription": "Subscription Plan",
        "money": "Payments",
        "movie": "Content Library",
        "show": "Shows",
        "song": "Audio",
        "music": "Music Player",
        "download": "Offline Experience",
        "internet": "Connectivity",
        "wifi": "Network Stability",
        "cancel": "Churn Risk",
        "update": "Maintenance/Version",
        "ad": "Ad Experience",
        "advertisement": "Monetization Flow",
        "message": "Communications",
        "send": "Messaging",
        "receive": "Incoming Alerts",
        "notification": "Notifications"
    }

    # Filter the keywords
    filtered = [w for w in words if w not in STOP_LABELS]
    
    # Use Semantic Mapping for the labels if possible
    final_topics = []
    for w in filtered[:2]: # Take up to 2
        label = SEMANTIC_MAP.get(w, w.capitalize())
        if label not in final_topics:
            final_topics.append(label)

    if len(final_topics) >= 2:
        # Example: "Playback" & "Stability" -> "Playback & Stability Issues"
        return f"{final_topics[0]} & {final_topics[1]} Issues"
    elif len(final_topics) == 1:
        # Example: "Billing" -> "Billing Related Issues"
        return f"{final_topics[0]} Related Issues"
    
    # Absolute fallback using original words if everything was filtered
    primary = words[0].capitalize() if words else "System"
    return f"{primary} Performance Feedback"