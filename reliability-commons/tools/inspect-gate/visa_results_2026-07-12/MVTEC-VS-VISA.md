# MVTec-AD vs VisA cross-benchmark table (JIM paper, second-benchmark section)

Re-aggregated 2026-07-12 from primary JSONs only (no memo numbers).
Protocol identical on both benchmarks: 5 seeds, R=20 stratified repeats,
alpha_miss=0.10, alpha_fr=0.05, primary (--good-cal test) protocol,
exploratory audit fixed+tuned, n_perm=2000, per-cell Holm.

| Benchmark | Backbone | mean I-AUROC (5 seeds) | repro target | repro pass | G1 cert. | G2 cert. (primary) | V1 tier-1 cells | K1+K2 seed trips | audit Holm rejects | median deferral |
|---|---|---|---|---|---|---|---|---|---|---|
| MVTec-AD | patchcore | 0.9820 ± 0.0004 | 0.991 | 5/5 | 15/15 | 4/15 | 75/75 | 0+0 | 48/150 | 0.707 |
| MVTec-AD | dinomaly | 0.9960 ± 0.0003 | 0.996 | 5/5 | 15/15 | 4/15 | 75/75 | 0+0 | 4/150 | 0.694 |
| VisA | patchcore | 0.9054 ± 0.0018 | n/a* | n/a* | 12/12 | 12/12 | 60/60 | 0+0 | 64/120 | 0.194 |
| VisA | dinomaly | 0.9870 ± 0.0004 | 0.987 | 5/5 | 12/12 | 12/12 | 60/60 | 0+0 | 42/120 | 0.040 |

*PatchCore-on-VisA has no repo-confirmed published image-AUROC figure, so its
reproduction row is descriptive (target n/a), per the tool's no-guessed-target rule.

## Reading

- VisA is the lower-ceiling benchmark the workload-gap memo asked for: PatchCore drops from 0.982 (MVTec) to 0.905 (VisA) mean I-AUROC; Dinomaly holds (0.996 -> 0.987, reproduction-gated 5/5 vs the paper's published 0.987 VisA figure).
- Audit informativeness: MVTec Dinomaly rejected 4/150 (ceiling effect); VisA Dinomaly rejects 42/120; VisA PatchCore rejects 64/120 (MVTec: 48/150).
- G2 counts above are the primary protocol on both benchmarks; the train-holdout
  promotion arm (computed 2026-07-12, MVTec, PatchCore only -- Dinomaly has no
  train-side score dump) is reported separately.
- K1+K2 column: number of seeds (of 5) tripping each kill-gate; 0+0 everywhere
  on both benchmarks.
