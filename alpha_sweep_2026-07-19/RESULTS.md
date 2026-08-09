# L1 — α-frontier sweep (post-freeze exploratory, prereg F4 slot) — 2026-07-19

**POST-FREEZE EXPLORATORY. Not confirmatory; edits no frozen result.** Re-runs the
frozen Stage-3 protocol (`splits.repeated_stratified_splits` R=20 → `calibrate_gate` →
`route_gate`, byte-identical code path to `analysis_2026-07-10` / `visa_results_2026-07-12`
/ `mpdd_results_2026-07-13` run_*_analysis.py) across a grid of operating points:
α_miss ∈ {0.20, 0.10, 0.05, 0.02, 0.01} × α_fr ∈ {0.10, 0.05, 0.02}, all 3 benchmarks ×
2 backbones × 5 seeds. Script: `script.py`. Full numeric output: `results.json`.
Figure: `../figures_2026-07-19/fig-alphafrontier.pdf` (also in `manuscripts/figures-src/`).

**Replication check (load-bearing):** at the paper's operating point (0.10, 0.05) the
sweep reproduces every frozen `v1_{backbone}_seed0.json` — per-category tier-1 mean
escaped rates and median deferral — with max abs diff **0.0** on all 6
(benchmark × backbone) pairs.

## Motivation

The paper's Limitations proves arithmetically that at α_miss=0.01 the calibration floors
collapse certification to 33/33 refusals, but never shows the sweep. This arm converts
that defensive paragraph into a controlled result: the deferral price of tighter
operating points, and the exact α at which floors bind.

## Headline (α_fr = 0.05; deferral = mean over 5 seeds of overall mean deferral;
cert = fraction of categories both-axis certified, primary protocol)

| Benchmark | Backbone | α=0.20 | α=0.10 (op. point) | α=0.05 | α=0.02 | α=0.01 |
|---|---|---|---|---|---|---|
| MVTec-AD | patchcore | def .487 cert .27 | def .548 cert .27 | def .611 cert .27 | def .826 cert .07 | def .860 cert **0.00** |
| MVTec-AD | dinomaly  | def .495 cert .27 | def .539 cert .27 | def .582 cert .27 | def .800 cert .07 | def .845 cert **0.00** |
| VisA | patchcore | def .203 cert 1.00 | def .263 cert 1.00 | def .334 cert 1.00 | def .388 cert 1.00 | def .607 cert **0.00** |
| VisA | dinomaly  | def .086 cert 1.00 | def .065 cert 1.00 | def .087 cert 1.00 | def .129 cert 1.00 | def .491 cert **0.00** |
| MPDD | patchcore | def .513 cert 0.00 | def .751 cert 0.00 | def .851 cert 0.00 | def 1.000 cert 0.00 | def 1.000 cert 0.00 |
| MPDD | dinomaly  | def .496 cert 0.00 | def .711 cert 0.00 | def .853 cert 0.00 | def 1.000 cert 0.00 | def 1.000 cert 0.00 |

## Reading

1. **VisA can tighten.** Both axes certify in 12/12 categories down to α_miss=0.02 at
   modest price (Dinomaly deferral 6.5%→12.9%; PatchCore 26.3%→38.8%). At α_miss=0.01 the
   floors bind and certification collapses to 0/12 — the sweep shows the cliff, not just
   asserts it.
2. **MVTec's ceiling is pool-size, not α.** Both-certified fraction is pinned at 0.27
   (4/15 — the G2 good-pool floors the train-holdout remedy addresses,
   `g2_promotion_2026-07-12`) across α ≥ 0.05; below 0.05 the defective-side floors start
   binding, and at 0.01 certification is 0/15. Deferral worsens smoothly
   (0.55→0.83–0.86) as α_miss tightens to 0.02.
3. **MPDD confirms the stingy extreme.** 0 both-certified at every grid point (G2 floors
   everywhere on the primary protocol — the holdout rescue `mpdd_results_2026-07-13` is
   the remedy); deferral saturates at 1.00 from α_miss=0.02 down.
4. The full 15-point grid (3 α_fr values) is in `results.json`; the figure fixes
   α_fr=0.05 for legibility. Per-repeat certification counts and per-category rates are
   preserved for any reviewer follow-up.
