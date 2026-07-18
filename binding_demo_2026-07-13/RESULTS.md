# Binding demonstration — "when a fixed threshold over-promises" (M4) — 2026-07-13

Compute-only run on cached MVTec-AD + VisA scores (CPU). No manuscript edited by this script.
Runner + result JSON live beside this file. This closes the deepest red-team wound (M4 /
MAJOR-2): it exhibits concrete (backbone, category) cells where a **naive fixed threshold
violates the escaped-defect or false-reject target while the certified gate holds** on the
same held-out eval data. Reported honestly; not manufactured.

---

## HEADLINE — the certificate binds, decisively, and it is NOT just "the gate defers everything"

**Violation cells exist on both benchmarks, both axes, both backbones, and they are
cross-seed stable.** Restricting to the strongest evidence — cells where the gate is
**certified on that axis in all 20 repeats** AND the bind holds in **all 5 backbone seeds**
(B1 over target, gate within target+tolerance) — there are **27**:

| | escaped axis (α_miss=0.10) | false-reject axis (α_fr=0.05) |
|---|---|---|
| **MVTec AD** | 3 (dinomaly: capsule, pill, screw) | 3 (patchcore:screw, dinomaly:cable, dinomaly:transistor) |
| **VisA** | 4 (patchcore:pcb3, dinomaly: candle, macaroni1, macaroni2) | 17 (11 patchcore + 6 dinomaly cells) |

The cleanest cases have **low deferral cost**, refuting the obvious rebuttal ("the gate only
wins by abstaining on everything"):

| cell | axis | B1 realized rate | gate realized rate | gate deferral | gate certified |
|---|---|---|---|---|---|
| MVTec dinomaly:**screw** | escaped | **0.242** | 0.080 | **0.04** | G1 ✓ |
| VisA dinomaly:**candle** | escaped | **0.214** | 0.079 | **0.04** | G1 ✓ |
| VisA dinomaly:**macaroni2** | escaped | **0.480** | 0.078 | 0.19 | G1 ✓ |
| MVTec dinomaly:**transistor** | false-reject | **0.168** | 0.022 | **0.10** | G2 ✓ |
| MVTec patchcore:**screw** | false-reject | **0.195** | 0.050 | 0.14 | G2 ✓ |
| VisA dinomaly:**pcb2** | false-reject | **0.354** | 0.025 | **0.05** | G2 ✓ |
| VisA patchcore:**capsules** | false-reject | **0.968** | 0.037 | 0.65 | G2 ✓ |

Read the top row: a single global best-F1 threshold lets **24% of defective screws escape**;
the certified gate, deferring just **4%** of images, holds the escaped rate at **8%** — under
the 10% target — because its per-category (Mondrian) calibration puts the auto-pass boundary
where a global threshold cannot. VisA patchcore:capsules is the extreme false-reject case: the
global threshold would auto-reject **97% of good capsules**; the gate holds false-reject at
**3.7%** (certified) at a 65%-deferral cost it discloses.

**The mechanism the demo exposes:** a naive fixed *global* threshold cannot simultaneously
serve categories with different score scales; it over-promises on whichever categories it
mis-fits. The certified gate refuses (defers) exactly where it cannot honor the target, and
elsewhere calibrates per category — so its realized rates stay within target where the fixed
threshold badly exceeds it.

---

## Construction (zero new statistics; all realized on held-out eval halves)

Per (benchmark, backbone, backbone-seed, repeat) a 50/50 stratified cal/eval split (design
§3.2, R=20 repeats):

* **Naive practitioner = B1**: one global best-F1 threshold fit on the **pooled** calibration
  half, applied to every eval image with **no deferral** (`score ≥ thr` → auto-reject, else
  auto-pass). Per category on the eval half:
  `escaped = #(defective, score < thr)/#defective`,
  `false-reject = #(good, score ≥ thr)/#good` — exactly the `certify.coverage_cell`
  definitions, fixed-threshold and abstention-free.
* **Certified gate**: `calibrate_gate(pooled cal, mondrian="category")`, routed over the eval
  half; realized per-category escaped / false-reject via `certify.coverage_cell` (deferred
  images are **not** counted as escaped / false-reject — they go to human review). Deferral
  rate reported per cell.

**Binding cell (tier-1 style, mean over R=20 repeats at backbone seed 0):**
escaped-axis = `B1 mean escaped > 0.10 AND gate mean escaped ≤ 0.13`;
false-reject-axis = `B1 mean FR > 0.05 AND gate mean FR ≤ 0.08` (tol = 0.03, the
`v1_pass_tier1` default). The **certified + cross-seed-stable** subset additionally requires
the gate to be certified on that axis in all 20 repeats and the bind to hold in all 5 backbone
seeds. The repeat-0 single split (the C2/B3 audit's split) is also stored per cell.

**Excluded from the certified headline (but retained in `results.json`):** false-reject cells
where the gate is *not* G2-certified (e.g. MVTec patchcore:toothbrush, B1=0.275, gate=0.000,
deferral=0.75, g2cert=0.00). There the gate's realized false-reject is 0 because it **refuses**
G2 for that category (auto-reject region empty), not because it holds a certified bound — that
is honest refusal, not a binding certificate, so it does not count as "the gate catches it."

---

## Label

**POST-HOC / EXPLORATORY.** This is the M4 illustration the red-team requested, not a
preregistered confirmatory arm. It is verdict-honest: had no violation cell existed, the paper
would have kept its "not demonstrated" framing. Violation cells do exist, so a short "When a
fixed threshold over-promises" subsection (exploratory label) is warranted.

Full per-cell numbers (B1 and gate escaped/FR means, ranges over R=20, per-seed means,
deferral, certification fractions) and both benchmarks: `results.json`.

---

## Reproduce

```
cd reliability-commons/tools/inspect-gate
PYTHONPATH=$(pwd)/../.. .venv/bin/python binding_demo_2026-07-13/run_binding_demo.py
```
