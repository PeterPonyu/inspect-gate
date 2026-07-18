"""Synthetic MVTec-shaped score fixtures shared across inspect-gate tests.

No network, no GPU, no torch/anomalib: everything is generated in-process
with a controllable separation between good/defective score distributions
(higher score = more anomalous, per ``io.py``'s sign convention), so gate
calibration and the audit have KNOWN ground truth to check against.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence

import numpy as np

DEFAULT_DEFECT_TYPES = ("scratch", "dent", "crack", "contamination")


def make_synthetic_scores(
    categories: Sequence[str] = ("bottle", "screw", "carpet"),
    n_train_good: int = 200,
    n_test_good: int = 60,
    n_test_defect: int = 40,
    seed: int = 0,
    separation: float = 3.0,
    noise_sigma: float = 1.0,
    n_defect_types: int = 3,
) -> List[Dict[str, Any]]:
    """Build a canonical scores table with a KNOWN good/defect separation.

    Good scores ~ N(0, noise_sigma); defective scores ~ N(separation,
    noise_sigma) -- ``separation`` in score-sigma units controls how
    "easy" the synthetic AD problem is (higher = better-separated, mirrors
    a well-trained backbone; ``separation=0`` gives an uninformative
    score, useful for audit null-behavior tests).
    """
    rng = np.random.default_rng(seed)
    records: List[Dict[str, Any]] = []
    defect_types = list(DEFAULT_DEFECT_TYPES[:n_defect_types])

    for cat in categories:
        for i in range(n_train_good):
            records.append({
                "image_id": f"{cat}_train_good_{i:04d}",
                "category": cat,
                "split": "train",
                "score": float(rng.normal(0.0, noise_sigma)),
                "label": "good",
                "defect_type": "good",
            })
        for i in range(n_test_good):
            records.append({
                "image_id": f"{cat}_test_good_{i:04d}",
                "category": cat,
                "split": "test",
                "score": float(rng.normal(0.0, noise_sigma)),
                "label": "good",
                "defect_type": "good",
            })
        for i in range(n_test_defect):
            dt = defect_types[i % len(defect_types)]
            records.append({
                "image_id": f"{cat}_test_defect_{i:04d}",
                "category": cat,
                "split": "test",
                "score": float(rng.normal(separation, noise_sigma)),
                "label": "defect",
                "defect_type": dt,
            })
    return records


def make_uninformative_scores(
    categories: Sequence[str] = ("bottle", "screw"),
    n_train_good: int = 100,
    n_test_good: int = 50,
    n_test_defect: int = 50,
    seed: int = 0,
) -> List[Dict[str, Any]]:
    """Scores drawn from the SAME distribution regardless of label -- a
    completely uninformative confidence score, used to check the audit
    correctly reports null (non-significant, excess_aurc ~ 0) results."""
    return make_synthetic_scores(
        categories=categories, n_train_good=n_train_good, n_test_good=n_test_good,
        n_test_defect=n_test_defect, seed=seed, separation=0.0, noise_sigma=1.0,
    )
