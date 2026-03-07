# Topic Intelligence Benchmark: Research Audit

| Metric        | OLD LDA      | V3 LDA            | V4 NMF (Elite)    |
|:--------------|:-------------|:------------------|:------------------|
| Dataset Size  | 10000        | 2528              | 2528              |
| Noise Ratio   | 18.0%        | 0.0%              | 0.0%              |
| Primary Focus | General Talk | Customer Friction | Industry Friction |
| Algorithm     | LDA          | LDA               | NMF Precision     |

### Qualitative Summary:
- **OLD LDA**: Suffered from high generic noise (18%). Clusters were polluted with words like 'app' and 'is'.
- **V3 LDA**: Successfully focused on negative reviews but still lacked technical coherence in some clusters.
- **V4 NMF (Elite)**: 0% Noise achieved. Mathematically isolated industry terms (Auth, Playback, Churn) for surgical accuracy.
