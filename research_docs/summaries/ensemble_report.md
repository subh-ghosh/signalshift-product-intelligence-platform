# Research Report: Step 7 - Ensemble Modeling

This final phase of benchmarking explored whether a "Voting Ensemble" (majority-rule consensus) could improve reliability and accuracy over single models.

## 📊 Ensemble Results
Tested a **Voter Classifier** consisting of: Logistic Regression, Linear SVM, and Random Forest.

| Model Selection | F1-Score | Accuracy | Training Complexity |
| :--- | :--- | :--- | :--- |
| **Best Single Model (LR)** | **0.9139** | **87.64%** | Low (1s) |
| **Voting Ensemble** | 0.9042 | 0.8675 | High (81s) |

## 🔍 Scientific Conclusion: The "Expert vs. Committee" Paradox

Our results show that the Ensemble performed slightly **lower** than the single best model (Logistic Regression). In Data Science research, this is a valid and important finding:

1. **Model Specialization**: If one model (Logistic Regression) is perfectly tuned for a specific feature set (Bi-gram TF-IDF), adding other models (like Random Forest) that are less suited for high-dimensional sparse data can actually "pull down" the majority vote.
2. **Robustness vs. Peak Performance**: While the F1-score is slightly lower, the Ensemble is likely more **Robust**. It is less prone to "Overfitting" to specific keywords because it requires a consensus between three mathematically different algorithms.
3. **Efficiency Trade-off**: The 80x increase in time (81s vs 1s) does not justify the performance.

## 🏆 Final Recommendation
For the **SignalShift B2B System**, we will stick with the **Optimized Logistic Regression (v2)** with **Balanced Class Weights**. It provides the highest accuracy, captures 10% more negative reviews, and is the most efficient for real-time API use.
