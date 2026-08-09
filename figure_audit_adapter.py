"""Repository-local registration metadata for the INSPECT figure audit."""

from __future__ import annotations

from pathlib import Path
from typing import Dict

PROJECT_ID = "inspect-gate"
ADAPTER_PROTOCOL_VERSION = 1
FIGURE_MANIFEST = "tools/inspect-gate/manifests/figures.yaml"
MANUSCRIPT_MANIFEST = "tools/inspect-gate/manifests/manuscripts.yaml"


def describe() -> Dict[str, object]:
    """Return non-inferred adapter metadata for the shared protocol client."""
    return {
        "project_id": PROJECT_ID,
        "adapter_protocol_version": ADAPTER_PROTOCOL_VERSION,
        "figure_manifest": FIGURE_MANIFEST,
        "manuscript_manifest": MANUSCRIPT_MANIFEST,
    }


def manifest_paths(repo_root: Path) -> tuple[Path, Path]:
    """Return the two repository-local manifest paths."""
    return repo_root / FIGURE_MANIFEST, repo_root / MANUSCRIPT_MANIFEST
