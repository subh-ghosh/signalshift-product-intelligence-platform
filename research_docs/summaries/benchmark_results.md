# Benchmark Results: Sentiment Classification

We have completed **Phase 1: Model Benchmarking**. This step provides a scientific baseline by comparing traditional ML classifiers on the processed Netflix review dataset.

## 📊 Comparison Table
Testing samples: **38,327 reviews** (20% holdout).

| Model | Accuracy | Precision (Pos) | Recall (Pos) | F1-Score |
| :--- | :--- | :--- | :--- | :--- |
| **Logistic Regression** | **87.66%** | 88.67% | **94.31%** | **0.9141** |
| **Linear SVM** | 87.32% | 88.42% | 94.11% | 0.9118 |
| **Naive Bayes** | 87.30% | **89.50%** | 92.63% | 0.9104 |
| **Random Forest** | 87.08% | 89.13% | 92.75% | 0.9091 |

## 🔍 Key Findings

### 1. The Winner: Logistic Regression
Logistic Regression achieved the highest **F1-Score (0.914)**. In research, F1-Score is often more important than accuracy because it balances precision and recall, especially in sentiment tasks where we want to avoid misclassifying "Negative" as "Positive".

### 2. High Recall vs. Precision
All models showed very high **Recall (~94%)**. This means the system is extremely good at finding positive reviews. However, the slightly lower **Precision (~88-89%)** indicates some negative reviews are still being flagged as positive.

### 3. Efficiency
Despite being the most complex, **Random Forest** did not outperform the linear models (LR/SVM), suggesting that the TF-IDF feature space is fairly linear and well-handled by simpler, faster algorithms.

---

## ⏭️ Current Step: Phase 2
We are now moving into **Phase 2: Feature Engineering & NLP Upgrades**.
We will aim to improve these baseline numbers using:
1. **N-grams**: To capture context (e.g., "not good").
2. **Contextual Embeddings**: Using Transformers to push accuracy past 90%.
