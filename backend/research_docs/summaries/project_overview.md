# Project Overview: SignalShift

**SignalShift** is an end-to-end Data Science and Engineering application designed to monitor and analyze Netflix user sentiment and product issues. It automates the pipeline from raw data acquisition (Kaggle) to actionable insights (Dashboard).

---

## 🚀 What It Is
A "Voice of the Customer" (VoC) dashboard for product managers. It takes thousands of daily Play Store reviews and uses Machine Learning to tell you, for example, that "Video Playback" is the top complaint today.

## 🛠️ Technology Stack

### Backend (Python/Intelligence)
- **FastAPI**: The high-performance web framework serving the API.
- **ML Models**:
  - **Sentiment Analysis**: Scikit-learn based model (TF-IDF + Classifier) to flag negative vs. positive feedback.
  - **Topic Modeling (BERTopic)**: Uses `sentence-transformers` and clustering to group similar complaints together automatically.
  - **Preprocessing**: `spaCy` for deep linguistic cleaning (lemmatization and stop-word removal).
- **Data Sync**: Custom Kaggle API integration for daily dataset updates.

### Frontend (React/Visualization)
- **React + Vite**: Modern, fast frontend architecture.
- **Recharts**: For dynamic sentiment and issue-distribution charts.
- **Axios**: Communicates with the FastAPI backend.

---

## 📂 Key Files & What They Do

### 🧠 Backend (Intelligence)
- [main.py](file:///media/subh/Shared%20Storage/signalshift/backend/app/main.py): Entry point; sets up middleware and connects routes.
- [routes.py](file:///media/subh/Shared%20Storage/signalshift/backend/app/api/routes.py): Defines the API endpoints (`/analyze-review`, `/dashboard/top-issues`, etc.).
- [ml_service.py](file:///media/subh/Shared%20Storage/signalshift/backend/app/services/ml_service.py): The "brain" that loads models and runs batch inferences in the background.
- [text_cleaner.py](file:///media/subh/Shared%20Storage/signalshift/backend/app/ml/text_cleaner.py): Uses spaCy to clean raw text so the AI can understand it better.
- [issue_labeler.py](file:///media/subh/Shared%20Storage/signalshift/backend/app/ml/issue_labeler.py): Converts raw ML clusters (e.g., "buffer, video, slow") into readable titles like "Video Playback Issues".

### 💻 Frontend (Interface)
- [Dashboard.jsx](file:///media/subh/Shared%20Storage/signalshift/frontend/src/pages/Dashboard.jsx): The main UI assembly containing charts and the summary metric cards.
- [api.js](file:///media/subh/Shared%20Storage/signalshift/frontend/src/services/api.js): Centralized logic for talking to the backend.

---

## 🔄 Functional Flow
1. **Sync**: API pulls the latest "Netflix Reviews" CSV from Kaggle.
2. **Classify**: Each review is passed through a Sentiment model.
3. **Cluster**: Negative reviews are grouped using BERT embeddings to find common themes.
4. **Label**: The top themes are auto-labeled for the dashboard.
5. **Visualize**: PMs log in to see what users are complaining about in real-time.
