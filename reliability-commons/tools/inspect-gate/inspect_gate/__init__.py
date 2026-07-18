"""inspect-gate: certified escaped-defect triage on MVTec AD.

A conformal three-way gate ({auto-pass, auto-reject, defer}) over any
anomaly-detection backbone's per-image scores, with a certified escaped-
defect rate and a certified false-reject rate, plus an excess-AURC audit
of field-standard threshold practice against the analytic random-deferral
null. See ``apps-design/01-APP-mvtec-triage.md`` for the full design spec
this package implements.

Lazy-import discipline (mirrors ``asr-gate``): this top-level package and
every module's import-time code path are torch/anomalib-free. Heavy deps
are imported inside the ``orchestration/score_*.py`` functions that
actually need them, never at module scope -- ``inspect-gate --help`` and
the full test suite run with no GPU/anomalib/torch installed.
"""

from __future__ import annotations

__version__ = "0.1.0.dev0"

__all__ = ["__version__"]
