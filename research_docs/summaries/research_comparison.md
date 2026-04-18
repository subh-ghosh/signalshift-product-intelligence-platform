# Literature Review: SignalShift vs. Research Standards

> Status note (current): BERTopic references below are historical benchmark context.
> Current production stack uses LR + bi-gram TF-IDF sentiment, MiniLM semantic
> routing, and NMF for supporting aspect/topic intelligence.

Based on your project documentation and standard NLP research papers, here is how SignalShift positions itself and how it can be upgraded to "PhD-Level" quality.

## 📊 The Current Gap

| Feature | Typical Research Paper | SignalShift (Current) | SignalShift (Target) |
| :--- | :--- | :--- | :--- |
| **Dataset Size** | 2k - 65k reviews | **191k reviews** | 191k (Massive Scale) |
| **Model Count** | 1 - 2 models | Multi-stage (sentiment + semantic routing + topic intelligence) | Production-focused, measurable upgrades |
| **Features** | Simple text/TF-IDF | TF-IDF + Embeddings | **Feature Engineering (NLP specific)** |
| **Topic Model** | LDA (Traditional) | NMF + semantic category routing | Keep BERTopic as benchmark, not production default |
| **System** | Static code/Script | **Automated API + UI** | Real-time Product Intelligence |

## 🔑 Scientific Advantages of SignalShift
1. **End-to-End Pipeline**: Unlike most papers that are just notebooks, you have a live API and Frontend.
2. **Modern NLP Stack**: Semantic Sentence-Transformer routing + calibrated classical sentiment offers a stronger quality/speed balance for this dataset than BERTopic-as-default.
3. **Scale**: Your 191k dataset is already larger than most peer-reviewed samples.

## 📈 The Resume Narrative
*"Developed a research-grade NLP pipeline that benchmarked transformers and ensembles, then selected the best production stack (LR + semantic routing + NMF support) to analyze 190k+ user reviews."*
