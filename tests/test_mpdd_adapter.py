"""Torch-free unit tests for mpdd_results_2026-07-13/scripts/mpdd_adapter.py.

Synthesises the MPDD box output schema (Dinomaly per-category {path:score}
dumps + log.txt; PatchCore canonical JSONL) plus an mpdd_prep manifest, then
drives the adapter's adapt_* functions directly (module globals overridden to
a 2-category / 1-seed mini-run and a tmp CANON dir) -- asserting the canonical
JSONL is written, the box-log AUROC cross-check passes, and a count mismatch
REFUSES."""
import importlib.util
import json
from pathlib import Path

import numpy as np
import pytest

_IG = Path(__file__).resolve().parents[1]
_ADAPTER = _IG / "mpdd_results_2026-07-13" / "scripts" / "mpdd_adapter.py"
_spec = importlib.util.spec_from_file_location("mpdd_adapter", _ADAPTER)
adapter = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(adapter)

from inspect_gate import reproduction as _repro  # noqa: E402

# Mini fixture: 2 categories, 1 seed. (defect_type, stem, score, label).
DATA = {
    "bracket_black": [
        ("good", "000", 0.50, "good"), ("good", "001", 0.90, "good"),
        ("scratch", "000", 0.40, "defect"), ("scratch", "001", 0.80, "defect"),
        ("hole", "000", 0.95, "defect"),
    ],
    "tubes": [
        ("good", "000", 0.30, "good"), ("good", "001", 0.35, "good"),
        ("dent", "000", 0.70, "defect"), ("dent", "001", 0.20, "defect"),
    ],
}
CATS = ["bracket_black", "tubes"]


def _mpdd_path(cat, dtype, stem):
    return f"/root/autodl-tmp/MPDD/{cat}/test/{dtype}/{stem}.png"


def _write_manifest(tmp_path):
    per_category = {}
    for cat in CATS:
        rows = DATA[cat]
        per_category[cat] = {
            "n_train_good": 5,
            "n_test_good": sum(1 for r in rows if r[3] == "good"),
            "n_test_defect": sum(1 for r in rows if r[3] == "defect"),
            "test_split": sorted([[r[0], r[1]] for r in rows]),
        }
    manifest = {"categories": CATS, "per_category": per_category}
    p = tmp_path / "manifest.json"
    p.write_text(json.dumps(manifest))
    return p


def _write_box_dumps(pull, seed=0):
    run = pull / "dinomaly" / f"seed_{seed}" / "run"
    run.mkdir(parents=True, exist_ok=True)
    log_lines = []
    for cat in CATS:
        rows = DATA[cat]
        scores = {_mpdd_path(cat, dt, stem): sc for dt, stem, sc, _lab in rows}
        (run / f"scores_{cat}.json").write_text(json.dumps(scores))
        auroc = _repro.image_auroc(
            np.array([r[2] for r in rows], dtype=float),
            np.array([r[3] == "defect" for r in rows], dtype=bool),
        )
        log_lines.append(f"{cat}: I-Auroc:{auroc:.4f}, I-AP:0.0000, I-F1:0.0000, "
                         f"P-AUROC:0.0000, P-AP:0.0000, P-F1:0.0000, P-AUPRO:0.0000")
    (run / "log.txt").write_text("\n".join(log_lines) + "\n")

    pc = pull / "patchcore" / f"seed_{seed}"
    pc.mkdir(parents=True, exist_ok=True)
    for cat in CATS:
        recs = [{
            "image_id": f"{cat}_test_{dt}_{stem}", "category": cat, "split": "test",
            "score": sc, "label": lab, "defect_type": dt,
        } for dt, stem, sc, lab in DATA[cat]]
        (pc / f"scores_{cat}.jsonl").write_text(
            "\n".join(json.dumps(r) for r in recs) + "\n")


def _configure(tmp_path):
    adapter.SEEDS = [0]
    adapter.CATEGORIES = CATS
    adapter.CANON = tmp_path / "canonical"
    adapter.CANON.mkdir(parents=True, exist_ok=True)


def test_adapt_dinomaly_and_patchcore_ok(tmp_path):
    _configure(tmp_path)
    manifest = _write_manifest(tmp_path)
    pull = tmp_path / "pull"
    _write_box_dumps(pull)

    official = adapter.load_official_test_split(manifest)
    assert official["bracket_black"] == {("good", "000"), ("good", "001"),
                                         ("scratch", "000"), ("scratch", "001"), ("hole", "000")}

    dino = adapter.adapt_dinomaly(pull, official)
    assert dino[0]["max_abs_diff"] <= adapter.AUROC_XCHECK_TOL
    out = adapter.CANON / "scores_dinomaly_seed0.jsonl"
    assert out.exists()
    recs = [json.loads(l) for l in out.read_text().splitlines() if l.strip()]
    assert len(recs) == sum(len(DATA[c]) for c in CATS)
    # label join is correct (good iff defect_type good)
    for r in recs:
        assert (r["label"] == "good") == (r["defect_type"] == "good")

    pc = adapter.adapt_patchcore(pull, official)
    assert pc[0]["n_records"] == sum(len(DATA[c]) for c in CATS)


def test_adapt_dinomaly_refuses_on_count_mismatch(tmp_path):
    _configure(tmp_path)
    manifest = _write_manifest(tmp_path)
    pull = tmp_path / "pull"
    _write_box_dumps(pull)
    # drop one image from a dump -> split mismatch vs manifest -> refuse
    f = pull / "dinomaly" / "seed_0" / "run" / "scores_tubes.json"
    d = json.loads(f.read_text())
    d.pop(next(iter(d)))
    f.write_text(json.dumps(d))

    official = adapter.load_official_test_split(manifest)
    with pytest.raises(SystemExit):
        adapter.adapt_dinomaly(pull, official)
