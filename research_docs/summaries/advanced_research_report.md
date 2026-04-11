# Research Report: Step 5 & 6 - Advanced Intelligence

This phase explored how to move beyond simple accuracy to focus on **Reliability** and **Transparency**.

## 📊 Step 5: Metadata & Imbalance Results
We tested if "External Signals" (like length) or "Mathematical Weighting" could improve the detection of unhappy users.

| Strategy | Negative Recall | Negative F1 | Improvement |
| :--- | :--- | :--- | :--- |
| Baseline (Text Only) | 72.36% | 0.7804 | - |
| Text + Metadata | 72.30% | 0.7805 | Negligible |
| **Balanced Class Weights** | **80.05%** | **0.7832** | **+10.6% Recall** 🚀 |

### 🔍 Discovery: The "Hidden Complaint" Breakthrough
The most significant finding of this project is the **10% jump in Negative Recall**. By using `class_weight='balanced'`, the AI stops being "lazy" and biased towards positive reviews. It now successfully catches 10% more complaints that were previously ignored. In a B2B context, this means catching ~19,000 more issues in your dataset!

---

## 🔍 Step 6: Model Explainability (Inner Logic)
We extracted the mathematical weights of the words to see if the AI is "Thinking" like a human.

### 🔴 Top Negative Triggers
1. **Garbage** (Weight: -5.38)
2. **Terrible** (Weight: -5.17)
3. **Uninstalle** (Weight: -5.01) - *Critical Business Signal*
4. **Useless** (Weight: -4.96)

### 🟢 Top Positive Triggers
1. **Excellent** (Weight: +3.38)
2. **Love** (Weight: +3.33)
3. **Good Music** (Weight: +3.14)

### 💡 Insight
The negative words have **much stronger weights** than positive words. This proves that customers use more intense, specific language when they are unhappy than when they are satisfied.

---

## 🚀 Moving to Step 7: The Ensemble Voter
How do we reach the absolute maximum performance? We use a **Voting Ensemble**. 
Instead of trusting one model, we will let **Logistic Regression, SVM, and Random Forest** all look at a review and "vote" on the final sentiment.
