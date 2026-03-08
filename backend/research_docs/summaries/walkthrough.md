# SignalShift — Full Platform Walkthrough

Complete record of all features built and DS improvements made.

---

## Dashboard Features (Phase 20–21)

### 📈 Dynamic Time-Series Filtering [Phase 20]
- **Controls**: 3M, 6M, 12M, ALL range selector on the Trending Chart
- **Logic**: Client-side data slicing — instant, lag-free transitions
- **File**: `TrendingChart.jsx`

### 🤖 Synchronized AI Intelligence [Phase 21]
- `range` state lifted to `Dashboard.jsx` — single source of truth
- `AiSummaryCard.jsx` re-fetches AI summary on every range change
- Backend `ai_summary_service.py` recalculates Risers/Fallers for the selected window
- `routes.py` accepts `limit_months` query parameter

---

## DS Pipeline Evolution

### Before (Phase 21 baseline)
```
Raw Reviews → Spam Filter → NMF (30 components, TF-IDF) → Rule-based Labels → CSV
```
**Problems:** Labels were brittle keyword concatenations (`"Open & Viber Issues"`), 30 raw clusters shown as duplicates, no accuracy metric.

---

### Phase 22 — Semantic Zero-Shot Labeling
**File:** `app/ml/issue_labeler.py` (full rewrite)

Replaced rule-based `issue_labeler` with **MiniLM zero-shot cosine similarity** against a 12-category universal taxonomy.

| Before | After |
|---|---|
| `open, viber, close` → `"Open & Viber Issues"` | `"App Crash & Launch Failure"` |
| `pay, money, watch` → `"Pay & Money Issues"` | `"Subscription & Billing"` |
| `bug, fix, issue` → `"Bug & Fix Issues"` | `"Bugs & Technical Errors"` |

**Taxonomy (app-agnostic, scales to any app):**
`Subscription & Billing`, `App Crash & Launch Failure`, `Video & Streaming Playback`, `Account & Login`, `Customer Support`, `Performance & Speed`, `Content & Features`, `Notifications & Spam`, `UI & Navigation`, `Bugs & Technical Errors`, `Privacy & Security`, `Download & Offline`

---

### Phase 23 — Category Deduplication & Merging
Merged 30 NMF raw topics → **12 clean canonical categories** by grouping on canonical label and summing mentions.

**Result (from simulation on real data):**
| Category | Mentions |
|---|---|
| Subscription & Billing | **428** |
| Privacy & Security | 198 |
| Bugs & Technical Errors | 158 |
| Customer Support | 153 |
| Content & Features | 133 |
| Video & Streaming Playback | 114 |

---

### Phase 24 — Tier 1: Direct Semantic Classification
**Architecture replaced:**
```
BEFORE: review → NMF (bag-of-words cluster) → relabel
AFTER:  review → MiniLM.encode() → cosine sim → 12 taxonomy centroids
```

Three sub-improvements:
1. **Direct Per-Review Classification** — each review encoded and matched against taxonomy matrix `(N, 384) @ (384, 12) → (N, 12)`. NMF kept only for ABSA aspect detection.
2. **Confidence Threshold Routing** — reviews scoring `< 0.30` routed to `"General App Feedback"` instead of forcing a bad match.
3. **Near-Duplicate Deduplication** — evidence reviews with cosine similarity `> 0.85` removed from the evidence pool before saving.

---

### Phase 25 — Tier 2: Research-Grade Improvements

#### 25.1 — Silhouette Score Benchmarking
- Samples up to 50 reviews per category, computes `silhouette_score(metric="cosine")`
- **Score near 1.0** = well-separated clusters, **near 0** = overlapping
- Output: `data/processed/classification_quality.csv`
```
metric, value, n_categories, n_samples, threshold_confidence, dedup_threshold
silhouette_score, 0.XXXX, 12, N, 0.30, 0.85
```

#### 25.2 — Temporal Semantic Drift Detection
- Monthly review texts tracked per category (up to 30/month)
- Embedding centroid computed per month, cosine drift between consecutive months
- `drift_score > 0.15` → flagged as `is_evolving = True`
- Output: `data/processed/semantic_drift.csv`

#### 25.3 — Neural Topic Discovery Tool
- **File:** `app/ml/neural_topic_discovery.py`
- Runs NMF on MiniLM sentence embeddings (not TF-IDF) to discover clusters in semantic space
- Surfaces unknown emerging issues not covered by taxonomy
- Run offline: `python app/ml/neural_topic_discovery.py`

---

### Phase 26 — Tier 3: Severity Scoring
Per-review severity score **1.0–5.0** computed inline:

```python
SEVERITY_5_WORDS = {"scam", "fraud", "lawsuit", "hack", "stolen"}   # +2.5
SEVERITY_4_WORDS = {"terrible", "refund", "charged", "unauthorized"} # +1.5
SEVERITY_3_WORDS = {"crash", "bug", "error", "slow", "annoying"}     # +0.5
# + caps_ratio > 0.3 → +0.5
# + each ! → +0.2 (capped +0.6)
```

`avg_severity` exported as a column in `topic_analysis.csv`.

---

### Phase 27 — Tier 3: Anomaly / Emerging Issue Detection
- Low-confidence reviews (below `CONFIDENCE_THRESHOLD = 0.30`) pooled during classification
- After batch, pool clustered with NMF on MiniLM embeddings
- Clusters with **20+ reviews** → surface as potential new issue
- Clusters with **40+ reviews** → `is_flagged = True`
- Output: `data/processed/emerging_issues.csv`

---

### Phase 28 — Tier 3: Few-Shot Fine-Tuning Script
**File:** `app/ml/finetune_encoder.py`

Full contrastive training loop using **triplet loss** on labeled review data:
```
Anchor  = review text
Positive = another review in same category
Negative = review from different category
→ Loss: TripletLoss (SentenceTransformers)
→ Epochs: 3, Batch: 16
→ Output: models/finetuned_encoder/
```

**Expected accuracy lift:** ~80% → ~95%+ (once 50+ labeled examples per category collected)

To use the fine-tuned model, update `ml_service.py`:
```python
SentenceTransformer('models/finetuned_encoder/', device='cpu')
```

---

## Final Pipeline Architecture

```
Raw Reviews
  ↓ spam_filter.py
  ↓ MiniLM encode (batch, normalized)
  ↓ cosine sim → 12 taxonomy centroids
      ├─ confidence ≥ 0.30 → canonical category
      └─ confidence < 0.30 → "General App Feedback" + anomaly pool
  ↓ severity score (1.0–5.0) per review
  ↓ monthly texts tracked per category
  ↓ evidence selection (min-heap, top-20)
  ↓ evidence re-ranking (label alignment)
  ↓ near-duplicate deduplication (cos > 0.85)
  ↓ avg_severity aggregation per category
  ↓ topic_analysis.csv  (label, mentions, avg_severity, sample_reviews)
  ↓ topic_timeseries.csv (label, month, mentions)
  ↓ [async] silhouette score → classification_quality.csv
  ↓ [async] temporal drift → semantic_drift.csv
  ↓ [async] anomaly cluster → emerging_issues.csv
  ↓ ai_summary_service.py → windowed executive summary
```

---

*SignalShift — Production-grade review intelligence platform.*
