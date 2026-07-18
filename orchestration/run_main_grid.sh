#!/usr/bin/env bash
# Main-grid run SKELETON (design §7 Phase 2): 15 categories x 5 backbone
# seeds x 2 backbones = 150 fitted backbone cells, x R=20 calibration
# repeats = 3,000 calibration/eval runs (design §3.3 grid arithmetic).
#
# Structure only, like asr-gate's run_expansion.sh -- this is NOT meant to
# run unattended. Guarded by REQUIRES_PREREG_FREEZE: an amendment
# preregistering targets (alpha_miss=0.10, alpha_fr=0.05), the 6-test Holm
# audit family, the split protocol (R=20, 50/50 stratified), the
# certifiability floor table (F6), and the K1-K7 kill-criteria thresholds
# must land and be confirmed before this touches the full 15-category grid,
# per the portfolio's preregistration discipline -- exactly mirroring
# asr-gate/orchestration/run_expansion.sh's own guard.
#
# next_boot_inspect_gate.sh (the Phase-0 + Phase-1 PILOT chain, 3
# categories x 2 backbones x 2 seeds) is the one that actually runs
# unattended today; this file exists so the main-grid shape is visible and
# reviewable before any compute is spent on it.

set -euo pipefail

if [ "${REQUIRES_PREREG_FREEZE:-}" != "confirmed" ]; then
  cat >&2 <<'EOF'
run_main_grid.sh: REFUSING TO RUN.

This sketches the FULL main grid (15 categories x 5 seeds x 2 backbones x
R=20 repeats, apps-design/01-APP-mvtec-triage.md §3.3/§7 Phase 2). It may
only run once:
  1. next_boot_inspect_gate.sh's Phase-0 + Phase-1 pilot has closed the
     loop end-to-end on bottle/screw/carpet x 2 backbones x 2 seeds, with
     K1/K2/K3/K5 (design §4) checked clean on the pilot cells;
  2. a PREREG-DRAFT amendment freezes: alpha_miss/alpha_fr targets, the
     confirmatory Holm family (3 practices x 2 backbones = 6, or the
     realized roster if a backbone is unavailable -- disclosed, never
     silently re-hardcoded), the R=20 split protocol, the certifiability-
     floor table (F6, per-category n_def_cal/n_good_cal/alpha_min), and
     the K1-K7 kill-criteria thresholds (design §4);
  3. the §1 citation scan is re-run (K6, scoop gate) at freeze time.

Set REQUIRES_PREREG_FREEZE=confirmed once all three are actually true.
This script is a structure-only skeleton either way -- read it before
trusting it with real compute (per asr-gate/orchestration/
run_expansion.sh's identical precedent).
EOF
  exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RESULTS_DIR="${RESULTS_DIR:-/root/autodl-tmp/inspect_gate_main_results}"
DATA_ROOT="${INSPECT_GATE_DATA_ROOT:-/root/autodl-tmp/mvtec_ad}"
DEVICE="${DEVICE:-cuda}"
ALPHA_MISS="${ALPHA_MISS:-0.10}"
ALPHA_FR="${ALPHA_FR:-0.05}"
N_REPEATS="${N_REPEATS:-20}"
N_SEEDS="${N_SEEDS:-5}"
AUDIT_N_PERM="${AUDIT_N_PERM:-2000}"

mkdir -p "$RESULTS_DIR"

step() { echo "== $1 =="; }

step "Stage A: score all 15 categories x N_SEEDS x {patchcore,dinomaly}"
echo "TODO: for seed in \$(seq 0 \$((N_SEEDS-1))); do" \
     "score_patchcore.py --category <all 15, comma-joined> --seed \$seed ...;" \
     "score_dinomaly.py --mode dump-ingest --scores-dump <per-seed dump> ...; done" \
     "(mirrors stage_2_score() in next_boot_inspect_gate.sh, all 15 categories)"

step "Stage B: reproduction gate on seed-0 scores (binding, per SOTA-REPRODUCTION-PLAN §3)"
echo "TODO: phase0.py --patchcore-scores ... --dinomaly-scores ... -o reproduction.json;" \
     "ABORT the grid if reproduction_gate_pass is False (design §3.6: 'no gate" \
     "result is reportable until fixed')"

step "Stage C: per (backbone, category, seed) run_pilot_cell.py, N_REPEATS=20"
echo "TODO: for backbone in patchcore dinomaly; do for category in <all 15>; do" \
     "for seed in \$(seq 0 \$((N_SEEDS-1))); do run_pilot_cell.py --scores" \
     "scores_\${backbone}_seed\${seed}.jsonl --category \$category --n-repeats" \
     "$N_REPEATS --alpha-miss $ALPHA_MISS --alpha-fr $ALPHA_FR -o" \
     "cell_\${backbone}_\${category}_seed\${seed}.json; done; done; done" \
     "(150 fitted-backbone cells x 20 repeats = 3,000 calibration/eval runs," \
     "design §3.3 arithmetic)"

step "Stage D: pool V1 across seeds (design F2/T3) + roster-derived global Holm audit"
echo "TODO: aggregate_v1_cells across ALL seeds' repeat cells per (category," \
     "backbone) -- design's tier-2 pooling is per (category,backbone), so" \
     "seeds pool into the SAME n_eval_def_total the pilot's single-seed call" \
     "does not; combine the per-seed 'inspect-gate audit' Holm families into" \
     "ONE global family exactly like asr-gate's next_boot_asr_expansion.sh" \
     "Stage D combined-Holm python block -- m computed from the REALIZED" \
     "roster, never hardcoded to 6"

step "Stage E: K1/K2/K4/K5/K7 kill-gate report + F1-F6/T1-T6 regeneration from result JSONs"
echo "TODO: certify.coverage_sanity_check_k1 / vacuity_check_k2 over all 30" \
     "V1 cells; K4 audit-headroom check (design §4, not yet a certify.py" \
     "function -- add if/when the main grid needs it); K7 compute-guard" \
     "check against the measured Phase-0 bench (design §3.6)"

echo "main-grid run skeleton complete -> $RESULTS_DIR"
echo "This is structure only -- every Stage above must be filled in against" \
     "the frozen PREREG-DRAFT amendment before this does anything beyond" \
     "printing TODOs."
