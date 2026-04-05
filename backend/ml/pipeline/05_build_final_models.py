import pandas as pd
import os
import importlib.util

# Robust path detection
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA_PATH = os.path.join(BASE_DIR, "data", "training", "processed", "cleaned_all_combined.csv")
MODEL_DIR = os.path.join(BASE_DIR, "models")
STEP_03_PATH = os.path.join(os.path.dirname(__file__), "03_train_sentiment_model.py")
STEP_04_PATH = os.path.join(os.path.dirname(__file__), "04_create_issue_embeddings.py")

spec = importlib.util.spec_from_file_location("step_03_train_sentiment_model", STEP_03_PATH)
step_03 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(step_03)

spec = importlib.util.spec_from_file_location("step_04_create_issue_embeddings", STEP_04_PATH)
step_04 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(step_04)

print("Step 5: Building Final Research-Aligned Models")
print("Goal: save the final sentiment model and semantic issue embeddings.")
print("Training mode only: uploaded CSV files must never be used to build models.")

# 1. Load Full Data
df = step_03.load_cleaned_dataset(DATA_PATH)

# 2. Train Optimized Sentiment Pipeline by reusing Step 03 logic
print("\n[1/2] Training Production Sentiment Pipeline...")
vectorizer, model, _ = step_03.train_sentiment_pipeline(
    df,
    test_size=0,
    model_kwargs={"class_weight": "balanced", "C": 1.0},
)

# 3. Build semantic issue taxonomy embeddings
print("\n[2/2] Building Semantic Issue Embeddings...")
issue_embedding_data = step_04.build_issue_embedding_artifacts()

# 4. Save Final Artifacts
print("\n[S] Saving production models to /models directory...")
step_03.save_sentiment_artifacts(vectorizer, model, MODEL_DIR)
step_04.save_issue_embeddings(issue_embedding_data)

print("\nSuccess! Systems are ready for production upgrade.")
