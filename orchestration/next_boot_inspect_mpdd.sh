#!/bin/bash
# next_boot_inspect_mpdd.sh -- inspect-gate MPDD third-benchmark chain
# (COMPUTE-PLAN-2026-07-13.md): metal-parts realism, both backbones, 5 seeds,
# replaying the frozen gate/V1/audit pipeline unchanged. Mirrors
# visa_brancha.sh conventions: content-gated markers everywhere, DISTINCT
# marker names, no pre-epilogue marker echo (2026-07-10 watcher-race rule),
# GPU-presence gate before any compute.
#
# MPDD is native MVTec-AD layout, so staging is EXTRACT + VERIFY (no VisA-
# style JPEG->PNG symlink prep): unzip the archive, then mpdd_prep.py freezes
# the split manifest and refuses on any count/structure mismatch.
#
# Data source (credential-free by default): the box pulls MPDD from, in order,
#   1. $MPDD_LOCAL_ZIP  (a zip already staged on the box -- fastest, preferred
#      if the user pushed it via boxkit / their HF bucket);
#   2. $MPDD_ZIP_URL    (default: the PUBLIC HF mirror meksamiao/mpdd, which
#      needs no token). HF can be slow/blocked from CN AutoDL boxes, so a
#      local push is preferred when available.
#
# Usage on the box:  bash next_boot_inspect_mpdd.sh
# Validate locally:  bash next_boot_inspect_mpdd.sh --dry-run   (no GPU, no
#      download, no compute -- checks every referenced script + prints the plan)

set -uo pipefail

DRY_RUN=0
[ "${1:-}" = "--dry-run" ] && DRY_RUN=1

# --- paths (env-overridable; default to on-box layout, but --dry-run derives
#     the repo root from this script's own location so it validates locally) --
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
IG_ROOT="${IG_ROOT:-$(cd "$SCRIPT_DIR/.." && pwd)}"            # inspect-gate dir
ORCH="$IG_ROOT/orchestration"
MPDD_SCRIPTS="$IG_ROOT/mpdd_results_2026-07-13/scripts"
RELIABILITY_COMMONS="${RELIABILITY_COMMONS:-/root/reliability-commons}"
DINOMALY_HOME="${DINOMALY_HOME:-/root/Dinomaly}"

# --- tunables (named defaults; no inline magic denominators) ----------------
RESULTS_DIR="${RESULTS_DIR:-/root/autodl-tmp/mpdd_brancha}"
MARKERS_DIR="$RESULTS_DIR/markers"
MPDD_ROOT="${MPDD_ROOT:-/root/autodl-tmp/MPDD}"               # native MVTec layout root
MPDD_LOCAL_ZIP="${MPDD_LOCAL_ZIP:-}"                          # preferred if set
MPDD_ZIP_URL="${MPDD_ZIP_URL:-https://huggingface.co/datasets/meksamiao/mpdd/resolve/main/MPDD.zip}"
MPDD_MANIFEST="${MPDD_MANIFEST:-$RESULTS_DIR/mpdd_split_manifest.json}"
CATS="bracket_black bracket_brown bracket_white connector metal_plate tubes"
SEEDS="${MPDD_SEEDS:-0 1 2 3 4}"
GPU_WAIT_S="${MPDD_GPU_WAIT_S:-172800}"
DINOMALY_ITERS_N="${MPDD_DINOMALY_ITERS:-10000}"
EXPECT_TRAIN_GOOD="${MPDD_EXPECT_TRAIN_GOOD:-888}"
EXPECT_TEST="${MPDD_EXPECT_TEST:-458}"
SMOKE_SEED="${MPDD_SMOKE_SEED:-0}"                            # one-cell smoke gate
# Train-holdout arm (FLOOR-PREDICTION.md "constructive counter-story": G2
# calibrates on a 20% train-good holdout -> floor 5/6 instead of 0/6).
# score_patchcore.py --holdout-frac is flag-gated and prereg-NEUTRAL (0.0 =
# byte-identical primary behavior); the PRIMARY stage-2 arm below never sets
# it, so the primary protocol stays untouched. Costs roughly one extra
# PatchCore pass (~+4-6 GPU-h).
HOLDOUT_ARM="${MPDD_HOLDOUT_ARM:-1}"                          # 0 disables stage 2b
HOLDOUT_FRAC="${MPDD_HOLDOUT_FRAC:-0.2}"
HOLDOUT_SEED="${MPDD_HOLDOUT_SEED:-0}"

step() { echo "== $1 =="; }

# ---------------------------------------------------------------------------
# --dry-run: validate every referenced script + print the plan, then exit 0.
# Runs fully on the workstation (no /root, no GPU, no network).
# ---------------------------------------------------------------------------
if [ "$DRY_RUN" -eq 1 ]; then
  echo "=== next_boot_inspect_mpdd.sh --dry-run ==="
  echo "IG_ROOT=$IG_ROOT"
  rc=0
  need=(
    "$ORCH/dinomaly_mpdd_uni.py"
    "$ORCH/dinomaly_patch.py"
    "$ORCH/mpdd_prep.py"
    "$ORCH/mvtec_layout.py"
    "$ORCH/score_patchcore.py"
    "$ORCH/score_dinomaly.py"
    "$MPDD_SCRIPTS/mpdd_adapter.py"
    "$MPDD_SCRIPTS/run_mpdd_analysis.py"
    "$MPDD_SCRIPTS/mpdd_floor_table.py"
  )
  for f in "${need[@]}"; do
    if [ -s "$f" ]; then echo "  OK   $f"; else echo "  MISS $f"; rc=1; fi
  done
  # dinomaly_mpdd_uni.py must carry the P1-P5 patch anchors dinomaly_patch.py needs
  echo "--- dinomaly_mpdd_uni.py patch-anchor check ---"
  py="$ORCH/dinomaly_mpdd_uni.py"
  for anchor in \
    "setup_seed(1)" \
    "total_iters = 10000" \
    "device = 'cuda:1' if torch.cuda.is_available() else 'cpu'" \
    "if __name__ == '__main__':" \
    "bracket_black"; do
    if grep -qF "$anchor" "$py" 2>/dev/null; then echo "  OK   anchor: $anchor"; else echo "  MISS anchor: $anchor"; rc=1; fi
  done
  echo "--- plan ---"
  echo "  categories : $CATS"
  echo "  seeds      : $SEEDS"
  echo "  expect     : train-good=$EXPECT_TRAIN_GOOD, test=$EXPECT_TEST"
  echo "  data src   : local=[${MPDD_LOCAL_ZIP:-<unset>}] url=[$MPDD_ZIP_URL]"
  echo "  stages     : 0 gpu-gate -> 1 stage+verify(mpdd_prep) -> 2 patchcore 6x5 (PRIMARY)"
  echo "               -> 2b patchcore train-holdout arm (frac=$HOLDOUT_FRAC seed=$HOLDOUT_SEED,"
  echo "                   phase-0 one-cell smoke w/ provenance-sidecar gate BEFORE 6x5;"
  echo "                   enabled=$HOLDOUT_ARM; separate patchcore_holdout/ output)"
  echo "               -> 3 dinomaly uni x5 (patch dinomaly_mpdd_uni) -> smoke gate"
  echo "               -> 4 latency env -> epilogue (MPDD_BRANCHA_ALL_DONE)"
  if [ "$rc" -eq 0 ]; then echo "DRY_RUN_OK"; else echo "DRY_RUN_FAILED (missing files/anchors above)"; fi
  exit "$rc"
fi

# ---------------------------------------------------------------------------
# Real box run below.
# ---------------------------------------------------------------------------
export CHAIN_LOG="${CHAIN_LOG:-/root/mpdd_brancha.log}"
source "$RELIABILITY_COMMONS/tools/boxkit/chain_lib.sh"
conda activate base 2>/dev/null || true
chain_prologue

mkdir -p "$RESULTS_DIR" "$MARKERS_DIR"

FAILED_MARKERS=()
mark() { local n="$1" s="$2"; printf '%s\n' "$s" > "$MARKERS_DIR/${n}.marker"; echo "MARKER ${n}=${s}"
  { [ "$s" = "FAILED" ] || [ "$s" = "REFUSED" ]; } && FAILED_MARKERS+=("$n"); return 0; }

# --- Stage 0: GPU-presence gate --------------------------------------------
step "0: GPU wait (up to ${GPU_WAIT_S}s)"
waited=0
until nvidia-smi --query-gpu=name --format=csv,noheader 2>/dev/null | grep -q .; do
  sleep 60; waited=$((waited+60)); [ "$waited" -ge "$GPU_WAIT_S" ] && break
done
if nvidia-smi --query-gpu=name --format=csv,noheader 2>/dev/null | grep -q .; then
  mark MPDD_GPU_PRESENT OK
else
  mark MPDD_GPU_PRESENT REFUSED
  echo "no GPU within ${GPU_WAIT_S}s -- aborting (disclosed)"
  chain_epilogue "$RESULTS_DIR" "MPDD_BRANCHA_PARTIAL_DONE" "mpdd_brancha"; exit 1
fi

# --- Stage 1: stage (extract native MVTec layout) + verify + freeze manifest -
step "1: MPDD staging (extract + mpdd_prep verify)"
if [ ! -d "$MPDD_ROOT/bracket_black/train/good" ]; then
  zip=""
  if [ -n "$MPDD_LOCAL_ZIP" ] && [ -s "$MPDD_LOCAL_ZIP" ]; then
    zip="$MPDD_LOCAL_ZIP"; echo "using local zip $zip"
  else
    zip="/root/autodl-tmp/MPDD.zip"
    echo "downloading MPDD from $MPDD_ZIP_URL"
    curl -sSL -C - -o "$zip" "$MPDD_ZIP_URL" || echo "warning: MPDD download non-zero"
  fi
  mkdir -p "$MPDD_ROOT"
  # zip may wrap the 6 category dirs in a top-level MPDD/ -- extract then
  # normalise so $MPDD_ROOT holds the 6 category dirs directly.
  tmpx="/root/autodl-tmp/_mpdd_extract"; rm -rf "$tmpx"; mkdir -p "$tmpx"
  unzip -q -o "$zip" -d "$tmpx" || echo "warning: unzip non-zero"
  if [ -d "$tmpx/MPDD/bracket_black" ]; then src="$tmpx/MPDD"; elif [ -d "$tmpx/bracket_black" ]; then src="$tmpx"; else src="$(dirname "$(find "$tmpx" -type d -name bracket_black | head -1)")"; fi
  [ -n "${src:-}" ] && cp -rn "$src"/* "$MPDD_ROOT"/ 2>/dev/null
fi
sha=$(sha256sum "${MPDD_LOCAL_ZIP:-/root/autodl-tmp/MPDD.zip}" 2>/dev/null | awk '{print $1}')
if python3 "$ORCH/mpdd_prep.py" "$MPDD_ROOT" "$MPDD_MANIFEST" \
     --expect-train-good "$EXPECT_TRAIN_GOOD" --expect-test "$EXPECT_TEST" \
     --archive-sha256 "${sha:-unknown}" 2>&1 | tee "$RESULTS_DIR/mpdd_prep.log" | grep -q "MPDD_PREP_OK"; then
  mark MPDD_STAGED OK
else
  mark MPDD_STAGED FAILED
fi

# --- Stage 2: PatchCore scoring, 6 cats x 5 seeds --------------------------
step "2: PatchCore MPDD (6 cats x seeds [$SEEDS])"
if [ "$(cat "$MARKERS_DIR/MPDD_STAGED.marker" 2>/dev/null)" = "OK" ]; then
  conda activate "${PATCHCORE_ENV:-anomalib}" || conda activate base
  pc_fail=0
  for s in $SEEDS; do
    out="$RESULTS_DIR/patchcore/seed_${s}"; mkdir -p "$out"
    for c in $CATS; do
      f="$out/scores_${c}.jsonl"
      [ -s "$f" ] && { echo "skip $f"; continue; }
      python3 "$ORCH/score_patchcore.py" --data-root "$MPDD_ROOT" --category "$c" \
        --seed "$s" --device cuda --out "$f" \
        || echo "warning: patchcore $c seed $s non-zero -- gate below authoritative"
      [ -s "$f" ] || pc_fail=1
      rm -rf /root/autodl-tmp/anomalib_results/* 2>/dev/null   # anomalib fills the data disk otherwise
    done
  done
  n_cells=$(find "$RESULTS_DIR/patchcore" -name "scores_*.jsonl" -size +0 | wc -l)
  n_expect=$(( $(echo $CATS | wc -w) * $(echo $SEEDS | wc -w) ))
  echo "patchcore cells: $n_cells / $n_expect"
  if [ "$n_cells" -eq "$n_expect" ] && [ "$pc_fail" -eq 0 ]; then mark MPDD_PATCHCORE OK; else mark MPDD_PATCHCORE FAILED; fi
else
  mark MPDD_PATCHCORE SKIPPED_DISCLOSED
fi

# --- Stage 2b: PatchCore train-holdout arm (G2 rescue, FLOOR-PREDICTION.md) --
# Phase-0 discipline per score_patchcore.py's module docstring: the holdout
# partition + fit-on-subset + holdout predict pass are anomalib-internals-
# dependent and MUST be smoke-verified on the real box before the full arm.
step "2b: PatchCore train-holdout arm (frac=$HOLDOUT_FRAC, enabled=$HOLDOUT_ARM)"
if [ "$HOLDOUT_ARM" = "1" ] && [ "$(cat "$MARKERS_DIR/MPDD_STAGED.marker" 2>/dev/null)" = "OK" ]; then
  conda activate "${PATCHCORE_ENV:-anomalib}" || conda activate base
  smk="$RESULTS_DIR/patchcore_holdout_smoke"; mkdir -p "$smk"
  sf="$smk/scores_bracket_black.jsonl"
  python3 "$ORCH/score_patchcore.py" --data-root "$MPDD_ROOT" --category bracket_black \
    --seed "$SMOKE_SEED" --device cuda --holdout-frac "$HOLDOUT_FRAC" \
    --holdout-seed "$HOLDOUT_SEED" --out "$sf" \
    || echo "warning: holdout smoke non-zero -- gate below authoritative"
  rm -rf /root/autodl-tmp/anomalib_results/* 2>/dev/null
  # Content gate: scores present AND the provenance sidecar carries a
  # non-empty holdout_ids list (proves the partition + holdout predict ran).
  if [ -s "$sf" ] && python3 - "$sf" << 'PY'
import json, sys
from pathlib import Path
p = Path(sys.argv[1]).with_suffix(".holdout_provenance.json")
d = json.load(open(p))
# score_patchcore stamps holdout_ids_by_category (dict cat -> [ids]);
# 2026-07-14 fix: the first gate read a nonexistent flat "holdout_ids" key
# and false-negatived a perfectly good smoke (137 = 79 test + 58 holdout).
by_cat = d.get("holdout_ids_by_category") or {}
n = sum(len(v) for v in by_cat.values())
assert n > 0, f"empty holdout_ids_by_category in {p}"
print(f"holdout smoke: {n} held-out train-good ids stamped "
      f"across {len(by_cat)} categories")
PY
  then
    mark MPDD_HOLDOUT_SMOKE OK
    ho_fail=0
    for s in $SEEDS; do
      out="$RESULTS_DIR/patchcore_holdout/seed_${s}"; mkdir -p "$out"
      for c in $CATS; do
        f="$out/scores_${c}.jsonl"
        [ -s "$f" ] && { echo "skip $f"; continue; }
        python3 "$ORCH/score_patchcore.py" --data-root "$MPDD_ROOT" --category "$c" \
          --seed "$s" --device cuda --holdout-frac "$HOLDOUT_FRAC" \
          --holdout-seed "$HOLDOUT_SEED" --out "$f" \
          || echo "warning: patchcore-holdout $c seed $s non-zero -- gate below authoritative"
        { [ -s "$f" ] && [ -s "${f%.jsonl}.holdout_provenance.json" ]; } || ho_fail=1
        rm -rf /root/autodl-tmp/anomalib_results/* 2>/dev/null
      done
    done
    n_ho=$(find "$RESULTS_DIR/patchcore_holdout" -name "scores_*.jsonl" -size +0 | wc -l)
    n_ho_expect=$(( $(echo $CATS | wc -w) * $(echo $SEEDS | wc -w) ))
    echo "patchcore-holdout cells: $n_ho / $n_ho_expect"
    if [ "$n_ho" -eq "$n_ho_expect" ] && [ "$ho_fail" -eq 0 ]; then mark MPDD_PATCHCORE_HOLDOUT OK
    else mark MPDD_PATCHCORE_HOLDOUT FAILED; fi
  else
    mark MPDD_HOLDOUT_SMOKE FAILED
    mark MPDD_PATCHCORE_HOLDOUT SKIPPED_DISCLOSED
    echo "holdout smoke failed -- primary arm unaffected; holdout arm skipped (disclosed)"
  fi
elif [ "$HOLDOUT_ARM" != "1" ]; then
  mark MPDD_PATCHCORE_HOLDOUT DISABLED_DISCLOSED
else
  mark MPDD_PATCHCORE_HOLDOUT SKIPPED_DISCLOSED
fi

# --- Stage 3: Dinomaly MPDD unified, 5 seeds -------------------------------
step "3: Dinomaly MPDD uni (patch + seeds [$SEEDS] x ${DINOMALY_ITERS_N} iters)"
if [ "$(cat "$MARKERS_DIR/MPDD_STAGED.marker" 2>/dev/null)" = "OK" ]; then
  conda activate "${DINOMALY_ENV:-dinomaly}" || conda activate base
  cp -f "$ORCH/dinomaly_mpdd_uni.py" "$DINOMALY_HOME/dinomaly_mpdd_uni.py"
  if python3 "$ORCH/dinomaly_patch.py" "$DINOMALY_HOME/dinomaly_mpdd_uni.py"; then
    mark MPDD_DINOMALY_PATCH OK
    dm_fail=0
    for s in $SEEDS; do
      run="$RESULTS_DIR/dinomaly/seed_${s}"; mkdir -p "$run"
      if [ -s "$run/run/model.pth" ]; then echo "skip seed $s"; else
        ( cd "$DINOMALY_HOME" && DINOMALY_SEED=$s DINOMALY_ITERS=$DINOMALY_ITERS_N DINOMALY_DEVICE=cuda:0 \
          python3 dinomaly_mpdd_uni.py --data_path "$MPDD_ROOT" --save_dir "$run" --save_name run \
          > "$RESULTS_DIR/dinomaly_seed${s}.log" 2>&1 ) || echo "warning: dinomaly seed $s non-zero"
      fi
      n_dumps=$(find "$run/run" -name "scores_*.json" -size +0 2>/dev/null | wc -l)
      echo "seed $s dumps: $n_dumps / 6"
      if [ "$n_dumps" -eq 6 ] && [ -s "$run/run/model.pth" ]; then mark "MPDD_DINOMALY_SEED_${s}" OK
      else mark "MPDD_DINOMALY_SEED_${s}" FAILED; dm_fail=1; fi

      # One-cell smoke gate: after the FIRST seed, sanity-check its own log
      # I-AUROC mean approaches the 97.2 published target before spending the
      # remaining 4 seeds (Phase-0 discipline; disclosed, non-fatal).
      if [ "$s" = "$SMOKE_SEED" ]; then
        mean=$(grep -oE "Mean: I-Auroc:[0-9.]+" "$run/run/log.txt" 2>/dev/null | tail -1 | grep -oE "[0-9.]+$")
        echo "smoke: seed $s mean I-AUROC = ${mean:-NA} (published uni target 0.972)"
        awk -v m="${mean:-0}" 'BEGIN{exit !(m+0 >= 0.90)}' \
          && mark MPDD_SMOKE_GATE OK \
          || { mark MPDD_SMOKE_GATE FAILED; echo "smoke gate: mean ${mean:-NA} < 0.90 floor -- uni port may need the sep fallback (disclosed)"; }
      fi
    done
    [ "$dm_fail" -eq 0 ] && mark MPDD_DINOMALY OK || mark MPDD_DINOMALY FAILED
  else
    mark MPDD_DINOMALY_PATCH FAILED; mark MPDD_DINOMALY SKIPPED_DISCLOSED
  fi
else
  mark MPDD_DINOMALY SKIPPED_DISCLOSED
fi

# --- Stage 4: latency env record -------------------------------------------
step "4: latency env record"
python3 - "$RESULTS_DIR" << 'PY' || echo "latency stage non-zero (disclosed)"
import json, sys, time, subprocess
gpu = subprocess.run(["nvidia-smi","--query-gpu=name,memory.total","--format=csv,noheader"],
                     capture_output=True, text=True).stdout.strip()
json.dump({"gpu": gpu, "recorded_at": time.strftime("%Y-%m-%dT%H:%M:%S")},
          open(sys.argv[1] + "/latency_env.json", "w"))
print("latency env recorded")
PY

# --- pack the dumps for pull -----------------------------------------------
tar -C "$RESULTS_DIR" -czf "$RESULTS_DIR/mpdd_brancha_pull.tgz" \
  patchcore patchcore_holdout patchcore_holdout_smoke dinomaly \
  mpdd_split_manifest.json markers 2>/dev/null \
  && echo "packed mpdd_brancha_pull.tgz" || echo "pack non-zero (disclosed)"

if [ "${#FAILED_MARKERS[@]}" -eq 0 ]; then
  marker_name="MPDD_BRANCHA_ALL_DONE"
else
  marker_name="MPDD_BRANCHA_PARTIAL_DONE"
  echo "MPDD_BRANCHA_PARTIAL -- failed: ${FAILED_MARKERS[*]}"
fi
chain_epilogue "$RESULTS_DIR" "$marker_name" "mpdd_brancha"
