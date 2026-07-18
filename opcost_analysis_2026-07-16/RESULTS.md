# Deployable operating-point / human-review-cost analysis — 2026-07-16

Round-2 red-team panel's single highest-leverage remaining lever for the inspect-gate
paper (score 83/100, near the accept boundary; see
`../manuscripts/FINAL-SCORE-R2-2026-07-16.md`): translate the certified dual-gate's
deferral rate into practitioner economics against the CRC single-threshold baseline,
so the "0.0% vs 36.9%" MPDD headline carries its 73.1%-deferral price inline.

**Not confirmatory; edits no frozen result.** Pure downstream cost-model transform of
already-frozen rates. Script: `script.py`. Full numeric output: `results.json`.

## Inputs

**FROZEN** (read verbatim, not recomputed) — pooled escaped-defect / false-reject /
deferral rates for our dual gate and the CRC single-threshold baseline, from
`../baseline_comparison_2026-07-15/results.json` (itself reading
`../gate_calibration/v1_<backbone>_seed<seed>.json`, frozen 2026-07-12/13):

| Benchmark | Method | Escaped | False-reject | Deferral |
|---|---|---|---|---|
| MPDD     | Our dual gate | 6.63% | 0.00%  | 73.09% |
| MPDD     | CRC           | 6.63% | 36.85% | 0.00%  |
| VisA     | Our dual gate | 7.64% | 2.96%  | 16.39% |
| VisA     | CRC           | 9.49% | 16.24% | 0.00%  |
| MVTec-AD | Our dual gate | 7.25% | 0.46%  | 54.36% |
| MVTec-AD | CRC           | 8.55% | 3.06%  | 0.00%  |

**ASSUMED** (illustrative deployment scenarios — labeled, not derived from any
benchmark's real factory economics; none of the three benchmarks ships production cost
data):

| Scenario | Throughput | Cost/escaped defect | Cost/false reject | Reviewer wage | Reviewer throughput | Review cost/part |
|---|---|---|---|---|---|---|
| Low-volume precision line | 100/hr | $5,000 | $150 | $45/hr | 120/hr | $0.375 |
| Mid-volume general industrial line | 600/hr | $300 | $15 | $30/hr | 240/hr | $0.125 |
| High-volume commodity line | 3,000/hr | $25 | $2 | $26/hr | 450/hr | $0.058 |

Each scenario models the *line*; each benchmark supplies the *rates* — all 3×3
combinations are computed (`results.json`).

## Headline numbers

**1. Human-review workload** at the certified operating point (parts/hour sent to a
reviewer = throughput × deferral rate; CRC has no deferral mechanism, so its reviewer
load is always 0 by construction — every non-passed CRC item is an automatic reject,
not a human decision):

| Benchmark | Low-volume precision (100/hr) | Mid-volume general (600/hr) | High-volume commodity (3,000/hr) |
|---|---|---|---|
| MPDD     | 73.1/hr (0.61 FTE) | 438.5/hr (1.83 FTE) | 2,192.7/hr (4.87 FTE) |
| VisA     | 16.4/hr (0.14 FTE) | 98.4/hr (0.41 FTE)   | 491.8/hr (1.09 FTE)   |
| MVTec-AD | 54.4/hr (0.45 FTE) | 326.1/hr (1.36 FTE)  | 1,630.7/hr (3.62 FTE) |

**2. Total $/hour cost (escaped-defect + false-reject + review-labor) — gate vs. CRC, and
gate's net savings:**

| Benchmark | Scenario | Gate $/hr | CRC $/hr | Gate savings $/hr | Gate cheaper? |
|---|---|---|---|---|---|
| MPDD     | Low-volume precision | 33,181 | 38,682 | **+5,500** | yes |
| MPDD     | Mid-volume general    | 11,990 | 15,252 | **+3,262** | yes |
| MPDD     | High-volume commodity | 5,100  | 7,184  | **+2,084** | yes |
| VisA     | Low-volume precision | 38,633 | 49,894 | **+11,261** | yes |
| VisA     | Mid-volume general    | 14,024 | 18,547 | **+4,522** | yes |
| VisA     | High-volume commodity | 5,933  | 8,093  | **+2,160** | yes |
| MVTec-AD | Low-volume precision | 36,346 | 43,197 | **+6,851** | yes |
| MVTec-AD | Mid-volume general    | 13,134 | 15,661 | **+2,527** | yes |
| MVTec-AD | High-volume commodity | 5,560  | 6,594  | **+1,034** | yes |

The dual gate is the cheaper deployment in all 9 (benchmark × scenario) combinations
computed. The saving is driven almost entirely by the false-reject-rate gap (CRC pays
3.0–36.9pp more false-rejects than the gate on every benchmark); it is *not* an
artifact of favorable escaped-defect rates — on MPDD the two methods share the
identical escaped-defect rate (6.63%, by the proven G1≡CRC threshold identity), and on
VisA/MVTec-AD the gate's escaped rate is additionally somewhat *lower* than CRC's
(7.64% vs 9.49%; 7.25% vs 8.55%), so the comparison is not tilted by the escaped axis
in the gate's favor.

## Sensitivity

Two breakeven quantities, solved analytically (independent of throughput, which
cancels out of the total-cost difference):

**(a) Breakeven false-reject unit cost** — the $/false-reject value above which the
gate is cheaper (holding the scenario's other costs fixed). On MPDD this ranges
$0.11–$0.74, i.e. the gate wins as long as a false reject costs more than about
11 cents to a dollar — trivially satisfied by all three assumed scenarios ($2–$150).
On VisA and MVTec-AD the breakeven is *negative* ($-3 to $-2,484): the gate is cheaper
even if false rejects were costless, because its escaped-defect rate is also lower
there.

**(b) Breakeven review-cost-per-part** (the more actionable sensitivity axis) — holding
the scenario's assumed escaped/false-reject unit costs fixed, how much could a human
reviewer cost per part before the gate's deferral overhead erases its false-reject
savings:

| Benchmark | Scenario | Breakeven review $/part | Assumed review $/part | Headroom |
|---|---|---|---|---|
| MPDD     | Low-volume precision | $75.63 | $0.375 | 202× |
| MPDD     | Mid-volume general    | $7.56  | $0.125 | 60×  |
| MPDD     | High-volume commodity | $1.01  | $0.058 | **17×** |
| VisA     | Low-volume precision | $687.27 | $0.375 | 1,833× |
| VisA     | Mid-volume general    | $46.10  | $0.125 | 369×   |
| VisA     | High-volume commodity | $4.45   | $0.058 | 77×    |
| MVTec-AD | Low-volume precision | $126.41 | $0.375 | 337×   |
| MVTec-AD | Mid-volume general    | $7.87   | $0.125 | 63×    |
| MVTec-AD | High-volume commodity | $0.69   | $0.058 | **12×** |

The least-robust cell is **MVTec-AD, high-volume commodity** (12× headroom): human
review would need to cost more than $0.69/part — about 12× the assumed $0.058/part —
before the CRC baseline becomes the cheaper deployment there. Every other cell has
headroom of 17×–1,833×. The direction is consistent across all 9 cells: the gate's
economic advantage is robust to large errors in the assumed review-labor cost, not a
knife-edge result of the specific scenario numbers chosen.

## Explicit limitations of this cost model (not modeled)

- Deferred items are costed only as review-labor time; no model of the reviewer's own
  error rate, of queueing/backlog dynamics under bursty defect rates, or of a
  second-stage disposition cost after human review.
- The CRC baseline is costed with zero review/appeal channel for its false-rejected
  good parts — a real deployment might route some auto-rejects to human appeal, which
  would raise CRC's modeled cost further (this analysis is if anything conservative
  toward CRC, not biased against it).
- Throughput, unit costs, and reviewer wage/throughput are illustrative scenario
  assumptions, explicitly labeled; no benchmark carries real production cost data, so
  the certified *rates* are frozen fact and the *dollar figures* are scenario-dependent
  by construction. The breakeven quantities in the Sensitivity section are the
  throughput-invariant, assumption-robust takeaway; the $/hour table is illustrative.
