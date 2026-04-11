# Project Overview: SignalShift

**SignalShift** is a production-grade, app-agnostic review intelligence platform. It ingests app store reviews, classifies each complaint into canonical business issue categories using semantic AI, and surfaces actionable insights on a live dashboard.

---

## 🚀 What It Is
A "Voice of the Customer" (VoC) dashboard for product managers. It takes thousands of Play Store reviews and uses ML to tell you *"Subscription & Billing is your #1 issue (428 mentions, avg severity 4.1/5)"* — in real time.

## 🛠️ Technology Stack

### Backend (Python/Intelligence)
- **FastAPI**: High-performance web API framework
- **ML Pipeline**:
  - **Sentiment**: Scikit-learn (TF-IDF + Logistic Regression, F1=0.91)
  - **Topic Classification**: MiniLM zero-shot cosine similarity → 12 canonical categories
  - **Severity Scoring**: Heuristic lexicon + text signal (1.0–5.0 scale)
  - **Drift Detection**: Monthly embedding centroid tracking
  - **Anomaly Detection**: NMF on embedding space for unknown issue clusters
  - **Fine-tuning**: Triplet loss contrastive training (ready when labeled data available)
- **Data Sync**: Kaggle API integration

### Frontend (React/Visualization)
- **React + Vite**, **Recharts** for dynamic charts
- **AI Executive Summary**: Recalculates top risers/fallers per selected time range

---

## 📂 Key Files

### 🧠 Backend
- [backend/app/services/ml_service.py](../../../backend/app/services/ml_service.py): Core inference pipeline
- [backend/ml/core/issue_labeler.py](../../../backend/ml/core/issue_labeler.py): Universal taxonomy + MiniLM zero-shot labeler
- [backend/app/services/ai_summary_service.py](../../../backend/app/services/ai_summary_service.py): AI executive summary

### 💻 Frontend
- [frontend/src/pages/Dashboard.jsx](../../../frontend/src/pages/Dashboard.jsx): Main UI
- [frontend/src/components/TrendingChart.jsx](../../../frontend/src/components/TrendingChart.jsx): Time-series chart
- [frontend/src/components/AiSummaryCard.jsx](../../../frontend/src/components/AiSummaryCard.jsx): AI insights card

---

## 🔄 Functional Flow
1. **Sync**: Kaggle API pulls latest app reviews CSV
2. **Sentiment**: Reviews classified negative/positive (LR, F1=0.91)
3. **Encode**: Negative reviews encoded with MiniLM (384-dim vectors)
4. **Classify**: Cosine similarity against 12 taxonomy centroids; confidence threshold 0.30
5. **Score**: Severity 1–5 computed per review; avg_severity per category
6. **Benchmark**: Silhouette score + temporal drift computed post-batch
7. **Anomaly**: Low-confidence reviews clustered for emerging issue detection
8. **Visualize**: Dashboard shows issue categories, trend chart, AI summary

---

## 📊 Output Files
| File | Contents |
|---|---|
| `topic_analysis.csv` | label, mentions, avg_severity, sample_reviews |
| `topic_timeseries.csv` | label, month, mentions |
| `classification_quality.csv` | silhouette_score, n_categories |
| `semantic_drift.csv` | category, month drift scores |
| `emerging_issues.csv` | unknown issue clusters |
