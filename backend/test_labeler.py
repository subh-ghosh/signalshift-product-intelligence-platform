import pandas as pd
import os

from app.services.paths import processed_data_dir

# Define the problematic generic words to ignore in labels
# These are words often found in clusters but provide zero value for a title
STOP_LABELS = {
    "app", "netflix", "good", "bad", "great", "excellent", "nice", "ok", "awesome", 
    "hai", "hua", "hi", "bhai", "yaar", "kya", "ko", "ki", "he", "it", "very", "is",
    "application", "working", "work", "use", "using", "like", "love", "really",
    "amazing", "super", "useful", "best", "worst", "better", "quality"
}

def improved_labeler(keywords_str):
    if not isinstance(keywords_str, str) or not keywords_str.strip():
        return "General Issue"
    
    words = [w.strip().lower() for w in keywords_str.split(",")]
    # Filter out stop labels
    filtered = [w for w in words if w not in STOP_LABELS]
    
    # If we have enough specific words, use them
    if len(filtered) >= 2:
        return f"{filtered[0].capitalize()} {filtered[1].capitalize()} Task"
    elif len(filtered) == 1:
        return f"{filtered[0].capitalize()} Related Problems"
    
    # Fallback to original if we filtered everything out
    return f"{words[0].capitalize()} System Feedback"

# Test on actual data
DATA_PATH = os.path.join(processed_data_dir(), "topic_analysis.csv")
if os.path.exists(DATA_PATH):
    df = pd.read_csv(DATA_PATH)
    print("Testing Improved Labeler on existing topics:\n")
    for idx, row in df.iterrows():
        old_words = [w.strip() for w in str(row["keywords"]).split(",")]
        old_label = f"{old_words[0].capitalize()} {old_words[1].capitalize()} Issues" if len(old_words) >= 2 else f"{old_words[0].capitalize()} Issues"
        new_label = improved_labeler(row["keywords"])
        print(f"ID {idx}:")
        print(f"  Keywords: {row['keywords']}")
        print(f"  Old Label: {old_label}")
        print(f"  New Label: {new_label}")
        print("-" * 30)
else:
    print("topic_analysis.csv not found. Please run the sync first.")
