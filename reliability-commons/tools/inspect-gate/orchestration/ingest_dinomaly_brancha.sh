#!/bin/bash
# ingest_dinomaly_brancha.sh -- box-side: merge Branch-A per-category score
# dumps per seed and ingest each into a canonical scores JSONL via
# score_dinomaly.py --mode dump-ingest (full-path keys match the box's
# /root/autodl-tmp/mvtec_ad layout). CPU-only, ~seconds per seed.
set -uo pipefail

# Non-interactive ssh does not load conda; ingest is stdlib-only so base works.
source /root/miniconda3/etc/profile.d/conda.sh 2>/dev/null && conda activate "${CHAIN_CONDA_ENV:-base}"

BA=/root/autodl-tmp/dinomaly_branchA
SD=/root/reliability-commons/tools/inspect-gate/orchestration/score_dinomaly.py
DATA=/root/autodl-tmp/mvtec_ad
OUT="$BA/canonical"
mkdir -p "$OUT"

# One invocation per (seed, category): a merged all-category dump poisons
# dump_ingest_category's basename-stem fallback (MVTec reuses 000.png stems
# across categories -> cross-category false matches -> duplicate image_ids).
CATS="carpet grid leather tile wood bottle cable capsule hazelnut metal_nut pill screw toothbrush transistor zipper"
fail=0
for s in 0 1 2 3 4; do
  seed_out="$OUT/scores_dinomaly_seed$s.jsonl"
  : > "$seed_out"
  for cat in $CATS; do
    PYTHONPATH=/root/reliability-commons python3 "$SD" --mode dump-ingest \
      --data-root "$DATA" \
      --category "$cat" \
      --scores-dump "$BA/seed_$s/run/scores_$cat.json" \
      --out "$OUT/tmp_seed${s}_${cat}.jsonl" || { fail=1; continue; }
    cat "$OUT/tmp_seed${s}_${cat}.jsonl" >> "$seed_out"
    rm -f "$OUT/tmp_seed${s}_${cat}.jsonl"
  done
done

echo "=== canonical line counts ==="
wc -l "$OUT"/*.jsonl
exit $fail
