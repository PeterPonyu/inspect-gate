#!/usr/bin/env bash
# next_boot_inspect_gate.sh -- Phase-0 + Phase-1 PILOT boot chain for
# inspect-gate (apps-design/01-APP-mvtec-triage.md §7, ADDENDUM
# 2026-07-10 backbone roster). Sources
# reliability-commons/tools/boxkit/chain_lib.sh's chain_prologue/
# chain_epilogue (the standing boxkit convention -- see that file's
# header) rather than reimplementing prologue/epilogue inline.
#
# Stages:
#   0. chain_prologue (conda activate, HF_HOME, balance_guard, gpu logger --
#      all pidfile-guarded, per chain_lib.sh's ABSOLUTE RULE: never
#      pkill-by-pattern where the invocation's own command line contains
#      the pattern).
#   1. Stage: untar MVTec AD from AUTODL_PUB_MVTEC_PATH -> DATA_ROOT,
#      freeze per-category counts (phase0.py).
#   2. Score the 3 pilot categories (bottle, screw, carpet -- design §7:
#      "3 categories spanning the structure") x 2 backbones x 2 seeds.
#      PatchCore via score_patchcore.py (anomalib, real GPU inference).
#      Dinomaly via score_dinomaly.py's dump-ingest mode -- REQUIRES a
#      score dump the operator produced by running the real Dinomaly
#      checkout's own eval script beforehand (score_dinomaly.py's module
#      docstring explains why --mode direct refuses rather than guessing
#      an unverified API); missing dump -> SKIPPED_DISCLOSED, the pilot
#      continues on PatchCore alone rather than blocking entirely.
#   3. Phase-0 reproduction gate (BINDING per
#      SOTA-REPRODUCTION-PLAN-2026-07-10.md §3): each backbone's seed-0
#      image-AUROC vs its target within tolerance, before any gate
#      calibration work. K3 (design §4: mean AUROC < 0.90 for either
#      backbone) is asserted here too, as a broader sanity floor
#      alongside the tighter target-vs-tolerance reproduction check.
#   4. Per (backbone, category, seed): run_pilot_cell.py (R=
#      PILOT_N_REPEATS repeats, NOT the main grid's R=20 -- keeps the
#      pilot loop cheap; see the "Tunables" section) -> calibrate/route/
#      certify/audit, content-gated markers.
#   5. Epilogue via chain_lib.sh's chain_epilogue, marker
#      INSPECT_GATE_PILOT_ALL_DONE.
#
# Every completion marker below asserts on RESULT CONTENT (row counts,
# non-null score fractions, pass_tier1 booleans), never a bare exit code
# -- the same DOFA-lesson discipline asr-gate's boot chains follow.
#
# The FULL main grid (15 categories x 5 seeds x 2 backbones, R=20) is
# NOT sketched in this file at all -- it stays behind
# REQUIRES_PREREG_FREEZE=confirmed exactly like asr-gate's
# run_expansion.sh precedent; see that file's header for the pattern this
# one mirrors once the main-grid script exists.
#
# Usage (on the AutoDL box): bash next_boot_inspect_gate.sh
# (or: nohup bash next_boot_inspect_gate.sh > /root/inspect_gate_boot.log 2>&1 &)

set -uo pipefail  # deliberately NOT -e: later stages/markers/epilogue must
                   # still run after an earlier stage's content gate fails.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RELIABILITY_COMMONS="${RELIABILITY_COMMONS:-/root/reliability-commons}"

# ---------------------------------------------------------------------------
# Tunables (env-overridable, named defaults -- ABSOLUTE RULE: no hardcoded
# paths/model IDs/statistical denominators inline in the stages below).
# ---------------------------------------------------------------------------
RESULTS_DIR="${RESULTS_DIR:-/root/autodl-tmp/inspect_gate_pilot_results}"
# /root/autodl-tmp/mvtec_ad is what the staged box actually uses (verified
# on-box 2026-07-10) -- THE named default, mirrored in phase0.py's
# DEFAULT_DATA_ROOT and ig_fullscore.sh's DATA_ROOT; still env-overridable.
DATA_ROOT="${INSPECT_GATE_DATA_ROOT:-/root/autodl-tmp/mvtec_ad}"
AUTODL_PUB_MVTEC_PATH="${AUTODL_PUB_MVTEC_PATH:-/root/autodl-pub/mvtec_anomaly_detection.tar.xz}"
DEVICE="${DEVICE:-cuda}"

PILOT_CATEGORIES="${PILOT_CATEGORIES:-bottle screw carpet}"  # design §7
PILOT_SEEDS="${PILOT_SEEDS:-0 1}"                              # design §7: x2 seeds
PILOT_N_REPEATS="${PILOT_N_REPEATS:-5}"                        # main grid uses R=20; pilot keeps it cheap
ALPHA_MISS="${ALPHA_MISS:-0.10}"
ALPHA_FR="${ALPHA_FR:-0.05}"
AUROC_TOLERANCE="${AUROC_TOLERANCE:-0.02}"
K3_MIN_AUROC="${K3_MIN_AUROC:-0.90}"                            # design §4 K3
AUDIT_N_PERM="${AUDIT_N_PERM:-2000}"

DINOMALY_SCORES_DUMP_SEED0="${DINOMALY_SCORES_DUMP_SEED0:-}"  # operator-provided, see stage_2 header
DINOMALY_SCORES_DUMP_SEED1="${DINOMALY_SCORES_DUMP_SEED1:-}"

HF_HOME="${HF_HOME:-/root/autodl-tmp/hf-cache}"
INSPECT_GATE_LOG="${INSPECT_GATE_LOG:-/root/inspect_gate_pilot.log}"
GPU_UTIL_LOG="${GPU_UTIL_LOG:-/root/gpu_util.log}"

MARKERS_DIR="${MARKERS_DIR:-$RESULTS_DIR/markers}"
mkdir -p "$RESULTS_DIR" "$MARKERS_DIR"

FAILED_MARKERS=()
DINOMALY_AVAILABLE=1

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

step() { echo "== $1 =="; }
skip() { echo "skip (already exists): $1"; }

# No-card guard (M2): a no-card box has a 2GB quota -- attempting a
# score_patchcore.py model load on one OOMs. Probe BEFORE Stage 2 (the
# first score invocation) and refuse to proceed to any model load if
# nvidia-smi is unavailable or reports zero devices.
assert_gpu_present() {
  local gpu_list
  if ! gpu_list="$(nvidia-smi -L 2>/dev/null)" || [ -z "$gpu_list" ]; then
    echo "IG_NO_GPU_ABORT: nvidia-smi -L failed or reported no devices -- " \
         "refusing to attempt any model load (no-card boxes have a 2GB " \
         "quota; a model load OOMs)." >&2
    return 1
  fi
  return 0
}

mark() {
  # mark NAME STATUS  (STATUS: OK|FAILED|DEGRADED|SKIPPED_DISCLOSED)
  local name="$1" status="$2"
  printf '%s\n' "$status" > "$MARKERS_DIR/${name}.marker"
  echo "MARKER ${name}=${status}"
  if [ "$status" = "FAILED" ]; then
    FAILED_MARKERS+=("$name")
  fi
}

# Content-gated: n_scored > 0 and a non-null score fraction, read straight
# from a scores-JSONL (never trusts a bare exit code -- DOFA-lesson
# discipline, same convention as asr-gate's boot chains).
assert_scores_content() {
  local path="$1" min_rows="${2:-1}"
  [ -s "$path" ] || { echo "CONTENT_GATE_FAIL $path: file missing/empty" >&2; return 1; }
  python3 - "$path" "$min_rows" <<'PYEOF'
import json, sys
path, min_rows = sys.argv[1], int(sys.argv[2])
n = 0
for line in open(path, encoding="utf-8"):
    line = line.strip()
    if not line:
        continue
    rec = json.loads(line)
    if rec.get("score") is None:
        print(f"CONTENT_GATE_FAIL {path}: null score at image_id={rec.get('image_id')}", file=sys.stderr)
        sys.exit(1)
    n += 1
if n < min_rows:
    print(f"CONTENT_GATE_FAIL {path}: n={n} < min_rows={min_rows}", file=sys.stderr)
    sys.exit(1)
print(f"CONTENT_GATE_OK {path}: n={n}")
PYEOF
}

assert_pass_tier1() {
  local path="$1" category="$2"
  [ -s "$path" ] || { echo "CONTENT_GATE_FAIL $path: file missing/empty" >&2; return 1; }
  python3 - "$path" "$category" <<'PYEOF'
import json, sys
path, category = sys.argv[1], sys.argv[2]
with open(path, encoding="utf-8") as f:
    result = json.load(f)
rec = result["v1"]["per_category"].get(category)
if rec is None:
    print(f"CONTENT_GATE_FAIL {path}: no V1 record for category={category}", file=sys.stderr)
    sys.exit(1)
if not rec["tier1"]["pass_tier1"]:
    print(f"CONTENT_GATE_FAIL {path}: category={category} tier1={rec['tier1']}", file=sys.stderr)
    sys.exit(1)
print(f"CONTENT_GATE_OK {path}: category={category} pass_tier1=True")
PYEOF
}

# ---------------------------------------------------------------------------
# Stage 0: prologue (chain_lib.sh)
# ---------------------------------------------------------------------------

source "${RELIABILITY_COMMONS}/tools/boxkit/chain_lib.sh"
export HF_HOME
# CHAIN_LOG must be set+exported BEFORE chain_prologue/chain_epilogue run,
# same as ig_fullscore.sh's L/CHAIN_LOG convention -- otherwise
# chain_epilogue's markers land in chain_lib.sh's own default log
# (/root/chain.log), not the log this script announces and tees to below.
export CHAIN_LOG="$INSPECT_GATE_LOG"
chain_prologue

mkdir -p "$(dirname "$INSPECT_GATE_LOG")" 2>/dev/null || true
exec > >(tee -a "$INSPECT_GATE_LOG") 2>&1
echo "logging to $INSPECT_GATE_LOG"

# ---------------------------------------------------------------------------
# Stage 1: dataset staging + frozen counts (phase0.py, --counts-only skipped
# -- this call DOES stage, unlike the reproduction-gate calls in stage 3
# which reuse the already-extracted data_root).
# ---------------------------------------------------------------------------

stage_1_staging() {
  step "Stage 1: stage MVTec AD + freeze per-category counts"
  local out="$RESULTS_DIR/phase0_staging.json"
  if python3 "$SCRIPT_DIR/phase0.py" \
       --autodl-pub-path "$AUTODL_PUB_MVTEC_PATH" --data-root "$DATA_ROOT" \
       --skip-reproduction-gate -o "$out"; then
    mark STAGE1_STAGING OK
  else
    mark STAGE1_STAGING FAILED
    return 1
  fi
}

# ---------------------------------------------------------------------------
# Stage 2: score the 3 pilot categories x 2 backbones x 2 seeds.
# ---------------------------------------------------------------------------

stage_2_score() {
  step "Stage 2: score pilot categories x {patchcore,dinomaly} x {${PILOT_SEEDS}}"
  local seed cat_csv="${PILOT_CATEGORIES// /,}"

  for seed in $PILOT_SEEDS; do
    local pc_out="$RESULTS_DIR/scores_patchcore_seed${seed}.jsonl"
    if [ -s "$pc_out" ]; then
      skip "$pc_out"
    else
      python3 "$SCRIPT_DIR/score_patchcore.py" \
        --data-root "$DATA_ROOT" --category "$cat_csv" --seed "$seed" \
        --device "$DEVICE" --out "$pc_out" \
        || echo "warning: score_patchcore.py seed=$seed exited non-zero -- content gate below will catch it"
    fi
    if assert_scores_content "$pc_out" 1; then
      mark "SCORE_patchcore_seed${seed}" OK
    else
      mark "SCORE_patchcore_seed${seed}" FAILED
    fi
  done

  for seed in $PILOT_SEEDS; do
    local dump_var="DINOMALY_SCORES_DUMP_SEED${seed}"
    local dump_path="${!dump_var:-}"
    local dn_out="$RESULTS_DIR/scores_dinomaly_seed${seed}.jsonl"
    if [ -z "$dump_path" ] || [ ! -s "$dump_path" ]; then
      echo "note: no DINOMALY_SCORES_DUMP_SEED${seed} provided/found -- Dinomaly" \
           "requires a score dump from the real checkout's own eval script" \
           "(score_dinomaly.py module docstring); SKIPPED_DISCLOSED, pilot" \
           "continues on PatchCore alone for this seed."
      mark "SCORE_dinomaly_seed${seed}" SKIPPED_DISCLOSED
      continue
    fi
    if [ -s "$dn_out" ]; then
      skip "$dn_out"
    else
      python3 "$SCRIPT_DIR/score_dinomaly.py" \
        --mode dump-ingest --data-root "$DATA_ROOT" --category "$cat_csv" \
        --scores-dump "$dump_path" --out "$dn_out" \
        || echo "warning: score_dinomaly.py seed=$seed exited non-zero -- content gate below will catch it"
    fi
    if assert_scores_content "$dn_out" 1; then
      mark "SCORE_dinomaly_seed${seed}" OK
    else
      mark "SCORE_dinomaly_seed${seed}" FAILED
      DINOMALY_AVAILABLE=0
    fi
  done

  if [ ! -s "$RESULTS_DIR/scores_dinomaly_seed0.jsonl" ]; then
    DINOMALY_AVAILABLE=0
  fi
}

# ---------------------------------------------------------------------------
# Stage 3: Phase-0 reproduction gate (BINDING) + K3 sanity floor, seed-0
# scores, before any gate-calibration work.
# ---------------------------------------------------------------------------

stage_3_reproduction_gate() {
  step "Stage 3: reproduction gate (binding) + K3 sanity floor"
  local pc_scores="$RESULTS_DIR/scores_patchcore_seed0.jsonl"
  local args=(--data-root "$DATA_ROOT" --category "${PILOT_CATEGORIES// /,}" --counts-only
              --auroc-tolerance "$AUROC_TOLERANCE" -o "$RESULTS_DIR/phase0_reproduction.json")
  [ -s "$pc_scores" ] && args+=(--patchcore-scores "$pc_scores")
  if [ "$DINOMALY_AVAILABLE" -eq 1 ]; then
    args+=(--dinomaly-scores "$RESULTS_DIR/scores_dinomaly_seed0.jsonl")
  fi

  if python3 "$SCRIPT_DIR/phase0.py" "${args[@]}"; then
    mark REPRODUCTION_GATE OK
  else
    mark REPRODUCTION_GATE FAILED
    echo "REPRODUCTION GATE FAILED -- per design §3.6/SOTA-REPRODUCTION-PLAN §3," \
         "no gate result is reportable until this is fixed. Continuing the" \
         "pilot loop anyway so its own content gates produce a diagnosable" \
         "PARTIAL marker, per this chain's non-fatal-stage convention." >&2
  fi

  python3 - "$RESULTS_DIR/phase0_reproduction.json" "$K3_MIN_AUROC" <<'PYEOF'
import json, sys
path, floor = sys.argv[1], float(sys.argv[2])
with open(path, encoding="utf-8") as f:
    result = json.load(f)
graded = result.get("reproduction", {})
if len(graded) < 1:
    # Vacuous-pass guard: an empty reproduction dict (e.g. Stage 2 produced
    # zero usable score files) must not fall through the empty for-loop
    # below and print a silent K3_OK.
    print(f"K3_TRIPPED: zero backbones graded (reproduction dict empty)", file=sys.stderr)
    sys.exit(1)
tripped = []
for backbone, rec in graded.items():
    if rec["mean_auroc"] < floor:
        tripped.append((backbone, rec["mean_auroc"]))
if tripped:
    print(f"K3_TRIPPED: {tripped} (floor={floor})", file=sys.stderr)
    sys.exit(1)
print(f"K3_OK: all backbones >= {floor}")
PYEOF
  if [ "$?" -eq 0 ]; then mark K3_BACKBONE_FLOOR OK; else mark K3_BACKBONE_FLOOR FAILED; fi
}

# ---------------------------------------------------------------------------
# Stage 4: per (backbone, category) pilot cells -- calibrate/route/certify/
# audit via run_pilot_cell.py, R=PILOT_N_REPEATS repeats.
# ---------------------------------------------------------------------------

stage_4_pilot_cells() {
  step "Stage 4: pilot cells (calibrate/route/certify/audit), R=${PILOT_N_REPEATS}"
  local backbone category
  for backbone in patchcore dinomaly; do
    if [ "$backbone" = "dinomaly" ] && [ "$DINOMALY_AVAILABLE" -eq 0 ]; then
      echo "note: dinomaly unavailable this run -- skipping its pilot cells (disclosed, PatchCore-only pilot)"
      for category in $PILOT_CATEGORIES; do
        mark "CELL_${backbone}_${category}" SKIPPED_DISCLOSED
      done
      continue
    fi
    local scores="$RESULTS_DIR/scores_${backbone}_seed0.jsonl"
    [ -s "$scores" ] || { for category in $PILOT_CATEGORIES; do mark "CELL_${backbone}_${category}" FAILED; done; continue; }

    for category in $PILOT_CATEGORIES; do
      local out="$RESULTS_DIR/cell_${backbone}_${category}.json"
      if [ -s "$out" ]; then
        skip "$out"
      else
        python3 "$SCRIPT_DIR/run_pilot_cell.py" \
          --scores "$scores" --category "$category" \
          --alpha-miss "$ALPHA_MISS" --alpha-fr "$ALPHA_FR" \
          --n-repeats "$PILOT_N_REPEATS" --backbone "$backbone" \
          --n-perm "$AUDIT_N_PERM" -o "$out" \
          || echo "warning: run_pilot_cell.py $backbone/$category exited non-zero -- content gate below will catch it"
      fi
      if assert_pass_tier1 "$out" "$category"; then
        mark "CELL_${backbone}_${category}" OK
      else
        mark "CELL_${backbone}_${category}" FAILED
      fi
    done
  done
}

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

GRID_ABORTED=0
if ! stage_1_staging; then GRID_ABORTED=1; fi
if [ "$GRID_ABORTED" -eq 0 ] && ! assert_gpu_present; then
  mark NO_GPU_GUARD FAILED
  GRID_ABORTED=1
fi
if [ "$GRID_ABORTED" -eq 0 ]; then stage_2_score; fi
if [ "$GRID_ABORTED" -eq 0 ]; then stage_3_reproduction_gate; fi
if [ "$GRID_ABORTED" -eq 0 ]; then stage_4_pilot_cells; else
  echo "PILOT ABORTED before Stage 2 -- see FAILED markers above ($MARKERS_DIR)" >&2
fi

if [ "${#FAILED_MARKERS[@]}" -eq 0 ]; then
  marker_name="INSPECT_GATE_PILOT_ALL_DONE"
else
  marker_name="INSPECT_GATE_PILOT_PARTIAL"
  echo "PARTIAL -- failed markers: ${FAILED_MARKERS[*]}" >&2
fi

chain_epilogue "$RESULTS_DIR $INSPECT_GATE_LOG $GPU_UTIL_LOG" "$marker_name"
