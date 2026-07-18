#!/bin/bash
# next_boot_inspect_ksdd2.sh -- inspect-gate KSDD2 ride-along chain
# (WORKLOAD-BENCHMARK-2026-07-15.md: real-production surface-defect realism,
# both backbones, 5 seeds, replaying the frozen gate/V1/audit pipeline
# unchanged). KSDD2 is a BINARY single-category dataset -> the pipeline's
# per-category machinery treats it as exactly 1 category, "kolektor_surface".
#
# Mirrors next_boot_inspect_mpdd.sh conventions: content-gated markers
# everywhere, DISTINCT marker names, no pre-epilogue marker echo (2026-07-10
# watcher-race rule). The ONE structural difference: the STAGING stage
# (download + extract + ksdd2_prep tree-build + manifest freeze) is NO-CARD --
# it runs and marks KSDD2_STAGED *before* the GPU-presence gate, so a
# no-card->GPU box can complete staging (and have a pullable built tree +
# manifest) even if a GPU never arrives. Only the PatchCore/Dinomaly scoring
# stages sit behind the GPU gate.
#
# KSDD2 ships FLAT (train/*.png + train/*_GT.png; test/ likewise), NOT native
# MVTec, so ksdd2_prep.py CONVERTS it (symlinks into kolektor_surface/{train,
# test}/...) and refuses on any count/structure mismatch.
#
# Data source (credential-free, PUBLIC -- CC BY-NC-SA 4.0, no form/login):
#   1. $KSDD2_LOCAL_ZIP  (a zip already staged on the box -- fastest, preferred);
#   2. $KSDD2_ZIP_URL    (default: the official ViCoS mirror go.vicos.si, which
#      302-redirects to data.vicos.si/datasets/KSDD/KolektorSDD2.zip, ~853 MB).
#
# Usage on the box:  bash next_boot_inspect_ksdd2.sh
# Validate locally:  bash next_boot_inspect_ksdd2.sh --dry-run   (no GPU, no
#      download, no compute -- checks every referenced script + prints the plan)

set -uo pipefail

DRY_RUN=0
[ "${1:-}" = "--dry-run" ] && DRY_RUN=1

# --- paths (env-overridable; default to on-box layout, but --dry-run derives
#     the repo root from this script's own location so it validates locally) --
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
IG_ROOT="${IG_ROOT:-$(cd "$SCRIPT_DIR/.." && pwd)}"            # inspect-gate dir
ORCH="$IG_ROOT/orchestration"
RELIABILITY_COMMONS="${RELIABILITY_COMMONS:-/root/reliability-commons}"
DINOMALY_HOME="${DINOMALY_HOME:-/root/Dinomaly}"

# --- tunables (named defaults; no inline magic denominators) ----------------
RESULTS_DIR="${RESULTS_DIR:-/root/autodl-tmp/ksdd2_brancha}"
MARKERS_DIR="$RESULTS_DIR/markers"
KSDD2_NATIVE_ROOT="${KSDD2_NATIVE_ROOT:-/root/autodl-tmp/KSDD2}"          # flat train/ test/
KSDD2_MVTEC_ROOT="${KSDD2_MVTEC_ROOT:-/root/autodl-tmp/KSDD2_mvtec}"      # built MVTec tree
KSDD2_LOCAL_ZIP="${KSDD2_LOCAL_ZIP:-}"                                    # preferred if set
KSDD2_ZIP_URL="${KSDD2_ZIP_URL:-https://go.vicos.si/kolektorsdd2}"
KSDD2_MANIFEST="${KSDD2_MANIFEST:-$RESULTS_DIR/ksdd2_split_manifest.json}"
CATS="kolektor_surface"
SEEDS="${KSDD2_SEEDS:-0 1 2 3 4}"
GPU_WAIT_S="${KSDD2_GPU_WAIT_S:-172800}"
DINOMALY_ITERS_N="${KSDD2_DINOMALY_ITERS:-10000}"
EXPECT_TRAIN_GOOD="${KSDD2_EXPECT_TRAIN_GOOD:-2085}"
EXPECT_TEST_GOOD="${KSDD2_EXPECT_TEST_GOOD:-894}"
EXPECT_TEST_DEFECT="${KSDD2_EXPECT_TEST_DEFECT:-110}"
EXPECT_TRAIN_DEFECT_EXCLUDED="${KSDD2_EXPECT_TRAIN_DEFECT_EXCLUDED:-246}"
SMOKE_SEED="${KSDD2_SMOKE_SEED:-0}"                                       # one-cell smoke gate
# Train-holdout arm (mirrors MPDD stage 2b; G2 calibrates on a 20% train-good
# holdout). score_patchcore.py --holdout-frac is flag-gated + prereg-NEUTRAL
# (0.0 == byte-identical primary behavior); the PRIMARY stage-2 arm never sets
# it, so the primary protocol stays untouched.
HOLDOUT_ARM="${KSDD2_HOLDOUT_ARM:-1}"                                     # 0 disables stage 2b
HOLDOUT_FRAC="${KSDD2_HOLDOUT_FRAC:-0.2}"
HOLDOUT_SEED="${KSDD2_HOLDOUT_SEED:-0}"

step() { echo "== $1 =="; }

# ---------------------------------------------------------------------------
# --dry-run: validate every referenced script + print the plan, then exit 0.
# Runs fully on the workstation (no /root, no GPU, no network).
# ---------------------------------------------------------------------------
if [ "$DRY_RUN" -eq 1 ]; then
  echo "=== next_boot_inspect_ksdd2.sh --dry-run ==="
  echo "IG_ROOT=$IG_ROOT"
  rc=0
  need=(
    "$ORCH/dinomaly_ksdd2_uni.py"
    "$ORCH/dinomaly_patch.py"
    "$ORCH/ksdd2_prep.py"
    "$ORCH/mvtec_layout.py"
    "$ORCH/score_patchcore.py"
    "$ORCH/score_dinomaly.py"
  )
  for f in "${need[@]}"; do
    if [ -s "$f" ]; then echo "  OK   $f"; else echo "  MISS $f"; rc=1; fi
  done
  # dinomaly_ksdd2_uni.py must carry the P1-P5 patch anchors dinomaly_patch.py
  # needs, plus the KSDD2 single-category roster.
  echo "--- dinomaly_ksdd2_uni.py patch-anchor check ---"
  py="$ORCH/dinomaly_ksdd2_uni.py"
  for anchor in \
    "setup_seed(1)" \
    "total_iters = 10000" \
    "device = 'cuda:1' if torch.cuda.is_available() else 'cpu'" \
    "if __name__ == '__main__':" \
    "kolektor_surface"; do
    if grep -qF "$anchor" "$py" 2>/dev/null; then echo "  OK   anchor: $anchor"; else echo "  MISS anchor: $anchor"; rc=1; fi
  done
  echo "--- plan ---"
  echo "  categories : $CATS  (binary single-category dataset)"
  echo "  seeds      : $SEEDS"
  echo "  expect     : train-good=$EXPECT_TRAIN_GOOD test-good=$EXPECT_TEST_GOOD"
  echo "               test-defect=$EXPECT_TEST_DEFECT excluded-train-defect=$EXPECT_TRAIN_DEFECT_EXCLUDED"
  echo "  data src   : local=[${KSDD2_LOCAL_ZIP:-<unset>}] url=[$KSDD2_ZIP_URL]"
  echo "  stages     : S NO-CARD stage+convert(ksdd2_prep, marks KSDD2_STAGED before GPU gate)"
  echo "               -> 0 gpu-gate -> 2 patchcore 1x5 (PRIMARY)"
  echo "               -> 2b patchcore train-holdout arm (frac=$HOLDOUT_FRAC seed=$HOLDOUT_SEED,"
  echo "                   phase-0 one-cell smoke w/ provenance-sidecar gate BEFORE 1x5;"
  echo "                   enabled=$HOLDOUT_ARM; separate patchcore_holdout/ output)"
  echo "               -> 3 dinomaly uni x5 (patch dinomaly_ksdd2_uni) -> smoke gate"
  echo "               -> 4 latency env -> epilogue (KSDD2_BRANCHA_ALL_DONE)"
  if [ "$rc" -eq 0 ]; then echo "DRY_RUN_OK"; else echo "DRY_RUN_FAILED (missing files/anchors above)"; fi
  exit "$rc"
fi

# ---------------------------------------------------------------------------
# Real box run below.
# ---------------------------------------------------------------------------
export CHAIN_LOG="${CHAIN_LOG:-/root/ksdd2_brancha.log}"
source "$RELIABILITY_COMMONS/tools/boxkit/chain_lib.sh"
conda activate base 2>/dev/null || true
chain_prologue

mkdir -p "$RESULTS_DIR" "$MARKERS_DIR"

FAILED_MARKERS=()
mark() { local n="$1" s="$2"; printf '%s\n' "$s" > "$MARKERS_DIR/${n}.marker"; echo "MARKER ${n}=${s}"
  { [ "$s" = "FAILED" ] || [ "$s" = "REFUSED" ]; } && FAILED_MARKERS+=("$n"); return 0; }

# --- Stage S: NO-CARD staging (download + extract + convert + freeze) -------
# Runs BEFORE the GPU gate: download/prep need no GPU, so a no-card box can
# still land the built MVTec tree + manifest (pullable) even if no GPU arrives.
step "S: KSDD2 NO-CARD staging (download + extract + ksdd2_prep convert)"
if [ ! -d "$KSDD2_MVTEC_ROOT/kolektor_surface/train/good" ]; then
  zip_ok=1
  if [ ! -d "$KSDD2_NATIVE_ROOT/train" ]; then
    zip=""
    if [ -n "$KSDD2_LOCAL_ZIP" ] && [ -s "$KSDD2_LOCAL_ZIP" ]; then
      zip="$KSDD2_LOCAL_ZIP"; echo "using local zip $zip"
    else
      zip="/root/autodl-tmp/KolektorSDD2.zip"
      echo "downloading KSDD2 from $KSDD2_ZIP_URL"
      curl -sSL -C - -o "$zip" "$KSDD2_ZIP_URL" || echo "warning: KSDD2 download non-zero"
    fi
    # Integrity gate (2026-07-16, prompted by a box closed mid-download): a
    # zip left partial by an interrupted `curl -C -` resume can extract
    # "successfully enough" for ksdd2_prep's exact-count check to still pass
    # while one truncated-but-still-PIL-decodable PNG gets silently
    # mis-labelled good/defect -- the count gate does NOT catch that. Test
    # the archive BEFORE extracting; on failure, delete and re-fetch clean
    # (no -C -, since the broken byte range itself may be the culprit) once,
    # then refuse (no extraction attempted, staging marked FAILED, downstream
    # stages self-gate off KSDD2_STAGED and disclose-skip per existing
    # convention -- no early chain abort here, matching how a ksdd2_prep.py
    # count-mismatch failure is already handled below).
    if ! unzip -t "$zip" > /dev/null 2>&1; then
      echo "warning: zip integrity check failed for $zip -- possible partial/corrupt download"
      if [ "$zip" = "/root/autodl-tmp/KolektorSDD2.zip" ]; then
        echo "re-fetching clean (no -C resume) and re-testing once"
        rm -f "$zip"
        curl -sSL -o "$zip" "$KSDD2_ZIP_URL" || echo "warning: KSDD2 clean re-download non-zero"
        if ! unzip -t "$zip" > /dev/null 2>&1; then
          echo "REFUSE: KSDD2 zip still fails integrity check after clean re-download -- not extracting"
          zip_ok=0
        fi
      else
        echo "REFUSE: local zip $KSDD2_LOCAL_ZIP failed integrity check -- re-stage it manually; not extracting"
        zip_ok=0
      fi
    fi
    if [ "$zip_ok" -eq 1 ]; then
      mkdir -p "$KSDD2_NATIVE_ROOT"
      # zip may wrap train/ test/ in a top-level dir -- extract then normalise so
      # $KSDD2_NATIVE_ROOT holds train/ and test/ directly.
      tmpx="/root/autodl-tmp/_ksdd2_extract"; rm -rf "$tmpx"; mkdir -p "$tmpx"
      unzip -q -o "$zip" -d "$tmpx" || echo "warning: unzip non-zero"
      src=""
      if [ -d "$tmpx/train" ] && [ -d "$tmpx/test" ]; then src="$tmpx"
      else src="$(dirname "$(find "$tmpx" -type d -name train | head -1)")"; fi
      [ -n "${src:-}" ] && cp -rn "$src"/train "$src"/test "$KSDD2_NATIVE_ROOT"/ 2>/dev/null
    fi
  fi
  if [ "$zip_ok" -eq 0 ]; then
    mark KSDD2_STAGED FAILED
  else
  sha=$(sha256sum "${KSDD2_LOCAL_ZIP:-/root/autodl-tmp/KolektorSDD2.zip}" 2>/dev/null | awk '{print $1}')
  if python3 "$ORCH/ksdd2_prep.py" "$KSDD2_NATIVE_ROOT" "$KSDD2_MVTEC_ROOT" "$KSDD2_MANIFEST" \
       --expect-train-good "$EXPECT_TRAIN_GOOD" --expect-test-good "$EXPECT_TEST_GOOD" \
       --expect-test-defect "$EXPECT_TEST_DEFECT" \
       --expect-train-defect-excluded "$EXPECT_TRAIN_DEFECT_EXCLUDED" \
       --archive-sha256 "${sha:-unknown}" 2>&1 | tee "$RESULTS_DIR/ksdd2_prep.log" | grep -q "KSDD2_PREP_OK"; then
    mark KSDD2_STAGED OK
  else
    mark KSDD2_STAGED FAILED
  fi
  fi
else
  echo "KSDD2 MVTec tree already present; re-freezing manifest (verify only)"
  sha=$(sha256sum "${KSDD2_LOCAL_ZIP:-/root/autodl-tmp/KolektorSDD2.zip}" 2>/dev/null | awk '{print $1}')
  if python3 "$ORCH/ksdd2_prep.py" "$KSDD2_NATIVE_ROOT" "$KSDD2_MVTEC_ROOT" "$KSDD2_MANIFEST" \
       --expect-train-good "$EXPECT_TRAIN_GOOD" --expect-test-good "$EXPECT_TEST_GOOD" \
       --expect-test-defect "$EXPECT_TEST_DEFECT" \
       --expect-train-defect-excluded "$EXPECT_TRAIN_DEFECT_EXCLUDED" \
       --no-build-tree --archive-sha256 "${sha:-unknown}" 2>&1 | tee "$RESULTS_DIR/ksdd2_prep.log" | grep -q "KSDD2_PREP_OK"; then
    mark KSDD2_STAGED OK
  else
    mark KSDD2_STAGED FAILED
  fi
fi

# --- Stage 0: GPU-presence gate (scoring stages only) ----------------------
step "0: GPU wait (up to ${GPU_WAIT_S}s)"
waited=0
until nvidia-smi --query-gpu=name --format=csv,noheader 2>/dev/null | grep -q .; do
  sleep 60; waited=$((waited+60)); [ "$waited" -ge "$GPU_WAIT_S" ] && break
done
if nvidia-smi --query-gpu=name --format=csv,noheader 2>/dev/null | grep -q .; then
  mark KSDD2_GPU_PRESENT OK
else
  mark KSDD2_GPU_PRESENT REFUSED
  echo "no GPU within ${GPU_WAIT_S}s -- staging done + pullable; aborting scoring (disclosed)"
  chain_epilogue "$RESULTS_DIR" "KSDD2_BRANCHA_PARTIAL_DONE" "ksdd2_brancha"; exit 1
fi

# --- Stage 2: PatchCore scoring, 1 cat x 5 seeds ---------------------------
step "2: PatchCore KSDD2 (1 cat x seeds [$SEEDS])"
if [ "$(cat "$MARKERS_DIR/KSDD2_STAGED.marker" 2>/dev/null)" = "OK" ]; then
  conda activate "${PATCHCORE_ENV:-anomalib}" || conda activate base
  pc_fail=0
  for s in $SEEDS; do
    out="$RESULTS_DIR/patchcore/seed_${s}"; mkdir -p "$out"
    for c in $CATS; do
      f="$out/scores_${c}.jsonl"
      [ -s "$f" ] && { echo "skip $f"; continue; }
      python3 "$ORCH/score_patchcore.py" --data-root "$KSDD2_MVTEC_ROOT" --category "$c" \
        --seed "$s" --device cuda --out "$f" \
        || echo "warning: patchcore $c seed $s non-zero -- gate below authoritative"
      [ -s "$f" ] || pc_fail=1
      rm -rf /root/autodl-tmp/anomalib_results/* 2>/dev/null   # anomalib fills the data disk otherwise
    done
  done
  n_cells=$(find "$RESULTS_DIR/patchcore" -name "scores_*.jsonl" -size +0 | wc -l)
  n_expect=$(( $(echo $CATS | wc -w) * $(echo $SEEDS | wc -w) ))
  echo "patchcore cells: $n_cells / $n_expect"
  if [ "$n_cells" -eq "$n_expect" ] && [ "$pc_fail" -eq 0 ]; then mark KSDD2_PATCHCORE OK; else mark KSDD2_PATCHCORE FAILED; fi
else
  mark KSDD2_PATCHCORE SKIPPED_DISCLOSED
fi

# --- Stage 2b: PatchCore train-holdout arm (G2 rescue; mirrors MPDD 2b) -----
step "2b: PatchCore train-holdout arm (frac=$HOLDOUT_FRAC, enabled=$HOLDOUT_ARM)"
if [ "$HOLDOUT_ARM" = "1" ] && [ "$(cat "$MARKERS_DIR/KSDD2_STAGED.marker" 2>/dev/null)" = "OK" ]; then
  conda activate "${PATCHCORE_ENV:-anomalib}" || conda activate base
  smk="$RESULTS_DIR/patchcore_holdout_smoke"; mkdir -p "$smk"
  sf="$smk/scores_kolektor_surface.jsonl"
  python3 "$ORCH/score_patchcore.py" --data-root "$KSDD2_MVTEC_ROOT" --category kolektor_surface \
    --seed "$SMOKE_SEED" --device cuda --holdout-frac "$HOLDOUT_FRAC" \
    --holdout-seed "$HOLDOUT_SEED" --out "$sf" \
    || echo "warning: holdout smoke non-zero -- gate below authoritative"
  rm -rf /root/autodl-tmp/anomalib_results/* 2>/dev/null
  # Content gate: scores present AND the provenance sidecar carries a
  # non-empty holdout_ids_by_category (proves the partition + holdout predict ran).
  if [ -s "$sf" ] && python3 - "$sf" << 'PY'
import json, sys
from pathlib import Path
p = Path(sys.argv[1]).with_suffix(".holdout_provenance.json")
d = json.load(open(p))
by_cat = d.get("holdout_ids_by_category") or {}
n = sum(len(v) for v in by_cat.values())
assert n > 0, f"empty holdout_ids_by_category in {p}"
print(f"holdout smoke: {n} held-out train-good ids stamped "
      f"across {len(by_cat)} categories")
PY
  then
    mark KSDD2_HOLDOUT_SMOKE OK
    ho_fail=0
    for s in $SEEDS; do
      out="$RESULTS_DIR/patchcore_holdout/seed_${s}"; mkdir -p "$out"
      for c in $CATS; do
        f="$out/scores_${c}.jsonl"
        [ -s "$f" ] && { echo "skip $f"; continue; }
        python3 "$ORCH/score_patchcore.py" --data-root "$KSDD2_MVTEC_ROOT" --category "$c" \
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
    if [ "$n_ho" -eq "$n_ho_expect" ] && [ "$ho_fail" -eq 0 ]; then mark KSDD2_PATCHCORE_HOLDOUT OK
    else mark KSDD2_PATCHCORE_HOLDOUT FAILED; fi
  else
    mark KSDD2_HOLDOUT_SMOKE FAILED
    mark KSDD2_PATCHCORE_HOLDOUT SKIPPED_DISCLOSED
    echo "holdout smoke failed -- primary arm unaffected; holdout arm skipped (disclosed)"
  fi
elif [ "$HOLDOUT_ARM" != "1" ]; then
  mark KSDD2_PATCHCORE_HOLDOUT DISABLED_DISCLOSED
else
  mark KSDD2_PATCHCORE_HOLDOUT SKIPPED_DISCLOSED
fi

# --- Stage 3: Dinomaly KSDD2 unified, 5 seeds ------------------------------
step "3: Dinomaly KSDD2 uni (patch + seeds [$SEEDS] x ${DINOMALY_ITERS_N} iters)"
if [ "$(cat "$MARKERS_DIR/KSDD2_STAGED.marker" 2>/dev/null)" = "OK" ]; then
  conda activate "${DINOMALY_ENV:-dinomaly}" || conda activate base
  cp -f "$ORCH/dinomaly_ksdd2_uni.py" "$DINOMALY_HOME/dinomaly_ksdd2_uni.py"
  if python3 "$ORCH/dinomaly_patch.py" "$DINOMALY_HOME/dinomaly_ksdd2_uni.py"; then
    mark KSDD2_DINOMALY_PATCH OK
    dm_fail=0
    for s in $SEEDS; do
      run="$RESULTS_DIR/dinomaly/seed_${s}"; mkdir -p "$run"
      if [ -s "$run/run/model.pth" ]; then echo "skip seed $s"; else
        ( cd "$DINOMALY_HOME" && DINOMALY_SEED=$s DINOMALY_ITERS=$DINOMALY_ITERS_N DINOMALY_DEVICE=cuda:0 \
          python3 dinomaly_ksdd2_uni.py --data_path "$KSDD2_MVTEC_ROOT" --save_dir "$run" --save_name run \
          > "$RESULTS_DIR/dinomaly_seed${s}.log" 2>&1 ) || echo "warning: dinomaly seed $s non-zero"
      fi
      n_dumps=$(find "$run/run" -name "scores_*.json" -size +0 2>/dev/null | wc -l)
      echo "seed $s dumps: $n_dumps / 1"
      if [ "$n_dumps" -eq 1 ] && [ -s "$run/run/model.pth" ]; then mark "KSDD2_DINOMALY_SEED_${s}" OK
      else mark "KSDD2_DINOMALY_SEED_${s}" FAILED; dm_fail=1; fi

      # One-cell smoke gate: after the FIRST seed, sanity-check its own log
      # I-AUROC mean is a plausible detector (>= 0.70 floor; KSDD2 has no
      # repo-confirmed published Dinomaly target, so this is a loose sanity
      # bound, not a reproduction gate). Disclosed, non-fatal.
      if [ "$s" = "$SMOKE_SEED" ]; then
        mean=$(grep -oE "Mean: I-Auroc:[0-9.]+" "$run/run/log.txt" 2>/dev/null | tail -1 | grep -oE "[0-9.]+$")
        echo "smoke: seed $s mean I-AUROC = ${mean:-NA} (KSDD2 descriptive; no published target)"
        awk -v m="${mean:-0}" 'BEGIN{exit !(m+0 >= 0.70)}' \
          && mark KSDD2_SMOKE_GATE OK \
          || { mark KSDD2_SMOKE_GATE FAILED; echo "smoke gate: mean ${mean:-NA} < 0.70 floor -- 1-cat uni port may need attention (disclosed)"; }
      fi
    done
    [ "$dm_fail" -eq 0 ] && mark KSDD2_DINOMALY OK || mark KSDD2_DINOMALY FAILED
  else
    mark KSDD2_DINOMALY_PATCH FAILED; mark KSDD2_DINOMALY SKIPPED_DISCLOSED
  fi
else
  mark KSDD2_DINOMALY SKIPPED_DISCLOSED
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
tar -C "$RESULTS_DIR" -czf "$RESULTS_DIR/ksdd2_brancha_pull.tgz" \
  patchcore patchcore_holdout patchcore_holdout_smoke dinomaly \
  ksdd2_split_manifest.json markers 2>/dev/null \
  && echo "packed ksdd2_brancha_pull.tgz" || echo "pack non-zero (disclosed)"

if [ "${#FAILED_MARKERS[@]}" -eq 0 ]; then
  marker_name="KSDD2_BRANCHA_ALL_DONE"
else
  marker_name="KSDD2_BRANCHA_PARTIAL_DONE"
  echo "KSDD2_BRANCHA_PARTIAL -- failed: ${FAILED_MARKERS[*]}"
fi
chain_epilogue "$RESULTS_DIR" "$marker_name" "ksdd2_brancha"
