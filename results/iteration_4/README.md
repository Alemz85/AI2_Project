## Iteration 4 — Classification

**Change:** Reframed as multi-class classification instead of regression.

**Classes:**
| Class | Load Range | Dataset % |
|-------|-----------|-----------|
| Idle | < 0.1 kWh | 56.4% |
| Low | 0.1 – 5 kWh | 25.3% |
| Medium | 5 – 20 kWh | 13.8% |
| High | ≥ 20 kWh | 4.5% |

**Rationale:** EV charging is event-driven — exact kWh prediction is hard (R² = 0.514).
Grid operators often need demand *level* rather than exact values for DR scheduling.

**Best model:** LightGBM (tuned) — 81% accuracy, 0.67 macro F1, zero overfitting
**Per-class F1:** Idle=0.92, Low=0.72, Medium=0.58, High=0.46
**vs Regression (binned):** 80.8% vs 42.3% accuracy, 0.670 vs 0.440 macro F1

**Notebooks:** `scripts/08 - Modeling (Classification).ipynb`, `scripts/09 - Classification Error Analysis.ipynb`
