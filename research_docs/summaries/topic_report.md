# Research Report: Step 3 - Topic Modeling Comparison

This phase compared traditional statistical topic modeling (LDA) against modern transformer-based clustering (BERTopic) using the project's Netflix review data.

## 📊 Results Matrix
Evaluation performed on **5,000 samples** using the **C_V Coherence Score** (Higher is better).

| Model Strategy | Coherence Score | Process Time | Winner |
| :--- | :--- | :--- | :--- |
| **LDA (Traditional)** | **0.4726** | **5.71s** | **⭐ Winner** |
| **BERTopic (Modern)** | 0.3979 | 45.29s | - |

## 🔍 Scientific Analysis: Why did LDA win?

This is a counter-intuitive finding that adds significant academic value to your project:

1. **Information Density**: For short, pre-processed app reviews, LDA's probabilistic approach is often more "focused." BERTopic uses high-dimensional embeddings which can sometimes capture too much "noise" from the language, leading to slightly less coherent word-groupings on smaller vocabulary sets.
2. **Sample Size Sensitivity**: LDA is highly optimized for finding global themes in a fixed vocabulary. BERTopic's strength is typically in larger datasets (>20k) where it can leverage its internal "HDBSCAN" clustering more effectively.
3. **Execution Efficiency**: LDA was **8x faster** while producing more coherent topics (0.47 vs 0.39).

## 🏆 Final Conclusion: The "SignalShift" Research Outcome
After 3 rounds of intense benchmarking, we have discovered the "Golden Configuration" for your specific dataset:

- **Vectorization**: Bi-gram TF-IDF
- **Sentiment Model**: Logistic Regression
- **Topic Model**: LDA (For coherence)

---

## 🚀 Step 4: System Upgrade
We now exit the "Research Phase" and enter the **"Production Phase."** 
We will:
1. Train the **Bi-gram TF-IDF** on the FULL 191k dataset.
2. Save the **Logistic Regression** as the final `sentiment_model.joblib`.
3. Integrate these "winners" into the main API service.
