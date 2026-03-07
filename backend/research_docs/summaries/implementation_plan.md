# Implementation Plan: Top Issues & Evidence Optimization

This plan focuses on elevating the "Top Issues" feature by ensuring the most relevant, "necessary" comments are shown as evidence and providing a formal benchmark of the architectural improvements.

## Proposed Changes

---

### Phase 10: Benchmarking & Qualitative Audit
Quantify the shift from generic clusters to actionable business intelligence.

#### [NEW] [topic_benchmark_v3.py](file:///media/subh/Shared%20Storage/signalshift/backend/app/ml/topic_benchmark_v3.py)
- Script to run "Old Strategy" (Generic) vs "New Strategy" (Negative-Only + Filtered) on the same 10k review sample.
- Calculate **Noise Ratio** (percentage of generic/Hindi filler words in top keywords).
- Save results to `data/processed/topic_evolution_summary.csv`.

---

### Phase 11: "Necessary Comments" Logic (Evidence Filter)
Refine how we select reviews for the "Evidence" section to ensure they are high-signal.

#### [MODIFY] [ml_service.py](file:///media/subh/Shared%20Storage/signalshift/backend/app/services/ml_service.py)
- Update `generate_topic_analysis_cache` to prioritize:
    1. **Length/Detail**: Ignore "it sucks" or "good" (too short).
    2. **Sentiment Extremity**: Prioritize Score 1 over Score 2.
    3. **Diversity**: Don't show 5 comments that say exactly the same thing.

#### [MODIFY] [routes.py](file:///media/subh/Shared%20Storage/signalshift/backend/app/api/routes.py)
- Update `/dashboard/issue-reviews` to return the pre-filtered, high-signal "Necessary" samples.

---

### Phase 12: Research Summary & Benchmarking UI
Visualize the "Before vs After" improvement for the user.

#### [NEW] [ResearchBenchmark.jsx](file:///media/subh/Shared%20Storage/signalshift/frontend/src/components/ResearchBenchmark.jsx)
- A comparison component showing the "Evolution of Intelligence" (Old Labels vs New Labels).

#### [MODIFY] [Dashboard.jsx](file:///media/subh/Shared%20Storage/signalshift/frontend/src/pages/Dashboard.jsx)
- Integrate the Research Benchmark into the "Executive Report" or as a dedicated "Research Impact" card.

## Verification Plan

### Automated Tests
- `topic_benchmark_v3.py` must show a >40% reduction in "Generic Noise" in keywords.
- Verify `topic_analysis.csv` actually contains longer, more descriptive sample reviews.

### Manual Verification
- Check the "Evidence" section in the dashboard to ensure "one-word" reviews are gone.
- Review the "Before vs After" table in the UI.
