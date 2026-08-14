#!/usr/bin/env python3
"""Build and verify the flat RiE LaTeX source package."""

from __future__ import annotations

import hashlib
import re
import shutil
import subprocess
import tempfile
import zipfile
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
BUILD_DATE = date(2026, 8, 11)
STAMP = (*BUILD_DATE.timetuple()[:3], 12, 0, 0)
STEM = f"inspect_rie_submission_source_{BUILD_DATE.isoformat()}"

FIGURES = (
    "fig-overview.pdf",
    "fig-scoreanatomy.pdf",
    "fig-samples.pdf",
    "fig-categorymap.pdf",
    "fig-alphafrontier.pdf",
    "fig-calfraction.pdf",
    "fig-calplanning.pdf",
    "fig-crcbaseline.pdf",
    "fig-opcost.pdf",
    "fig-g2delta.pdf",
    "fig-binding-escaped.pdf",
    "fig-binding-fr.pdf",
    "fig-validity.pdf",
    "fig-deferral.pdf",
    "fig-jointmon.pdf",
    "fig-xdet.pdf",
    "fig-mondrian-1.pdf",
    "fig-mondrian-2.pdf",
)

SOURCES = {
    "paper_rie.tex": HERE / "paper_rie.tex",
    "paper_rie.bbl": HERE / "paper_rie.bbl",
    "refs.bib": HERE / "refs.bib",
    **{f"figures/{name}": HERE / "figures" / name for name in FIGURES},
}

FORBIDDEN_MEMBER_PARTS = (
    ".bak",
    "_archive",
    "PORTAL_PACK",
    ".omc",
    ".claude",
    "paper_rie-",
)

# RiE-adapted: do NOT reject valid body/bib content (DOI paths like 10.1016/j.ress,
# the word "internal", or retained comment provenance). Absolute home paths and
# unresolved TODO/FIXME markers remain hard fails.
FORBIDDEN_TEXT = re.compile(
    r"/home/|/Users/|"
    r"(?:^|[^A-Za-z])(?:TODO(?:-USER)?|FIXME|TBD|placeholder)(?:$|[^A-Za-z])",
    re.IGNORECASE,
)

PROVENANCE_LINE = re.compile(r"^%\s*(source|figure)\s*:", re.IGNORECASE)
HEADER_STRIP_MARKERS = (
    "Internal provenance comments are retained only",
    "removed automatically by build_submission_package.py",
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def strip_internal_provenance(tex: str) -> str:
    """Drop working-tree-only provenance comments before external packaging."""
    out: list[str] = []
    for line in tex.splitlines(keepends=True):
        stripped = line.lstrip("%").strip()
        if any(marker in stripped for marker in HEADER_STRIP_MARKERS):
            continue
        if PROVENANCE_LINE.match(line):
            continue
        out.append(line)
    # Collapse runs of blank comment-banner lines left by header stripping.
    text = "".join(out)
    text = re.sub(
        r"(?m)^% =+\n(?:% =+\n)+",
        "% =====================================================================\n",
        text,
        count=1,
    )
    return text


def write_readme(path: Path) -> None:
    path.write_text(
        "Inspect RiE submission source "
        f"(frozen {BUILD_DATE.isoformat()})\n"
        "Contents: paper_rie.tex + paper_rie.bbl + refs.bib + figures/*.pdf\n\n"
        "Build command:\n"
        "  latexmk -pdf -interaction=nonstopmode -halt-on-error paper_rie.tex\n\n"
        "SHA256SUMS covers every payload member except SHA256SUMS itself.\n",
        encoding="utf-8",
    )


def zip_info(name: str) -> zipfile.ZipInfo:
    info = zipfile.ZipInfo(name, STAMP)
    info.compress_type = zipfile.ZIP_DEFLATED
    info.create_system = 3
    info.external_attr = 0o100644 << 16
    return info


def verify_compiles(stage: Path) -> int:
    """Compile the staged source in a scratch copy; return the page count."""
    with tempfile.TemporaryDirectory(prefix="rie-verify-") as scratch:
        work = Path(scratch) / "pkg"
        shutil.copytree(stage, work)
        proc = subprocess.run(
            ["latexmk", "-pdf", "-interaction=nonstopmode", "-halt-on-error", "paper_rie.tex"],
            cwd=work,
            capture_output=True,
            text=True,
        )
        pdf = work / "paper_rie.pdf"
        if proc.returncode != 0 or not pdf.is_file():
            tail = "\n".join(proc.stdout.splitlines()[-40:])
            raise SystemExit(f"Packaged source failed to compile:\n{tail}")
        info = subprocess.run(
            ["pdfinfo", str(pdf)], capture_output=True, text=True, check=True
        )
        pages = next(
            (
                int(line.split(":", 1)[1].strip())
                for line in info.stdout.splitlines()
                if line.lower().startswith("pages")
            ),
            0,
        )
        log = (work / "paper_rie.log").read_text(encoding="utf-8", errors="replace")
        undefined = [
            line for line in log.splitlines() if "undefined" in line.lower() and "Warning" in line
        ]
        if undefined:
            raise SystemExit(
                "Packaged source compiled with undefined references:\n"
                + "\n".join(undefined[:10])
            )
        print(f"verified: packaged source compiles standalone, {pages} pages, no undefined refs")
        return pages


def main() -> None:
    missing = [str(path) for path in SOURCES.values() if not path.is_file()]
    if missing:
        raise SystemExit("Missing package inputs:\n" + "\n".join(missing))

    raw_tex = SOURCES["paper_rie.tex"].read_text(encoding="utf-8")
    packaged_tex = strip_internal_provenance(raw_tex)
    referenced = set(re.findall(r"\\includegraphics(?:\[[^]]*\])?\{([^}]+\.pdf)\}", packaged_tex))
    packaged_figures = {f"figures/{name}" for name in FIGURES}
    # includegraphics paths may be figures/foo.pdf
    if referenced != packaged_figures:
        raise SystemExit(
            f"Figure allowlist mismatch: referenced={sorted(referenced)}, "
            f"packaged={sorted(packaged_figures)}"
        )

    zip_path = HERE / f"{STEM}.zip"
    sidecar = HERE / f"{STEM}.zip.sha256"

    with tempfile.TemporaryDirectory(prefix=f"{STEM}-") as tmp:
        stage = Path(tmp)
        for member, source in SOURCES.items():
            target = stage / member
            target.parent.mkdir(parents=True, exist_ok=True)
            if member == "paper_rie.tex":
                target.write_text(packaged_tex, encoding="utf-8")
            else:
                shutil.copyfile(source, target)
        write_readme(stage / "README.txt")

        payload = sorted([*SOURCES, "README.txt"])
        for member in payload:
            if any(part.lower() in member.lower() for part in FORBIDDEN_MEMBER_PARTS):
                raise SystemExit(f"Forbidden package member: {member}")
            path = stage / member
            if path.suffix.lower() in {".tex", ".bib", ".bbl", ".txt"}:
                match = FORBIDDEN_TEXT.search(path.read_text(encoding="utf-8", errors="replace"))
                if match:
                    raise SystemExit(f"Forbidden text {match.group()!r} in {member}")

        verify_compiles(stage)

        sums = stage / "SHA256SUMS"
        sums.write_text(
            "".join(f"{sha256(stage / member)}  {member}\n" for member in payload),
            encoding="utf-8",
        )
        members = sorted([*payload, "SHA256SUMS"])
        with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
            for member in members:
                archive.writestr(zip_info(member), (stage / member).read_bytes())

    with zipfile.ZipFile(zip_path) as archive:
        if archive.testzip() is not None:
            raise SystemExit("ZIP CRC verification failed")
        names = archive.namelist()
        expected = sorted([*SOURCES, "README.txt", "SHA256SUMS"])
        if names != expected:
            raise SystemExit(f"Unexpected ZIP members: {names}")

    digest = sha256(zip_path)
    sidecar.write_text(f"{digest}  {zip_path.name}\n", encoding="utf-8")
    subprocess.run(["sha256sum", "-c", sidecar.name], cwd=HERE, check=True)
    print(f"built {zip_path.name} ({zip_path.stat().st_size} bytes)")
    print(f"sha256 {digest}")


if __name__ == "__main__":
    main()
