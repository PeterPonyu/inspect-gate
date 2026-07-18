#!/bin/bash
# Dinomaly Branch-A chain (inspect-gate second backbone, design 01 addendum +
# survey §1 recommended path, user-directed 2026-07-10): self-train the
# official Apache-2.0 Dinomaly (multi-class-unified MVTec, one model per seed
# x DINOMALY_SEEDS) from DINOv2-reg weights, dump per-image scores, ready for
# score_dinomaly.py --mode dump-ingest. Waits for any running ig_fullscore
# pass to release the GPU. Markers content-gated; epilogue via chain_lib
# (NO_AUTOSHUTDOWN honored). Deploy by scp, launch by path -- NEVER via a
# heredoc-over-ssh whose cmdline would embed process patterns (2x phantom
# pgrep-match incidents 2026-07-10).
set -uo pipefail

RELIABILITY_COMMONS="${RELIABILITY_COMMONS:-/root/reliability-commons}"
# shellcheck disable=SC1091
source "${RELIABILITY_COMMONS}/tools/boxkit/chain_lib.sh"

DINOMALY_REPO="${DINOMALY_REPO:-/root/Dinomaly}"
DATA_ROOT="${MVTEC_DATA_ROOT:-/root/autodl-tmp/mvtec_ad}"
RESULTS_DIR="${RESULTS_DIR:-/root/autodl-tmp/dinomaly_branchA}"
WEIGHTS_URL="${DINOV2_WEIGHTS_URL:-https://dl.fbaipublicfiles.com/dinov2/dinov2_vitb14/dinov2_vitb14_reg4_pretrain.pth}"
WEIGHTS_DEST="$DINOMALY_REPO/backbones/weights/$(basename "$WEIGHTS_URL")"
WEIGHTS_MIN_BYTES="${DINOV2_WEIGHTS_MIN_BYTES:-300000000}"
DINOMALY_SEEDS="${DINOMALY_SEEDS:-0 1 2 3 4}"
DINOMALY_FULL_ITERS="${DINOMALY_FULL_ITERS:-10000}"
DINOMALY_SMOKE_ITERS="${DINOMALY_SMOKE_ITERS:-30}"
N_CATEGORIES="${IG_N_CATEGORIES:-15}"

export CHAIN_CONDA_ENV=dinomaly
export HF_HOME="${HF_HOME:-/root/autodl-tmp/hf-cache}"
export CHAIN_LOG="${CHAIN_LOG:-/root/dinomaly_branchA.log}"
MARKERS_DIR="$RESULTS_DIR/markers"
mkdir -p "$RESULTS_DIR" "$MARKERS_DIR"

FAILED_MARKERS=()
mark() {
  printf '%s\n' "$2" > "$MARKERS_DIR/$1.marker"
  echo "MARKER $1=$2"
  [ "$2" = "FAILED" ] && FAILED_MARKERS+=("$1")
}

# Wait for any holdout/fullscore pass to release the GPU. Bracket trick keeps
# the pattern from matching THIS script even if a cmdline ever quotes it.
while pgrep -f 'ig_fullscor[e].sh' >/dev/null 2>&1; do sleep 120; done
echo "[$(date)] GPU free -- starting Dinomaly Branch-A"

chain_prologue
source /etc/network_turbo >/dev/null 2>&1 || true

# Gate 1: env import probe (never pip exit codes).
if python -c "import torch, timm; assert torch.cuda.is_available()" 2>>"$RESULTS_DIR/env_probe.log"; then
  mark DINOMALY_ENV_PROBE OK
else
  mark DINOMALY_ENV_PROBE FAILED
fi

# Gate 2: DINOv2-reg weights (prefetch into the repo's own cache path; its
# vit_encoder.load() then hits the cache and never re-downloads).
mkdir -p "$(dirname "$WEIGHTS_DEST")"
if [ ! -s "$WEIGHTS_DEST" ] || [ "$(stat -c %s "$WEIGHTS_DEST")" -lt "$WEIGHTS_MIN_BYTES" ]; then
  for i in 1 2 3; do
    wget -q -c -O "$WEIGHTS_DEST" "$WEIGHTS_URL" && break
    sleep 5
  done
fi
if [ -s "$WEIGHTS_DEST" ] && [ "$(stat -c %s "$WEIGHTS_DEST")" -ge "$WEIGHTS_MIN_BYTES" ]; then
  mark DINOV2_WEIGHTS OK
else
  mark DINOV2_WEIGHTS FAILED
fi

# Gate 3: apply the anchored Branch-A patch (idempotent; diff recorded).
if python "$RELIABILITY_COMMONS/tools/inspect-gate/orchestration/dinomaly_patch.py" \
     "$DINOMALY_REPO/dinomaly_mvtec_uni.py" 2>&1 | tee "$RESULTS_DIR/patch.log"; then
  mark DINOMALY_PATCH OK
else
  mark DINOMALY_PATCH FAILED
fi

if [ "${#FAILED_MARKERS[@]}" -gt 0 ]; then
  echo "upstream gates failed -- refusing to train" >&2
  chain_epilogue "$RESULTS_DIR" "DINOMALY_BRANCHA_PARTIAL_DONE" "dinomaly_brancha"
  exit 1
fi

cd "$DINOMALY_REPO"

# count_scores DIR -> number of per-category score JSONs with >0 entries.
count_scores() {
  python - "$1" <<'PY'
import json, sys
from pathlib import Path
d = Path(sys.argv[1])
n = 0
for f in d.glob("scores_*.json"):
    try:
        if len(json.load(open(f))) > 0:
            n += 1
    except Exception:
        pass
print(n)
PY
}

# Stage 4: smoke -- tiny iteration count, full eval+dump path end-to-end.
smoke_dir="$RESULTS_DIR/smoke"
if [ "$(count_scores "$smoke_dir/run" 2>/dev/null)" = "$N_CATEGORIES" ]; then
  echo "skip smoke (already complete)"
  mark DINOMALY_SMOKE OK
else
  rm -rf "$smoke_dir"
  DINOMALY_SEED=0 DINOMALY_ITERS="$DINOMALY_SMOKE_ITERS" \
    python dinomaly_mvtec_uni.py --data_path "$DATA_ROOT" \
    --save_dir "$smoke_dir" --save_name run \
    2>&1 | tee "$RESULTS_DIR/smoke.log" | tail -40
  if [ "$(count_scores "$smoke_dir/run" 2>/dev/null)" = "$N_CATEGORIES" ]; then
    mark DINOMALY_SMOKE OK
  else
    mark DINOMALY_SMOKE FAILED
  fi
fi

# Stage 5: full training, one unified model per seed.
if [ "${#FAILED_MARKERS[@]}" -eq 0 ]; then
  for seed in $DINOMALY_SEEDS; do
    seed_dir="$RESULTS_DIR/seed_${seed}"
    if [ "$(count_scores "$seed_dir/run" 2>/dev/null)" = "$N_CATEGORIES" ] && [ -s "$seed_dir/run/model.pth" ]; then
      echo "skip seed $seed (already complete)"
      mark "DINOMALY_SEED_${seed}" OK
      continue
    fi
    DINOMALY_SEED="$seed" DINOMALY_ITERS="$DINOMALY_FULL_ITERS" \
      python dinomaly_mvtec_uni.py --data_path "$DATA_ROOT" \
      --save_dir "$seed_dir" --save_name run \
      2>&1 | tee "$RESULTS_DIR/train_seed${seed}.log" | grep -E "Mean:|iter \[|dump_image" || true
    if [ "$(count_scores "$seed_dir/run" 2>/dev/null)" = "$N_CATEGORIES" ] && [ -s "$seed_dir/run/model.pth" ]; then
      mark "DINOMALY_SEED_${seed}" OK
    else
      mark "DINOMALY_SEED_${seed}" FAILED
    fi
  done
else
  echo "smoke failed -- full training refused (disclosed)"
fi

if [ "${#FAILED_MARKERS[@]}" -eq 0 ]; then
  marker_name="DINOMALY_BRANCHA_ALL_DONE"
else
  marker_name="DINOMALY_BRANCHA_PARTIAL_DONE"
  echo "PARTIAL -- failed markers: ${FAILED_MARKERS[*]}"
fi
# Do NOT echo $marker_name here: the watcher greps this log for the marker,
# and chain_epilogue only emits it AFTER the results tar completes. A pre-tar
# echo made the watcher pull a still-growing tarball (2026-07-10 incident).
chain_epilogue "$RESULTS_DIR" "$marker_name" "dinomaly_brancha"
