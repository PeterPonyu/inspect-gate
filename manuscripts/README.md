# Inspect paper manuscripts (RiE / AEI)

Standalone git root for the Inspect gate manuscripts and figure SSOT.

## Layout

| Path | Role |
|------|------|
| `rie/` | Reliability Engineering manuscript (`paper_rie.tex`) |
| `aei/` | AEI mirror manuscript + figures |
| `figures-src/` | Pure R + TikZ figure SSOT (`Makefile`, `R/`, `tikz/`, `out/`) |
| `refs.bib` | Shared bibliography |
| `jim/` | JIM venue variant (if present) |

Desktop shortcut: `papers/inspect-rie` → `rie/`, `papers/inspect-aei` → `aei/`, `papers/inspect-canonical` → this directory.

## Build figures

```bash
cd figures-src
make r-data   # regenerates out/*.tex from R (needs frozen JSON under ../..)
make all
make sync-rie sync-aei
```

Frozen analysis JSON lives next to this tree under `tools/inspect-gate/` (e.g. `calplanning_2026-07-29/`, `opcost_analysis_2026-07-16/`) and is **not** part of this paper repo.

## Build paper

```bash
cd rie
latexmk -pdf paper_rie.tex
```
