# Final Research Synthesis: SignalShift Intelligence

This document summarizes the complete scientific journey of SignalShift — from initial benchmarking through production-grade DS upgrades.

---

## 📈 Phase 1–9: Benchmarking Milestones (Sentiment Model)

| Step | Focus | Finding |
|---|---|---|
| 1 | Vectorization | Bi-gram TF-IDF: F1=0.9138 (best) |
| 2 | Model Selection | Logistic Regression: 87.64% accuracy, 3000x faster than BERT |
| 2.5 | Transformers | Generic DistilBERT F1=0.87 < domain-optimized LR F1=0.91 |
| 3 | Topic Modeling | LDA coherence 0.4726 > BERTopic 0.3979 (8x slower) |
| 5 | Class Imbalance | Balanced weights: +10.6% Negative Recall (+19k complaints caught) |
| 6 | Explainability | Key negative triggers: *garbage* (-5.38), *terrible* (-5.17) |
| 7 | Ensembles | Single optimized LR (0.9139) > Voting ensemble (0.9042) |
| 8 | Hypertuning | C=1, l2 penalty = optimal regularization |
| 9 | Robustness | 5-fold CV std dev = 0.0013 (production-ready) |

---

## 🧠 Phase 10–21: Infrastructure & Intelligence

| Phase | What Built |
|---|---|
| 10–14 | NMF pipeline, spam filter, semantic evidence selector |
| 15–16 | Stop-word tuning, time-series CSV export |
| 17–18 | AI executive summary, keyword highlighting |
| 19–21 | PDF export, dynamic chart range, synchronized AI summary |

---

## 🔬 Phase 22–28: DS Pipeline Evolution (Tiers 1–3)

### Tier 1 (Phase 22–24) — Classification Accuracy
| What | Result |
|---|---|
| Semantic zero-shot labeling (MiniLM cosine) | `"open, viber"` → `"App Crash & Launch Failure"` ✅ |
| Category deduplication (30 → 12 categories) | `Subscription & Billing: 428 mentions` (merged from 3 NMF clusters) |
| Direct per-review classification | NMF downgraded to ABSA only; all routing = MiniLM cosine sim |
| Confidence threshold (0.30) | Low-confidence → "General App Feedback" + anomaly pool |
| Near-duplicate dedup (cos > 0.85) | Evidence pool: diverse, non-repetitive top 15 reviews |

### Tier 2 (Phase 25) — Measurement & Discovery
| What | Output |
|---|---|
| Silhouette Score benchmarking | `classification_quality.csv` — quantifies cluster separation |
| Temporal Semantic Drift | `semantic_drift.csv` — flags categories with `drift_score > 0.15` |
| Neural Topic Discovery (NMF on embeddings) | `neural_topics.csv` — finds clusters not in taxonomy |

### Tier 3 (Phase 26–28) — Enterprise Grade
| What | Output |
|---|---|
| Severity scoring (1.0–5.0) | `avg_severity` column in `topic_analysis.csv` |
| Anomaly / emerging issue detection | `emerging_issues.csv` (flagged at ≥40 volume) |
| Few-shot fine-tuning script | `finetune_encoder.py` — ready when 50+ labeled examples available |

---

## 💡 Top Research Findings

1. **"Reject NMF for Classification"**: NMF (bag-of-words) assigns `"sign, email, password"` to `Privacy & Security`. MiniLM cosine similarity correctly routes it to `Account & Login`.
2. **"Confidence Routing Beats Forced Assignment"**: Reviews with low cosine similarity to any category should never be forced — they become the best signal for detecting *emerging unknown issues*.
3. **"Monthly Drift Proves Issues Evolve"**: A `drift_score > 0.15` on "Subscription & Billing" between Jan and Mar indicates the complaint shifted from *pricing* to *failed auto-charges* — same category, different root cause.

---

## 🏁 Current Technical State
`MLService` runs the full Tier 1–3 pipeline on every Kaggle sync. The sentiment model remains Logistic Regression (LR + TF-IDF Bi-gram, F1=0.91). Topic classification is 100% semantic via MiniLM. Fine-tuning infrastructure is ready for when labeled data is collected.
