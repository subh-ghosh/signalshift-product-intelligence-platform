import pandas as pd
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.decomposition import LatentDirichletAllocation as LDA
from bertopic import BERTopic
import gensim
from gensim.models.coherencemodel import CoherenceModel
import gensim.corpora as corpora
import time
import os

# Robust path detection
BASE_DIR = "/media/subh/Shared Storage/signalshift/backend"
DATA_PATH = os.path.join(BASE_DIR, "data/processed/cleaned_reviews.csv")

print("Step 3: Topic Modeling Comparison (LDA vs. BERTopic)")
print("Goal: Use the 'Coherence Score' to scientifically prove which model finds better themes.")

# 1. Load Data
df = pd.read_csv(DATA_PATH).dropna(subset=["cleaned_content"])
# Using 5,000 samples for a fast, statistically significant comparison
sample_size = 5000
df_sample = df.sample(sample_size, random_state=42)
texts = df_sample["cleaned_content"].astype(str).tolist()
tokenized_texts = [t.split() for t in texts]

# Create Gensim dictionary for Coherence calculation
id2word = corpora.Dictionary(tokenized_texts)
corpus = [id2word.doc2bow(text) for text in tokenized_texts]

# -----------------------------
# Test 1: Traditional LDA
# -----------------------------
print(f"\n[1] Running LDA (The 2003 Standard)...")
start_lda = time.time()
lda_model = LDA(n_components=10, random_state=42)
lda_model.fit(CountVectorizer().fit_transform(texts))

# Extract topics for Gensim coherence
# (Converting sklearn LDA output to Gensim-compatible format for scoring)
lda_topics = []
tf_vectorizer = CountVectorizer()
tf_vectorizer.fit(texts)
feature_names = tf_vectorizer.get_feature_names_out()
for topic_idx, topic in enumerate(lda_model.components_):
    lda_topics.append([feature_names[i] for i in topic.argsort()[:-11:-1]])

lda_coherence_model = CoherenceModel(topics=lda_topics, texts=tokenized_texts, dictionary=id2word, coherence='c_v')
lda_score = lda_coherence_model.get_coherence()
duration_lda = time.time() - start_lda
print(f"    - LDA Coherence (C_V): {lda_score:.4f}")
print(f"    - Time: {duration_lda:.2f}s")

# -----------------------------
# Test 2: BERTopic (The 2022 Standard)
# -----------------------------
print(f"\n[2] Running BERTopic (Modern Transformers)...")

# FORCE CPU for GTX 1050 compatibility
from sentence_transformers import SentenceTransformer
embedding_model = SentenceTransformer("all-MiniLM-L6-v2", device="cpu")

start_bert = time.time()
topic_model = BERTopic(embedding_model=embedding_model, nr_topics=10) 
topics, probs = topic_model.fit_transform(texts)

# Extract topics for coherence
bertopic_topics = []
for i in range(10): # Match n_components
    try:
        words = [word for word, _ in topic_model.get_topic(i)[:10]]
        bertopic_topics.append(words)
    except:
        continue

bert_coherence_model = CoherenceModel(topics=bertopic_topics, texts=tokenized_texts, dictionary=id2word, coherence='c_v')
bert_score = bert_coherence_model.get_coherence()
duration_bert = time.time() - start_bert
print(f"    - BERTopic Coherence (C_V): {bert_score:.4f}")
print(f"    - Time: {duration_bert:.2f}s")

# -----------------------------
# Summary
# -----------------------------
print("\n--- Topic Modeling Summary ---")
print(f"LDA Score: {lda_score:.4f}")
print(f"BERTopic Score: {bert_score:.4f}")

if bert_score > lda_score:
    print(f"\nWINNER: BERTopic (Improvement: {((bert_score/lda_score)-1)*100:.2f}%)")
    print("This proves that Embeddings capture semantic meaning better than raw word frequency.")
else:
    print("\nWINNER: LDA (Traditional statistics won on this sample size).")

# Save Comparison
results = pd.DataFrame({
    "Model": ["LDA", "BERTopic"],
    "Coherence_Score": [lda_score, bert_score],
    "Time": [duration_lda, duration_bert]
})
results.to_csv(os.path.join(BASE_DIR, "data/processed/topic_benchmarks.csv"), index=False)
