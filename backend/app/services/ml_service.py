import joblib
import pickle
import time
import numpy as np

from sentence_transformers import SentenceTransformer

from app.ml.text_cleaner import clean_text


class MLService:

    def __init__(self):

        print("Loading ML models...")

        # sentiment model
        self.sentiment_model = joblib.load("models/sentiment_model.joblib")

        # tfidf vectorizer
        self.vectorizer = joblib.load("models/tfidf_vectorizer.joblib")

        print("Loading embedding model...")

        self.embedding_model = SentenceTransformer("all-MiniLM-L6-v2")

        print("Loading topic embeddings...")

        with open("models/topic_embeddings.pkl", "rb") as f:
            data = pickle.load(f)

        self.topics = data["topics"]
        self.topic_embeddings = data["embeddings"]
        
        # Progress tracking for large uploads
        self.progress = {
            "processed": 0, 
            "total": 0, 
            "status": "idle",
            "eta_seconds": 0,
            "start_time": None
        }
        self.should_stop = False

    print("ML models loaded successfully.")

    def _update_eta(self, processed, total, start_time):
        """Calculates estimated seconds remaining based on processing speed"""
        if processed == 0 or start_time is None:
            return 0
        
        elapsed = time.time() - start_time
        speed = processed / elapsed  # items per second
        remaining = total - processed
        
        if speed > 0:
            return round(remaining / speed)
        return 0

    def stop_analysis(self):
        """Signals the background job to stop early"""
        self.should_stop = True
        self.progress["status"] = "stopping"

    # -------------------------
    # Sentiment
    # -------------------------

    def predict_sentiment(self, review):

        cleaned = clean_text(review)

        vector = self.vectorizer.transform([cleaned])

        sentiment = self.sentiment_model.predict(vector)[0]

        return sentiment

    def predict_sentiment_batch(self, reviews):
        """Vectorized sentiment prediction for large batches with progress tracking"""
        self.should_stop = False
        total = len(reviews)
        self.progress["total"] = total
        self.progress["processed"] = 0
        self.progress["status"] = "sentiment"
        self.progress["start_time"] = time.time()
        self.should_stop = False
        
        sentiments = []
        batch_size = 512  # Sentiment is faster, use larger batches
        
        for i in range(0, total, batch_size):
            if self.should_stop:
                print(f"Sentiment analysis stopped at {i} reviews.")
                break
                
            try:
                batch = reviews[i:i + batch_size]
                cleaned_reviews = [clean_text(r) for r in batch]
                vectors = self.vectorizer.transform(cleaned_reviews)
                batch_sentiments = self.sentiment_model.predict(vectors)
                sentiments.extend(batch_sentiments.tolist())
            except Exception as e:
                print(f"Error processing sentiment batch {i}: {e}")
                # Fill with neutral or error label if batch fails
                sentiments.extend(["neutral"] * len(batch))
            
            self.progress["processed"] = min(i + batch_size, total)
            self.progress["eta_seconds"] = self._update_eta(
                self.progress["processed"], 
                total, 
                self.progress["start_time"]
            )
            
        return sentiments

    # -------------------------
    # Topic detection
    # -------------------------

    def predict_topic(self, review):

        cleaned = clean_text(review)
        review_embedding = self.embedding_model.encode([cleaned])[0]

        # Cosine similarity
        similarities = np.dot(self.topic_embeddings, review_embedding) / (
            np.linalg.norm(self.topic_embeddings, axis=1) * np.linalg.norm(review_embedding)
        )

        best_index = int(np.argmax(similarities))

        topic = self.topics[best_index]

        return {
            "topic_id": best_index,
            "keywords": topic
        }

    # -------------------------
    # Full analysis
    # -------------------------

    def analyze_review(self, review):

        sentiment = self.predict_sentiment(review)

        topic_info = self.predict_topic(review)

        return {
            "review": review,
            "sentiment": sentiment,
            "topic_id": topic_info["topic_id"],
            "topic_keywords": topic_info["keywords"]
        }

    # -------------------------
    # Issue detection for batch
    # -------------------------

    def detect_issues(self, reviews):

        issue_counter = {}

        for review in reviews:

            result = self.analyze_review(review)

            issue = result["topic_keywords"]

            issue_counter[issue] = issue_counter.get(issue, 0) + 1

        sorted_issues = sorted(
            issue_counter.items(),
            key=lambda x: x[1],
            reverse=True
        )

        issues = []

        for issue, count in sorted_issues[:10]:

            issues.append({
                "issue": issue,
                "mentions": count
            })

        return issues
        
    # -------------------------
    # Dashboard Cache Generation
    # -------------------------
    
    def generate_topic_analysis_cache(self, df):
        """
        Runs batch inference on a newly uploaded dataset's negative reviews
        using vectorized batch encoding for high performance.
        """
        import pandas as pd
        self.should_stop = False
        
        self.progress["status"] = "analyzing"
        
        # Only analyze negative sentiment
        if "sentiment" in df.columns:
            negative_df = df[df["sentiment"] == "negative"].copy()
        else:
            negative_df = df.copy()
            
        total_negative = len(negative_df)
        self.progress["total"] = total_negative
        self.progress["processed"] = 0
        self.progress["start_time"] = time.time()
            
        if total_negative == 0:
            pd.DataFrame(columns=['topic_id', 'keywords', 'mentions', 'sample_reviews']).to_csv("data/processed/topic_analysis.csv", index=False)
            self.progress["status"] = "idle"
            return
            
        reviews = negative_df["content"].astype(str).tolist()
        topic_stats = {}
        
        batch_size = 128
        for i in range(0, total_negative, batch_size):
            if self.should_stop:
                print(f"Topic analysis stopped at {i} reviews.")
                break
                
            try:
                batch_reviews = reviews[i:i + batch_size]
                cleaned_batch = [clean_text(r) for r in batch_reviews]
                
                # Vectorized batch encoding (CRITICAL for performance)
                batch_embeddings = self.embedding_model.encode(cleaned_batch)
                
                # Calculate similarities for the whole batch at once
                for j, review_embedding in enumerate(batch_embeddings):
                    # Cosine similarity
                    norm_topics = np.linalg.norm(self.topic_embeddings, axis=1)
                    norm_review = np.linalg.norm(review_embedding)
                    
                    if norm_review == 0:
                        continue
                        
                    similarities = np.dot(self.topic_embeddings, review_embedding) / (norm_topics * norm_review)
                    best_index = int(np.argmax(similarities))
                    
                    t_id = best_index
                    keywords = self.topics[t_id]
                    
                    if t_id not in topic_stats:
                        topic_stats[t_id] = {
                            "keywords": keywords,
                            "mentions": 0,
                            "sample_reviews": []
                        }
                        
                    topic_stats[t_id]["mentions"] += 1
                    if len(topic_stats[t_id]["sample_reviews"]) < 20: 
                        topic_stats[t_id]["sample_reviews"].append(batch_reviews[j])
            except Exception as e:
                print(f"Error processing topic batch {i}: {e}")
            
            self.progress["processed"] = min(i + batch_size, total_negative)
            self.progress["eta_seconds"] = self._update_eta(
                self.progress["processed"], 
                total_negative, 
                self.progress["start_time"]
            )

        # Format into a dataframe
        rows = []
        for t_id, data in topic_stats.items():
            rows.append({
                "topic_id": t_id,
                "keywords": data["keywords"],
                "mentions": data["mentions"],
                "sample_reviews": str(data["sample_reviews"]) 
            })
            
        cache_df = pd.DataFrame(rows).sort_values(by="mentions", ascending=False)
        cache_df.to_csv("data/processed/topic_analysis.csv", index=False)
        
        self.progress["status"] = "complete"
        print(f"Successfully generated and cached new topic_analysis.csv for {total_negative} reviews.")