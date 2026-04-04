# Implementation Plan: SignalShift ML Pipeline

## Current Status — All Phases Complete ✅

The SignalShift ML pipeline has been fully evolved through three tiers. Below is the complete record.

---

## Completed Phases (10–21): Core Infrastructure

| Phase | What | Status |
|---|---|---|
| 10 | NMF benchmark vs old LDA | ✅ |
| 11–12 | Evidence quality filter, NMF + TF-IDF | ✅ |
| 13 | Semantic reranking (MiniLM cosine) | ✅ |
| 14 | Spam / junk pre-processing filter | ✅ |
| 15 | NMF stop-word tuning, dynamic thresholds | ✅ |
| 16 | Time-series export (`topic_timeseries.csv`) | ✅ |
| 17 | AI Executive Summary service | ✅ |
| 18 | Evidence keyword highlighting | ✅ |
| 19 | PDF export, AI summary formatting | ✅ |
| 20 | Dynamic chart time-range (3M/6M/12M/ALL) | ✅ |
| 21 | Synchronized AI summary with time range | ✅ |

---

## Tier 1 DS Upgrades (Phase 22–24)

### Phase 22 — Semantic Zero-Shot Labeler
#### [MODIFY] [issue_labeler.py](file:///media/subh/Shared%20Storage/signalshift/backend/app/ml/issue_labeler.py)
- Replaced rule-based `generate_issue_label()` with MiniLM cosine similarity
- 12-category universal taxonomy (app-agnostic, works for any mobile/SaaS app)
- `generate_issue_label(keywords, encoder=None)` — accepts pre-loaded encoder to avoid double load

### Phase 23 — Category Deduplication *(superseded by Phase 24)*
- Merged 30 NMF raw topics → 12 categories by group-by canonical label
- Mention counts summed, evidence pools merged
- Superseded: Phase 24 eliminates duplicates upstream

### Phase 24 — Direct Per-Review Semantic Classification
#### [MODIFY] [ml_service.py](file:///media/subh/Shared%20Storage/signalshift/backend/app/services/ml_service.py)
- **Classification**: `(N_reviews, 384) @ (384, 12) → (N, 12)` similarity matrix; argmax = category
- **NMF role**: Downgraded to ABSA aspect detection only, not categorization
- **Confidence routing**: `< 0.30` → `"General App Feedback"` + anomaly pool
- **Dedup**: Evidence with cosine sim `> 0.85` skipped

---

## Tier 2 DS Upgrades (Phase 25)

### Phase 25.1 — Silhouette Score Quality Benchmarking
#### [MODIFY] [ml_service.py](file:///media/subh/Shared%20Storage/signalshift/backend/app/services/ml_service.py)
- Samples up to 50 reviews/category, computes `silhouette_score(metric="cosine")`
- Output: `data/processed/classification_quality.csv`

### Phase 25.2 — Temporal Semantic Drift Detection
#### [MODIFY] [ml_service.py](file:///media/subh/Shared%20Storage/signalshift/backend/app/services/ml_service.py)
- Tracks up to 30 review texts per (category, month) during batch
- Monthly centroid embeddings, consecutive cosine drift computed
- `drift_score > 0.15` → `is_evolving = True`
- Output: `data/processed/semantic_drift.csv`

### Phase 25.3 — Neural Topic Discovery Tool
#### [NEW] [neural_topic_discovery.py](file:///media/subh/Shared%20Storage/signalshift/backend/app/ml/neural_topic_discovery.py)
- Standalone script: NMF on MiniLM embeddings (RELU shift for non-negativity)
- Discovers semantic clusters not in the predefined taxonomy
- Outputs `data/processed/neural_topics.csv` with top-5 representative reviews per cluster

---

## Tier 3 DS Upgrades (Phase 26–28)

### Phase 26 — Severity Scoring
#### [MODIFY] [ml_service.py](file:///media/subh/Shared%20Storage/signalshift/backend/app/services/ml_service.py)
- `compute_severity(text)` → score 1.0–5.0
- Lexicon: `SEVERITY_5` (scam/fraud), `SEVERITY_4` (terrible/refund), `SEVERITY_3` (crash/bug)
- Signals: caps ratio, exclamation density
- `avg_severity` column added to `topic_analysis.csv`

### Phase 27 — Anomaly / Emerging Issue Detection
#### [MODIFY] [ml_service.py](file:///media/subh/Shared%20Storage/signalshift/backend/app/services/ml_service.py)
- Pools low-confidence reviews during classification (`low_conf_reviews` list)
- Post-batch: NMF on embedding space of pooled reviews
- Clusters with `≥ 20` reviews exported; `≥ 40` flagged as high-priority
- Output: `data/processed/emerging_issues.csv`

### Phase 28 — Few-Shot Fine-Tuning Infrastructure
#### [NEW] [finetune_encoder.py](file:///media/subh/Shared%20Storage/signalshift/backend/app/ml/finetune_encoder.py)
- Input: `data/labeled/review_labels.csv` (`review`, `category` columns)
- Builds anchor/positive/negative triplets per category
- Trains with `TripletLoss` for 3 epochs, saves to `models/finetuned_encoder/`
- Self-evaluates accuracy against labeled set at completion
- **Prerequisite**: 50+ labeled examples per category

---

## Output Files Reference

| File | Contents |
|---|---|
| `data/processed/topic_analysis.csv` | label, mentions, avg_severity, sample_reviews |
| `data/processed/topic_timeseries.csv` | label, month, mentions |
| `data/processed/classification_quality.csv` | silhouette_score, n_categories, thresholds |
| `data/processed/semantic_drift.csv` | category, month_from, month_to, drift_score, is_evolving |
| `data/processed/emerging_issues.csv` | cluster_id, estimated_volume, is_flagged, sample_reviews |
| `data/processed/neural_topics.csv` | neural_topic_id, avg_activation, top reviews |
| `data/processed/aspect_analysis.csv` | aspect, mentions |

---

## Remaining: Tier 3 Item 1 (Optional)

### Multilingual Support
**Change**: Swap `all-MiniLM-L6-v2` → `paraphrase-multilingual-MiniLM-L12-v2` in `ml_service.py`
- Same 384-dim space, same cosine logic
- Supports 50+ languages (Hindi, Spanish, French, etc.)
- One-line change in `MLService.__init__`

---

## Verification Plan

### Auto-checks (run on each Kaggle sync)
- `classification_quality.csv` — silhouette score logged; target `> 0.25`
- `emerging_issues.csv` — review flagged clusters, update taxonomy if volume ≥ 40
- `semantic_drift.csv` — monitor `is_evolving = True` categories for root-cause changes

### When labeled data available
- Run `python app/ml/finetune_encoder.py`
- Target accuracy on labeled set: `> 85%` before switching to fine-tuned model
- Update `ml_service.py` encoder path to `models/finetuned_encoder/`
