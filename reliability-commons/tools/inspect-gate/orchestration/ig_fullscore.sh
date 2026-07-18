#!/bin/bash
# inspect-gate FULL score-substrate run: 15 categories x PC_SEEDS PatchCore
# fits+scorings (prereg-NEUTRAL score caching; certification analysis stays
# behind the freeze, per run_main_grid.sh's REQUIRES_PREREG_FREEZE guard).
# Ends: tar -> marker -> ack-wait -> self-shutdown (chain_lib.sh's
# chain_epilogue).
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RELIABILITY_COMMONS="${RELIABILITY_COMMONS:-/root/reliability-commons}"
source "${RELIABILITY_COMMONS}/tools/boxkit/chain_lib.sh"
source /root/miniconda3/etc/profile.d/conda.sh && conda activate base
source /etc/network_turbo >/dev/null 2>&1 || true
export HF_HOME=/root/autodl-tmp/hf-cache HF_ENDPOINT=https://hf-mirror.com HF_HUB_DISABLE_XET=1
L="${IG_LOG:-/root/ig_fullscore.log}"
export CHAIN_LOG="$L"
chain_prologue
exec > >(tee -a "$L") 2>&1

# /root/autodl-tmp/mvtec_ad is what the staged box actually uses (verified
# on-box 2026-07-10) -- THE named default, mirrored in phase0.py's
# DEFAULT_DATA_ROOT and next_boot_inspect_gate.sh's DATA_ROOT.
DATA_ROOT="${MVTEC_DATA_ROOT:-/root/autodl-tmp/mvtec_ad}"
OUT_DIR="${IG_SCORES_DIR:-/root/autodl-tmp/ig_scores_full}"
SEEDS="${PC_SEEDS:-0 1 2 3 4}"
# Train-holdout arm (prereg-NEUTRAL score caching; score_patchcore.py's
# --holdout-frac, default 0.0 = byte-identical legacy behavior). When > 0,
# ALWAYS pair with a dedicated IG_SCORES_DIR + IG_TAR_NAME so the frozen
# test-only substrate is never mixed with holdout-bearing score files.
HOLDOUT_FRAC="${IG_HOLDOUT_FRAC:-0.0}"
TAR_NAME="${IG_TAR_NAME:-ig_fullscore}"

mkdir -p "$OUT_DIR"

# No-card guard (M2): a no-card box has a 2GB quota -- attempting a
# score_patchcore.py model load on one OOMs. Probe up front, before any
# model load is attempted, and exit via the normal chain_epilogue path
# (tar + a distinct marker + ack-wait + shutdown) rather than a hard
# `exit` that would strand the box without packaging/acking whatever
# results already exist in $OUT_DIR.
GPU_LIST="$(nvidia-smi -L 2>/dev/null)" || GPU_LIST=""
if [ -z "$GPU_LIST" ]; then
  echo "IG_NO_GPU_ABORT: nvidia-smi -L failed or reported no devices -- " \
       "refusing to attempt any model load (no-card boxes have a 2GB " \
       "quota; a model load OOMs)."
  chain_epilogue "$OUT_DIR $L" "IG_FULLSCORE_NO_GPU_ABORT" "ig_fullscore"
  exit 1
fi

CATS=$(find "$DATA_ROOT" -maxdepth 1 -mindepth 1 -type d -printf "%f\n" | sort)

FAIL=0
for cat in $CATS; do
  for seed in $SEEDS; do
    out="$OUT_DIR/scores_patchcore_${cat}_seed${seed}.jsonl"
    if [ -s "$out" ]; then
      echo "skip existing (pre-count-check) $out"
    else
      python3 "$SCRIPT_DIR/score_patchcore.py" --data-root "$DATA_ROOT" \
        --category "$cat" --seed "$seed" --out "$out" \
        --holdout-frac "$HOLDOUT_FRAC" \
        || echo "warning: scorer non-zero for $cat seed $seed"
    fi

    if [ -s "$out" ]; then
      n_lines=$(wc -l < "$out")
      n_test_images=$(find "$DATA_ROOT/$cat/test" -type f | wc -l)
      # M7 expected-row count: test images, plus the realized holdout size
      # when the holdout arm is on. The holdout arithmetic MUST match
      # partition_train_holdout (min(n, max(1, round(frac*n))), python
      # round semantics) -- so compute it with python, not shell arithmetic.
      expected="$n_test_images"
      if [ "$HOLDOUT_FRAC" != "0.0" ] && [ "$HOLDOUT_FRAC" != "0" ]; then
        n_train_good=$(find "$DATA_ROOT/$cat/train/good" -type f | wc -l)
        n_holdout=$(python3 -c "n=$n_train_good; f=$HOLDOUT_FRAC; print(min(n, max(1, round(f*n))) if n else 0)")
        expected=$((n_test_images + n_holdout))
      fi
      if [ "$n_lines" -ne "$expected" ]; then
        # Content gate (M7), same DOFA-lesson discipline as
        # next_boot_inspect_gate.sh's assert_scores_content: a bare exit
        # code / non-empty file is not enough -- the row count must match
        # the on-disk test-image count for this category. Delete the bad
        # file so a resumed run re-scores it instead of trusting a
        # truncated/duplicated cache forever.
        echo "SCORE_${cat}_s${seed}_COUNT_BAD n_lines=$n_lines expected=$expected (n_test_images=$n_test_images holdout_frac=$HOLDOUT_FRAC)"
        rm -f "$out"
        FAIL=1
      else
        echo "SCORE_${cat}_s${seed}_OK n=$n_lines"
      fi
    else
      echo "SCORE_${cat}_s${seed}_FAILED"; FAIL=1
    fi
  done
done
[ "$FAIL" -eq 0 ] && echo "IG_FULLSCORE_ALL_CELLS_OK" || echo "IG_FULLSCORE_PARTIAL_CELLS"

if [ "$FAIL" -eq 0 ]; then
  marker_name="IG_FULLSCORE_ALL_DONE"
else
  # Distinct from the clean-path marker (M3) -- a watcher polling for
  # IG_FULLSCORE_ALL_DONE must not mistake a partial run for a complete one.
  marker_name="IG_FULLSCORE_PARTIAL_DONE"
fi
chain_epilogue "$OUT_DIR $L" "$marker_name" "$TAR_NAME"
