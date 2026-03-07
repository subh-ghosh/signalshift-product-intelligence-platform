from bertopic import BERTopic
from sentence_transformers import SentenceTransformer
from umap import UMAP
from hdbscan import HDBSCAN
from sklearn.feature_extraction.text import CountVectorizer
from app.ml.text_cleaner import clean_text
import pandas as pd
import numpy as np

class DynamicClusteringService:
    """
    Phase 15: State-of-the-Art Embedding Clustering
    Replaces static NMF with Dynamic HDBSCAN-based clustering.
    Solves: Dynamic Cluster Sizing, Semantic Embeddings, Hierarchical Topics, Dynamic Stopwords.
    """
    def __init__(self):
        print("[HDBSCAN/BERTopic] Initializing State-of-the-Art Embedding Pipeline...")
        
        # 1. Semantic Embedding Model (Forcing CPU to prevent CUDA capability errors like sm_61)
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2', device='cpu')

        # 2. UMAP - Dimensionality Reduction
        # Reduces the 384-dimensional embeddings down to 5D, which makes geometric clustering much more accurate.
        self.umap_model = UMAP(n_neighbors=15, n_components=5, min_dist=0.0, metric='cosine', random_state=42)

        # 3. HDBSCAN - Density-Based Clustering
        # Unlike NMF, this DYNAMICALLY finds the right number of topics and naturally filters out outliers (Topic -1)
        self.hdbscan_model = HDBSCAN(min_cluster_size=15, metric='euclidean', cluster_selection_method='eom', prediction_data=True)

        # 4. Dynamic Stopwords via c-TF-IDF Vectorizer
        # Extracts keywords natively while neutralizing background noise specific to the dataset.
        self.vectorizer_model = CountVectorizer(stop_words="english", ngram_range=(1, 2))

        # Core Pipeline
        self.topic_model = BERTopic(
            embedding_model=self.embedding_model,
            umap_model=self.umap_model,
            hdbscan_model=self.hdbscan_model,
            vectorizer_model=self.vectorizer_model,
            language="english",
            calculate_probabilities=False
        )

    def extract_dynamic_topics(self, reviews: list[str], progress_dict=None):
        """
        Runs the full BERTopic pipeline strictly on the provided list of text.
        Returns the processed topic cache mapped out.
        """
        import time
        if len(reviews) < 50:
            print("[Warning] Dataset too small for reliable HDBSCAN density clustering.")
            return []

        print(f"-> Extracting dense embeddings for {len(reviews)} reviews...")
        
        # 1. Manually encode so we can stream progress to the UI!
        embeddings = []
        batch_size = 500
        total = len(reviews)
        start_time = time.time()
        
        for i in range(0, total, batch_size):
            batch = reviews[i:i + batch_size]
            batch_emb = self.embedding_model.encode(batch, show_progress_bar=False)
            embeddings.extend(batch_emb)
            
            if progress_dict is not None:
                processed = min(i + batch_size, total)
                elapsed = time.time() - start_time
                speed = processed / elapsed if elapsed > 0 else 0
                eta = int((total - processed) / speed) if speed > 0 else 0
                
                progress_dict["processed"] = processed
                progress_dict["total"] = total
                progress_dict["status"] = f"Translating semantics (Embeddings)... {processed}/{total}"
                progress_dict["eta_seconds"] = eta
                
        # 2. Fit topic model geometrically
        if progress_dict is not None:
            progress_dict["processed"] = total
            progress_dict["status"] = "Clustering geometry (UMAP & HDBSCAN)... this takes 1-2 minutes"
            progress_dict["eta_seconds"] = 0
            
        import numpy as np
        embeddings = np.array(embeddings)
        topics, _ = self.topic_model.fit_transform(reviews, embeddings=embeddings)

        # Build Hierarchical topics
        # We can dynamically roll up clusters
        try:
             hierarchical_topics = self.topic_model.hierarchical_topics(reviews)
             topic_tree = self.topic_model.get_topic_tree(hierarchical_topics)
             print(f"Hierarchical Structure Discovered:\n{topic_tree[:500]}...") # Print top of tree
        except Exception as e:
             print(f"Not enough topics to build a hierarchy: {e}")

        # Get topic info dataframe
        # Columns: Topic, Count, Name, Representation, Representative_Docs
        topic_info = self.topic_model.get_topic_info()
        
        results = []
        
        for _, row in topic_info.iterrows():
            t_id = row['Topic']
            # Topic -1 is the "Outlier" topic in HDBSCAN. We skip it as it's just noise.
            if t_id == -1: continue
            
            mentions = row['Count']
            # Representation is a list of the top words via c-TF-IDF
            # e.g. ['login', 'password', 'works']
            keywords_list = row['Representation']
            
            # Create a label string for our platform format
            keywords_str = ", ".join(keywords_list[:4])
            
            # Pick representative docs (HDBSCAN naturally finds the centroids)
            representative_docs = row.get('Representative_Docs', [])
            
            # BERTopic limits typical rep docs, if missing we query for the best matching docs
            if not representative_docs:
                topic_docs = [reviews[i] for i, t in enumerate(topics) if t == t_id]
                # Fallback just take top 10 longest/first
                representative_docs = topic_docs[:10]

            results.append({
                "topic_id": t_id,
                "keywords": keywords_str,
                "mentions": mentions,
                "sample_reviews": representative_docs
            })

        return results
