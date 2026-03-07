import sys
import os
import pandas as pd
# Add current directory to path to allow direct script execution
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from text_cleaner import clean_text

# Robust path detection
BASE_DIR = "/media/subh/Shared Storage/signalshift/backend"
DATA_PATH = os.path.join(BASE_DIR, "data/processed/cleaned_reviews.csv")

print("Step 10: Aspect-Based Sentiment Analysis (ABSA) Prototype")
print("Goal: Identify the 'Reason' behind the sentiment.")

# 1. Define Business Aspects and associated Keywords
# This is a "Heuristic-Seed" approach, common in professional NLP
ASPECTS = {
    "Performance/Technical": ["crash", "lag", "buffer", "freeze", "slow", "loading", "error", "bug"],
    "Content/Library": ["movie", "show", "series", "selection", "episodes", "watch", "boring"],
    "UI/UX Experience": ["interface", "design", "navigation", "button", "screen", "search", "easy"],
    "Pricing/Subscription": ["expensive", "price", "money", "subscription", "plan", "cancel", "worth"],
}

def analyze_aspects(text):
    text = text.lower()
    results = {}
    
    for aspect, keywords in ASPECTS.items():
        # Count keyword hits
        hits = [word for word in keywords if word in text]
        if hits:
            results[aspect] = hits
            
    return results

# 2. Test on Samples
print("\n[T] Running Aspect Detection on Sample Reviews...")

sample_reviews = [
    "The movies are great but the app keeps crashing on my phone.",
    "Way too expensive for such a small selection of shows.",
    "Very easy to use interface, I love the new search button!",
    "It buffers for 20 minutes before every episode, fix this bug."
]

for review in sample_reviews:
    detected = analyze_aspects(review)
    print(f"\nReview: \"{review}\"")
    if detected:
        for aspect, hits in detected.items():
            print(f"  -> ASPECT: {aspect} (Triggers: {hits})")
    else:
        print("  -> ASPECT: General/Uncategorized")

# 3. Research Path
print("\n--- Why this is 'Mastery' Level ---")
print("1. Granularity: Instead of a flat 'Total Negative' count, you can now tell a company:")
print("   '80% of your negative reviews are due to Performance issues.'")
print("2. Actionability: This directly feeds into our B2B Ticketing logic.")
print("   High-Impact 'Technical' issues can automatically create High-Priority Engineering tickets.")
