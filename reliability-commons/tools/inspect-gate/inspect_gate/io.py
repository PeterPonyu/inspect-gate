"""Canonical scores-JSONL schema, validation, and I/O.

The gate never sees pixels, only scores + labels (design §2.2): every
``inspect-gate`` command downstream of ``score`` consumes ONE canonical
record shape, regardless of which backbone produced it (PatchCore,
Dinomaly, or a precomputed table ingested via ``--backbone scores-json``).
This module is the only schema-aware code in the tool.

Canonical fields (per image)
-----------------------------
Required:
  - ``image_id`` (str): unique image id (unique within the whole table,
    not just within a category -- callers should prefix with category if
    their source ids collide, e.g. MVTec's per-category ``000.png`` reuse).
  - ``category`` (str): MVTec category name (e.g. ``"bottle"``), the
    primary Mondrian/blocking unit throughout the tool.
  - ``split`` (str): the ORIGINAL MVTec split the image came from, one of
    ``"train"`` or ``"test"``. This is NOT the calibration/evaluation half
    assignment (that is a derived, in-memory role computed by
    :mod:`inspect_gate.splits` at calibration time, never persisted back
    into the canonical scores file -- ``splits.py``'s module docstring
    explains why).
  - ``score`` (float): the anomaly score. **Sign convention (load-bearing,
    stated once here and referenced everywhere else in this package):
    HIGHER SCORE = MORE ANOMALOUS.** This is the standard PatchCore/
    Dinomaly/anomalib convention and is the OPPOSITE of the sibling
    ``asr-gate`` tool's "higher = more confident" convention -- do not port
    sign assumptions from that package.
  - ``label`` (str): ground-truth label, one of ``"good"`` or ``"defect"``.
  - ``defect_type`` (str): the specific MVTec defect subtype (e.g.
    ``"broken_large"``) for defective images, or the literal string
    ``"good"`` for non-defective images (never ``null`` -- a defect-free
    image's defect_type is defined to be "good", matching MVTec's own
    per-category test subdirectory naming, so it can be used as a Mondrian
    stratum key directly without a null-check at every call site).

A table with an unpartitioned mix of categories/splits is expected and
normal (e.g. one scores-JSONL per (backbone, seed) covering all staged
categories) -- callers filter by ``category``/``split``/``label`` as
needed; this module does not assume any particular grouping.
"""

from __future__ import annotations

import json
import math
import os
from pathlib import Path
from typing import Any, Dict, List, Union

__all__ = [
    "SchemaError",
    "REQUIRED_FIELDS",
    "VALID_LABELS",
    "VALID_SPLITS",
    "GOOD_DEFECT_TYPE",
    "load_jsonl",
    "write_jsonl",
    "validate_scores",
    "load_scores",
    "to_jsonable",
    "category_counts",
]

REQUIRED_FIELDS = ("image_id", "category", "split", "score", "label", "defect_type")
VALID_LABELS = ("good", "defect")
VALID_SPLITS = ("train", "test")
GOOD_DEFECT_TYPE = "good"


class SchemaError(ValueError):
    """Raised on any scores-table validation failure, with a precise,
    actionable message (which record, which field, what was expected)."""


def _is_real_number(x: Any) -> bool:
    return isinstance(x, (int, float)) and not isinstance(x, bool)


def load_jsonl(path: Union[str, Path]) -> List[Dict[str, Any]]:
    """Load a JSON-Lines file (one JSON object per non-blank line)."""
    path = Path(path)
    records: List[Dict[str, Any]] = []
    with open(path, "r", encoding="utf-8") as f:
        for lineno, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError as e:
                raise SchemaError(f"{path}:{lineno}: invalid JSON ({e})") from e
    if not records:
        raise SchemaError(f"{path}: contains no records")
    return records


def to_jsonable(obj: Any) -> Any:
    """Recursively convert numpy scalars/arrays into plain Python types."""
    try:
        import numpy as np
    except ImportError:  # pragma: no cover - numpy is a hard dep elsewhere
        np = None  # type: ignore[assignment]
    if isinstance(obj, dict):
        return {str(k): to_jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [to_jsonable(v) for v in obj]
    if np is not None:
        if isinstance(obj, np.ndarray):
            return [to_jsonable(v) for v in obj.tolist()]
        if isinstance(obj, np.floating):
            return float(obj)
        if isinstance(obj, np.integer):
            return int(obj)
        if isinstance(obj, np.bool_):
            return bool(obj)
    return obj


def write_jsonl(path: Union[str, Path], records: List[Dict[str, Any]]) -> None:
    """Write a list of JSON-serializable records as JSON-Lines, atomically:
    the records are written to a sibling ``<path>.tmp`` file first (flushed
    + fsynced), then ``os.replace`` renames it onto ``path`` -- a crash or
    exception mid-write can never leave a partial/corrupt file at ``path``
    itself (a stray ``.tmp`` sibling is the worst case, cleaned up on
    failure below, and harmlessly overwritten by the next successful write
    otherwise)."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    try:
        with open(tmp_path, "w", encoding="utf-8") as f:
            for rec in records:
                f.write(json.dumps(to_jsonable(rec), ensure_ascii=False) + "\n")
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, path)
    except BaseException:
        tmp_path.unlink(missing_ok=True)
        raise


def validate_scores(records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Validate + normalize a list of raw records into canonical score rows.

    Raises :class:`SchemaError` identifying the offending record (position
    and, if available, ``image_id``) on any problem. Duplicate ``image_id``
    values ARE allowed across different ``category``/``split`` combinations
    are NOT allowed globally -- ``image_id`` must be globally unique in one
    table (see module docstring: prefix with category upstream if needed).
    """
    if not isinstance(records, list) or len(records) == 0:
        raise SchemaError("scores table must be a non-empty list of records")

    normalized: List[Dict[str, Any]] = []
    seen_ids = set()

    for i, rec in enumerate(records):
        tag = f"record[{i}]"
        if not isinstance(rec, dict):
            raise SchemaError(f"{tag}: expected an object, got {type(rec).__name__}")
        image_id = rec.get("image_id")
        if image_id is not None:
            tag = f"record[{i}] (image_id={image_id!r})"

        for field in REQUIRED_FIELDS:
            if field not in rec or rec[field] is None:
                raise SchemaError(f"{tag}: missing required field '{field}'")

        if not isinstance(rec["image_id"], (str, int)):
            raise SchemaError(f"{tag}: 'image_id' must be str or int")
        image_id_norm = str(rec["image_id"])
        if image_id_norm in seen_ids:
            raise SchemaError(f"{tag}: duplicate image_id {image_id_norm!r}")
        seen_ids.add(image_id_norm)

        if not isinstance(rec["category"], str) or not rec["category"]:
            raise SchemaError(f"{tag}: 'category' must be a non-empty string")
        if rec["split"] not in VALID_SPLITS:
            raise SchemaError(f"{tag}: 'split' must be one of {VALID_SPLITS}, got {rec['split']!r}")
        if not _is_real_number(rec["score"]):
            raise SchemaError(f"{tag}: 'score' must be a number")
        if not math.isfinite(rec["score"]):
            raise SchemaError(f"{tag}: 'score' must be finite, got {rec['score']!r}")
        if rec["label"] not in VALID_LABELS:
            raise SchemaError(f"{tag}: 'label' must be one of {VALID_LABELS}, got {rec['label']!r}")
        if not isinstance(rec["defect_type"], str) or not rec["defect_type"]:
            raise SchemaError(f"{tag}: 'defect_type' must be a non-empty string")
        if rec["label"] == "good" and rec["defect_type"] != GOOD_DEFECT_TYPE:
            raise SchemaError(
                f"{tag}: label='good' requires defect_type={GOOD_DEFECT_TYPE!r}, "
                f"got {rec['defect_type']!r}"
            )
        if rec["label"] == "defect" and rec["defect_type"] == GOOD_DEFECT_TYPE:
            raise SchemaError(
                f"{tag}: label='defect' cannot have defect_type={GOOD_DEFECT_TYPE!r}"
            )

        normalized.append(
            {
                "image_id": image_id_norm,
                "category": rec["category"],
                "split": rec["split"],
                "score": float(rec["score"]),
                "label": rec["label"],
                "defect_type": rec["defect_type"],
            }
        )

    return normalized


def load_scores(path: Union[str, Path]) -> List[Dict[str, Any]]:
    """Load + validate a canonical scores table from a ``.jsonl`` file."""
    path = Path(path)
    if path.suffix != ".jsonl":
        raise SchemaError(
            f"{path}: unrecognized extension {path.suffix!r}; expected .jsonl "
            "(the canonical inspect-gate scores-table format)"
        )
    return validate_scores(load_jsonl(path))


def category_counts(records: List[Dict[str, Any]]) -> Dict[str, Dict[str, int]]:
    """Per-category {n_total, n_good, n_defect} counts -- the Phase-0
    deliverable the design doc requires be frozen from realized data,
    never assumed (§3.2: "no per-category count appears in this design as
    fact")."""
    counts: Dict[str, Dict[str, int]] = {}
    for r in records:
        c = counts.setdefault(r["category"], {"n_total": 0, "n_good": 0, "n_defect": 0})
        c["n_total"] += 1
        c["n_good" if r["label"] == "good" else "n_defect"] += 1
    return counts
