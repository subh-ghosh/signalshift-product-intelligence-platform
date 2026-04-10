import pandas as pd
import time
import os
import joblib
from bertopic import BERTopic
from sentence_transformers import SentenceTransformer
from umap import UMAP
from hdbscan import HDBSCAN
from sklearn.feature_extraction.text import CountVectorizer

def run_bertopic_benchmark():
    print("--- ARCHITECTURE EVOLUTION BENCHMARK (NMF vs BERTopic) ---\n")
    
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    # 1. Load Data
    print("Loading recent dataset...")
    df = pd.read_csv(os.path.join(BASE_DIR, "data/processed/cleaned_reviews.csv"))
    
    # Take a 3k sample of Negative Reviews perfectly matched for issue tracking
    sample_df = df[df["score"] <= 2].head(3000).copy()
    reviews = sample_df["cleaned_content"].astype(str).tolist()
    
    print(f"Sample size: {len(reviews)} negative reviews.")
    
    # 2. Benchmark NMF V4.1 (Current Elite Baseline)
    print("\n[V4.1] Running Current NMF Engine...")
    start_time = time.time()
    
    nmf_model = joblib.load(os.path.join(BASE_DIR, "models/nmf_model.joblib"))
    nmf_vectorizer = joblib.load(os.path.join(BASE_DIR, "models/nmf_vectorizer.joblib"))
    
    X_nmf = nmf_vectorizer.transform(reviews)
    W_nmf = nmf_model.transform(X_nmf)
    
    nmf_topics = [int(w.argmax()) if w.max() >= 0.05 else -1 for w in W_nmf]
    nmf_outliers = nmf_topics.count(-1) / len(reviews)
    nmf_time = time.time() - start_time
    
    print(f"NMF Outlier/Noise Ratio: {nmf_outliers:.1%}")
    print(f"NMF Inference Time: {nmf_time:.2f}s")

    # 3. Benchmark BERTopic (Phase 15 Candidate)
    print("\n[V5.0] Running Experimental BERTopic Engine...")
    start_time = time.time()
    
    # We use MiniLM (fastest encoder), UMAP (dimension reduction), HDBSCAN (density clustering)
    # n_neighbors=15 is strict, min_cluster_size=20 prevents hyper-fragmentation
    embedding_model = SentenceTransformer('all-MiniLM-L6-v2', device='cpu') # Force CPU for local dev
    umap_model = UMAP(n_neighbors=15, n_components=5, min_dist=0.0, metric='cosine', random_state=42)
    hdbscan_model = HDBSCAN(min_cluster_size=20, metric='euclidean', cluster_selection_method='eom', prediction_data=True)
    vectorizer_model = CountVectorizer(stop_words="english")
    
    topic_model = BERTopic(
        embedding_model=embedding_model,
        umap_model=umap_model,
        hdbscan_model=hdbscan_model,
        vectorizer_model=vectorizer_model,
        verbose=True
    )
    
    topics, probs = topic_model.fit_transform(reviews)
    
    bertopic_outliers = topics.count(-1) / len(reviews)
    bertopic_time = time.time() - start_time
    bertopic_topic_count = len(set(topics)) - (1 if -1 in topics else 0)
    
    print(f"BERTopic Discovered Concepts: {bertopic_topic_count}")
    print(f"BERTopic Outlier/Noise Ratio: {bertopic_outliers:.1%}")
    print(f"BERTopic Training/Inference Time: {bertopic_time:.2f}s")
    
    # 4. Generate Report
    report = f"""# SignalShift Phase 15: Architecture Evolution Benchmark

## Objective
Evaluate the migration from linear mathematical clustering (**NMF**) to state-of-the-art transformer clustering (**BERTopic**) for the core "Top Issues" engine.

## Dataset
- **Size**: {len(reviews)} High-Signal Negative Reviews (Score <= 2)

## Benchmark Results

| Metric | V4.1 NMF (Current Elite) | V5.0 BERTopic (Experimental) |
| :--- | :--- | :--- |
| **Core AI Model** | Linear Algebra (TF-IDF Matrices) | Semantic Transformers (MiniLM-L6) + UMAP + HDBSCAN |
| **Target Clusters** | Forced (n=30) | Auto-Detected ({bertopic_topic_count}) |
| **Outlier Ratio** | {nmf_outliers:.1%} (Dropped via threshold) | {bertopic_outliers:.1%} (HDBSCAN Noise Bin) |
| **Total Inference Time** | {nmf_time:.2f}s | {bertopic_time:.2f}s (Heavy computation) |

### Qualitative Analysis
*(To be filled after manual review of topic output)*
- **BERTopic Top 3 Issues**:
{chr(10).join([f"  - Topic {i}: " + "_".join([word[0] for word in topic_model.get_topic(i)[:5]]) for i in range(min(3, bertopic_topic_count))])}

## Verdict
*Pending user review of the topic cohesion vs processing time trade-off.*
"""
    
    out_dir = os.path.join(BASE_DIR, "research_docs/summaries")
    os.makedirs(out_dir, exist_ok=True)
    report_path = os.path.join(out_dir, "BERTopic_Benchmark_Report.md")
    
    with open(report_path, "w") as f:
        f.write(report)
        
    print(f"\nBenchmark complete! Initial report generated at: {report_path}")
    
if __name__ == "__main__":
    run_bertopic_benchmark()
