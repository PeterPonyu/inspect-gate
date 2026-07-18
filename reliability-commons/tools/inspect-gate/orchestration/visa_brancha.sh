#!/bin/bash
# visa_brancha.sh -- inspect-gate VisA second-benchmark chain (gap-audit I1
# + I3 latency; answers the red-team ceiling-substrate MAJOR). Pre-launchable
# on a GPU-LESS box: Stage 0 polls for a GPU (the user flips the box mode)
# before any compute stage runs. Mirrors dinomaly_branchA.sh conventions:
# content gates everywhere, DISTINCT markers, no pre-epilogue marker echo
# (2026-07-10 watcher-race rule).
set -uo pipefail
source /root/miniconda3/etc/profile.d/conda.sh && conda activate base

export CHAIN_LOG="${CHAIN_LOG:-/root/visa_brancha.log}"
source /root/reliability-commons/tools/boxkit/chain_lib.sh
chain_prologue

RESULTS_DIR="${RESULTS_DIR:-/root/autodl-tmp/visa_brancha}"
MARKERS_DIR="$RESULTS_DIR/markers"
mkdir -p "$RESULTS_DIR" "$MARKERS_DIR"
RAW="${VISA_RAW:-/root/autodl-tmp/visa_raw}"
TAR="${VISA_TAR:-/root/autodl-tmp/VisA_20220922.tar}"
CSV="${VISA_SPLIT_CSV:-/root/autodl-tmp/1cls.csv}"
PYROOT_A="${VISA_PYROOT_A:-/root/autodl-tmp/VisA_pytorch/1cls}"        # anomalib naming (<stem>_mask.png)
PYROOT_B="${VISA_PYROOT_B:-/root/autodl-tmp/VisA_pytorch_dino/1cls}"  # Dinomaly naming (<stem>/000.png)
CATS="candle capsules cashew chewinggum fryum macaroni1 macaroni2 pcb1 pcb2 pcb3 pcb4 pipe_fryum"
SEEDS="${VISA_SEEDS:-0 1 2 3 4}"
GPU_WAIT_S="${VISA_GPU_WAIT_S:-172800}"   # user flips the box to GPU mode
DINOMALY_ITERS_N="${VISA_DINOMALY_ITERS:-10000}"

FAILED_MARKERS=()
step() { echo "== $1 =="; }
mark() { local n="$1" s="$2"; printf '%s\n' "$s" > "$MARKERS_DIR/${n}.marker"; echo "MARKER ${n}=${s}"
  { [ "$s" = "FAILED" ] || [ "$s" = "REFUSED" ]; } && FAILED_MARKERS+=("$n"); return 0; }

# --- Stage 0: GPU-presence gate (box may still be in no-GPU mode) ----------
step "0: GPU wait (up to ${GPU_WAIT_S}s)"
waited=0
until nvidia-smi --query-gpu=name --format=csv,noheader 2>/dev/null | grep -q .; do
  sleep 60; waited=$((waited+60))
  if [ "$waited" -ge "$GPU_WAIT_S" ]; then break; fi
done
if nvidia-smi --query-gpu=name --format=csv,noheader 2>/dev/null | grep -q .; then
  mark VISA_GPU_PRESENT OK
else
  mark VISA_GPU_PRESENT REFUSED
  echo "no GPU appeared within ${GPU_WAIT_S}s -- aborting (disclosed)"
  chain_epilogue "$RESULTS_DIR" "VISA_BRANCHA_PARTIAL_DONE" "visa_brancha"
  exit 1
fi

# --- Stage 1: staging (extract tar + official 1cls split -> MVTec layout) --
step "1: VisA staging"
if [ ! -d "$RAW/candle" ]; then
  mkdir -p "$RAW" && tar xf "$TAR" -C "$RAW" || true
fi
n_jpg=$(find "$RAW" -name "*.JPG" 2>/dev/null | wc -l)
echo "raw JPGs: $n_jpg (expect 10821)"
if [ "$n_jpg" -eq 10821 ] && [ -s "$CSV" ]; then
  if python3 /root/reliability-commons/tools/inspect-gate/orchestration/visa_prep.py "$RAW" "$CSV" "$PYROOT_A" "$PYROOT_B" 2>&1 | tee "$RESULTS_DIR/visa_prep.log" | grep -q "VISA_PREP_OK"; then
    mark VISA_STAGED OK
  else
    mark VISA_STAGED FAILED
  fi
else
  mark VISA_STAGED FAILED
fi

# --- Stage 2: PatchCore scoring, 12 cats x 5 seeds (anomalib env) ----------
step "2: PatchCore VisA (12 cats x seeds [$SEEDS])"
if [ "$(cat "$MARKERS_DIR/VISA_STAGED.marker")" = "OK" ]; then
  conda activate "${PATCHCORE_ENV:-anomalib}" || conda activate base
  pc_fail=0
  for s in $SEEDS; do
    out="$RESULTS_DIR/patchcore/seed_${s}"
    mkdir -p "$out"
    for c in $CATS; do
      f="$out/scores_${c}.jsonl"
      [ -s "$f" ] && { echo "skip $f"; continue; }
      python3 /root/reliability-commons/tools/inspect-gate/orchestration/score_patchcore.py \
        --data-root "$PYROOT_A" --category "$c" --seed "$s" --device cuda --out "$f" \
        || echo "warning: patchcore $c seed $s non-zero -- gate below authoritative"
      [ -s "$f" ] || pc_fail=1
      # anomalib's ImageVisualizer writes per-test-image PNGs unconditionally
      # (~500MB/cell); they are never consumed by this pipeline and filled the
      # 50GB data disk at 100% on 2026-07-12 (2nd occurrence of the 07-10
      # incident). Purge after every cell.
      rm -rf /root/autodl-tmp/anomalib_results/* 2>/dev/null
    done
  done
  n_cells=$(find "$RESULTS_DIR/patchcore" -name "scores_*.jsonl" -size +0 | wc -l)
  n_expect=$(( $(echo $CATS | wc -w) * $(echo $SEEDS | wc -w) ))
  echo "patchcore cells: $n_cells / $n_expect"
  if [ "$n_cells" -eq "$n_expect" ] && [ "$pc_fail" -eq 0 ]; then mark VISA_PATCHCORE OK; else mark VISA_PATCHCORE FAILED; fi
else
  mark VISA_PATCHCORE SKIPPED_DISCLOSED
fi

# --- Stage 3: Dinomaly VisA unified, 5 seeds (dinomaly env; patched script) -
step "3: Dinomaly VisA (patch + seeds [$SEEDS] x ${DINOMALY_ITERS_N} iters)"
if [ "$(cat "$MARKERS_DIR/VISA_STAGED.marker")" = "OK" ]; then
  conda activate "${DINOMALY_ENV:-dinomaly}" || conda activate base
  if python3 /root/reliability-commons/tools/inspect-gate/orchestration/dinomaly_patch.py /root/Dinomaly/dinomaly_visa_uni.py; then
    mark VISA_DINOMALY_PATCH OK
    dm_fail=0
    for s in $SEEDS; do
      run="$RESULTS_DIR/dinomaly/seed_${s}"
      mkdir -p "$run"
      if [ -s "$run/run/model.pth" ]; then echo "skip seed $s"; else
        ( cd /root/Dinomaly && DINOMALY_SEED=$s DINOMALY_ITERS=$DINOMALY_ITERS_N DINOMALY_DEVICE=cuda:0 \
          python3 dinomaly_visa_uni.py --data_path "$PYROOT_B" --save_dir "$run" --save_name run \
          > "$RESULTS_DIR/dinomaly_seed${s}.log" 2>&1 ) || echo "warning: dinomaly seed $s non-zero"
      fi
      n_dumps=$(find "$run/run" -name "scores_*.json" -size +0 2>/dev/null | wc -l)
      echo "seed $s dumps: $n_dumps / 12"
      if [ "$n_dumps" -eq 12 ] && [ -s "$run/run/model.pth" ]; then
        mark "VISA_DINOMALY_SEED_${s}" OK
      else
        mark "VISA_DINOMALY_SEED_${s}" FAILED; dm_fail=1
      fi
    done
    [ "$dm_fail" -eq 0 ] && mark VISA_DINOMALY OK || mark VISA_DINOMALY FAILED
  else
    mark VISA_DINOMALY_PATCH FAILED
    mark VISA_DINOMALY SKIPPED_DISCLOSED
  fi
else
  mark VISA_DINOMALY SKIPPED_DISCLOSED
fi

# --- Stage 4: I3 latency timing (per-image inference, both backbones) ------
step "4: latency timing (I3)"
conda activate "${DINOMALY_ENV:-dinomaly}" || conda activate base
python3 - "$RESULTS_DIR" << 'PY' || echo "latency stage non-zero (disclosed)"
import json, sys, time
# Wall-clock per-cell throughput derived from the logs is recorded at
# analysis time; here record the GPU + env identity for the latency table.
import subprocess
gpu = subprocess.run(["nvidia-smi","--query-gpu=name,memory.total","--format=csv,noheader"],
                     capture_output=True, text=True).stdout.strip()
json.dump({"gpu": gpu, "recorded_at": time.strftime("%Y-%m-%dT%H:%M:%S")},
          open(sys.argv[1] + "/latency_env.json", "w"))
print("latency env recorded")
PY

if [ "${#FAILED_MARKERS[@]}" -eq 0 ]; then
  marker_name="VISA_BRANCHA_ALL_DONE"
  # No pre-epilogue echo of the marker (watcher-race rule).
else
  marker_name="VISA_BRANCHA_PARTIAL_DONE"
  echo "VISA_BRANCHA_PARTIAL -- failed: ${FAILED_MARKERS[*]}"
fi
chain_epilogue "$RESULTS_DIR" "$marker_name" "visa_brancha"
