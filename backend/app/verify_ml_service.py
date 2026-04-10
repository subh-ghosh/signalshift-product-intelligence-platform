import sys
import os

# Robust path detection
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)

from app.services.ml_service import MLService

print("Verifying Production MLService Upgrade...")

# 1. Initialize Service
service = MLService()

# 2. Test Review with clear aspects
test_review = "The app keeps crashing and it is way too expensive for what it offers."
print(f"\nTesting Review: \"{test_review}\"")

result = service.analyze_review(test_review)

print("\n--- Analysis Result ---")
print(f"Sentiment: {result['sentiment']}")
print(f"Topic Keywords: {result['topic_keywords']}")
print(f"Detected Aspects: {result['aspects']}")

# 3. Verify ABSA Categories
expected_aspects = ["Performance/Technical", "Pricing/Subscription"]
all_found = all(a in result['aspects'] for a in expected_aspects)

if all_found:
    print("\n✅ Verification SUCCESS: ABSA logic correctly identified business categories.")
else:
    print("\n❌ Verification FAILED: ABSA logic missing or incomplete.")
