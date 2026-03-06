def generate_issue_label(keywords: str) -> str:
    """
    Auto-generates a clean dashboard title based directly on the raw cluster keywords.
    This approach is 100% dynamic and auto-generates the title without using any 
    hardcoded candidate lists or external APIs.
    """
    if not isinstance(keywords, str) or not keywords.strip():
        return "Unknown Issue"

    # The keywords come in as a comma-separated string: "video, playback, buffer"
    words = [w.strip() for w in keywords.split(",")]
    
    # We take the top 2 most mathematically important keywords from the cluster
    if len(words) >= 2:
        # Example: "video", "playback" -> "Video Playback Issues"
        return f"{words[0].capitalize()} {words[1].capitalize()} Issues"
    elif len(words) == 1:
        # Example: "video" -> "Video Issues"
        return f"{words[0].capitalize()} Issues"
    else:
        return "General Platform Complaints"