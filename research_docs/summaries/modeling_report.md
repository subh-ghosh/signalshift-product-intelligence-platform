# Research Report: Step 2 - Advanced Modeling

This phase tested whether more complex algorithms like Support Vector Machines (SVM) or Random Forests could outperform our baseline on the optimized Bi-gram feature set.

## 📊 Results Matrix
Evaluation performed on **38,327** test samples.

| Model | Accuracy | F1-Score | Training Time | Efficiency Rank |
| :--- | :--- | :--- | :--- | :--- |
| **Logistic Regression** | **87.64%** | **0.9139** | **1.27s** | **⭐ 1st** |
| **Linear SVM** | 87.30% | 0.9116 | 20.63s | 2nd |
| **Random Forest** | 87.03% | 0.9087 | 162.43s | 3rd |

## 🔍 Scientific Observations

### 1. The Linear Ceiling
Despite increasing computer power (Random Forest took 128x longer), performance did not improve. This is a classic "Research Finding": for high-dimensional text data via TF-IDF, simple linear boundaries (Logistic Regression) are often mathematically optimal.

### 2. Random Forest Limitations
Random Forest is great for structured data (like age, price, etc.) but often struggles with the sparse, high-dimensional matrices created by TF-IDF (10,000+ columns).

### 3. Conclusion for Step 2
Complexity $\neq$ Accuracy. We have reached the maximum signal possible using "Bag of Words" (TF-IDF) methods. 

---

## 🏆 The "Final Boss" Challenge (Step 2.5)
To break the **87% accuracy barrier**, we must stop looking at words as isolated numbers and start looking at **Context**. 

**Next**: We use **BERT (Bidirectional Encoder Representations from Transformers)**. Unlike the models above, BERT understands that *"this is not bad"* means "Good", whereas TF-IDF just sees the word "bad".
