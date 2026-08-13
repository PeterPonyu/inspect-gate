#!/usr/bin/env python3
"""Render inspect-gate web figures from committed frozen tables.

Writes SVG/PNG under site/figures-web/. Never writes manuscript PDFs.
"""

from __future__ import annotations

import csv
import json
import shutil
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager, patches
from matplotlib.lines import Line2D

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "manuscripts" / "figures-src"
OUT = ROOT / "site" / "figures-web"
FONT_DIR = Path(__file__).resolve().parent / "fonts"

INK = "#1C1917"
PAPER = "#F4F0E8"
PASS = "#009E73"
DEFER = "#E69F00"
REJECT = "#8B5E3C"
NAIVE = "#D55E00"
CERT = "#3D8B7A"
PC = "#0072B2"
DM = "#D55E00"
REFUSE = "#8A8680"
KS = "#C47B16"
CARD = "#FFFDF8"

SAMPLE_MAP = {
    0: "inspect-sample-mpdd-good-pass.png",
    1: "inspect-sample-mpdd-good-defer.png",
    2: "inspect-sample-mpdd-good-reject.png",
    3: "inspect-sample-mpdd-def-pass.png",
    4: "inspect-sample-mpdd-def-pass-gt.png",
    5: "inspect-sample-mpdd-def-defer.png",
    6: "inspect-sample-mpdd-def-defer-gt.png",
    7: "inspect-sample-mpdd-def-reject.png",
    8: "inspect-sample-mpdd-def-reject-gt.png",
    9: "inspect-sample-visa-good-pass.png",
    10: "inspect-sample-visa-good-defer.png",
    11: "inspect-sample-visa-good-reject.png",
    12: "inspect-sample-visa-def-pass.png",
    13: "inspect-sample-visa-def-pass-gt.png",
    14: "inspect-sample-visa-def-defer.png",
    15: "inspect-sample-visa-def-defer-gt.png",
    16: "inspect-sample-visa-def-reject.png",
    17: "inspect-sample-visa-def-reject-gt.png",
}


def setup_fonts() -> str:
    family = "DejaVu Sans"
    for ttf in sorted(FONT_DIR.glob("IBMPlexSans-*.ttf")):
        font_manager.fontManager.addfont(str(ttf))
        family = "IBM Plex Sans"
    for ttf in sorted(FONT_DIR.glob("IBMPlexMono-*.ttf")):
        font_manager.fontManager.addfont(str(ttf))
    plt.rcParams.update(
        {
            "font.family": family,
            "font.size": 11,
            "axes.titlesize": 12,
            "axes.labelsize": 12,
            "xtick.labelsize": 11,
            "ytick.labelsize": 11,
            "figure.facecolor": PAPER,
            "axes.facecolor": CARD,
            "axes.edgecolor": INK,
            "text.color": INK,
            "axes.labelcolor": INK,
            "xtick.color": INK,
            "ytick.color": INK,
            "svg.fonttype": "none",
            "axes.unicode_minus": False,
            "legend.frameon": False,
        }
    )
    return family


def read_csv(rel: str) -> list[dict[str, str]]:
    path = SRC / rel
    with path.open(newline="", encoding="utf-8") as handle:
        lines = [line for line in handle if line.strip() and not line.lstrip().startswith("#")]
    return list(csv.DictReader(lines))


def fnum(value: str | None) -> float | None:
    if value is None:
        return None
    text = str(value).strip()
    if text in {"", "NA", "n/a", "None"}:
        return None
    return float(text)


def save(fig: plt.Figure, stem: str) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    svg = OUT / f"{stem}.svg"
    png = OUT / f"{stem}.png"
    fig.savefig(svg, bbox_inches="tight", facecolor=PAPER)
    fig.savefig(png, dpi=160, bbox_inches="tight", facecolor=PAPER)
    plt.close(fig)


def panel_label(ax, letter: str) -> None:
    ax.text(
        0.0,
        1.02,
        f"({letter})",
        transform=ax.transAxes,
        ha="left",
        va="bottom",
        fontsize=11,
        fontweight="bold",
        color=INK,
    )


def write_overview() -> None:
    svg = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 420" role="img" aria-labelledby="ov-title ov-desc">
  <title id="ov-title">Three-way triage gate</title>
  <desc id="ov-desc">Anomaly score enters a floor check, then pass, defer, or reject, or audited-not-certified.</desc>
  <rect width="1200" height="420" fill="#f4f0e8"/>
  <g font-family="IBM Plex Sans, sans-serif" fill="#1c1917">
    <rect x="40" y="160" width="170" height="80" fill="#fffdf8" stroke="#1c1917"/>
    <text x="125" y="190" text-anchor="middle" font-size="14">anomaly score</text>
    <text x="125" y="212" text-anchor="middle" font-size="12">higher = more anomalous</text>
    <path d="M210 200 H270" stroke="#1c1917" stroke-width="1.5" marker-end="url(#arrow)"/>
    <rect x="270" y="150" width="200" height="100" fill="#fffdf8" stroke="#1c1917"/>
    <text x="370" y="185" text-anchor="middle" font-size="14">floor check</text>
    <text x="370" y="208" text-anchor="middle" font-size="12">αmin = 1/(ncal+1)</text>
    <path d="M470 200 H530" stroke="#1c1917" stroke-width="1.5" marker-end="url(#arrow)"/>
    <rect x="530" y="150" width="190" height="100" fill="#fffdf8" stroke="#1c1917"/>
    <text x="625" y="185" text-anchor="middle" font-size="15">(tlo , thi)</text>
    <text x="625" y="208" text-anchor="middle" font-size="12">split-conformal band</text>
    <path d="M720 200 H790" stroke="#1c1917" stroke-width="1.5" marker-end="url(#arrow)"/>
    <rect x="790" y="40" width="170" height="70" fill="#009e73" stroke="#1c1917"/>
    <text x="875" y="82" text-anchor="middle" font-size="14" fill="#fffdf8">AUTO-PASS</text>
    <rect x="790" y="155" width="170" height="70" fill="#e69f00" stroke="#1c1917"/>
    <text x="875" y="197" text-anchor="middle" font-size="14">DEFER</text>
    <rect x="790" y="270" width="170" height="70" fill="#8b5e3c" stroke="#1c1917"/>
    <text x="875" y="312" text-anchor="middle" font-size="14" fill="#fffdf8">AUTO-REJECT</text>
    <path d="M370 150 V70 H790" fill="none" stroke="#1c1917" stroke-width="1.4" stroke-dasharray="6 4" marker-end="url(#arrow)"/>
    <rect x="790" y="40" width="0" height="0"/>
    <rect x="980" y="40" width="180" height="70" fill="url(#hatch)" stroke="#1c1917"/>
    <text x="1070" y="70" text-anchor="middle" font-size="13">audited-not-</text>
    <text x="1070" y="90" text-anchor="middle" font-size="13">certified</text>
    <text x="370" y="58" text-anchor="middle" font-size="12">floor-control (dashed)</text>
    <text x="600" y="390" text-anchor="middle" font-size="13">If a floor is unmet, that auto-action is emptied (threshold ±∞).</text>
  </g>
  <defs>
    <marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="8" markerHeight="8" orient="auto-start-reverse">
      <path d="M 0 0 L 10 5 L 0 10 z" fill="#1c1917"/>
    </marker>
    <pattern id="hatch" width="8" height="8" patternUnits="userSpaceOnUse" patternTransform="rotate(-45)">
      <rect width="8" height="8" fill="#ece6d8"/>
      <line x1="0" y1="0" x2="0" y2="8" stroke="#8a8680" stroke-width="3"/>
    </pattern>
  </defs>
</svg>
"""
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "inspect-fig-overview-web.svg").write_text(svg, encoding="utf-8")


def plot_scoreanatomy() -> None:
    payload = json.loads((SRC / "data/frozen/scoreanatomy_points.json").read_text(encoding="utf-8"))
    fig, axes = plt.subplots(2, 2, figsize=(12.2, 8.2))
    letters = "abcd"
    for ax, cell, letter in zip(axes.ravel(), payload["cells"], letters):
        good = [float(v) for v in cell["eval_scores"]["good"]]
        defect = [float(v) for v in cell["eval_scores"]["defect"]]
        t_lo = cell["thresholds"].get("t_lo")
        t_hi = cell["thresholds"].get("t_hi")
        refused = t_lo is None and t_hi is None
        values = good + defect
        if t_lo is not None:
            values.append(float(t_lo))
        if t_hi is not None:
            values.append(float(t_hi))
        lo, hi = min(values), max(values)
        pad = max(0.02, (hi - lo) * 0.08)
        rng = (max(0.0, lo - pad), min(1.0, hi + pad))
        ax.hist(good, bins=18, range=rng, color=PASS, alpha=0.75, label="good")
        ax.hist(defect, bins=18, range=rng, color=REJECT, alpha=0.55, label="defect")
        if refused:
            ax.text(0.5, 0.82, "REFUSED (thresholds ±∞)", transform=ax.transAxes, ha="center", fontsize=11)
        else:
            if t_lo is not None:
                ax.axvline(float(t_lo), color=PASS, lw=1.6)
                ax.text(float(t_lo), ax.get_ylim()[1], " t_lo", color=PASS, va="top", fontsize=10)
            if t_hi is not None:
                ax.axvline(float(t_hi), color=REJECT, lw=1.6, linestyle="--")
                ax.text(float(t_hi), ax.get_ylim()[1], " t_hi", color=REJECT, va="top", fontsize=10)
        tag = "exploratory" if cell["benchmark"] != "MVTec AD" else "confirmatory"
        title = f"{cell['benchmark']} / {cell['category']} / {cell['backbone']} [{tag}]"
        ax.set_title(title, loc="left", fontsize=11)
        ax.set_xlabel("anomaly score (higher = more anomalous)")
        ax.set_ylabel("images")
        panel_label(ax, letter)
        if letter == "a":
            ax.legend(loc="upper left")
    fig.tight_layout()
    save(fig, "inspect-fig-scoreanatomy-web")


def plot_alphafrontier() -> None:
    rows = read_csv("R/alphafrontier_data.csv")
    benches = ["MVTec-AD", "VisA", "MPDD"]
    fig, axes = plt.subplots(2, 3, figsize=(12.4, 7.4), sharex=True)
    for col, bench in enumerate(benches):
        tag = "confirmatory" if bench == "MVTec-AD" else "exploratory"
        for row_i, (field, ylab) in enumerate(
            (("deferral_mean", "deferral"), ("certified_mean", "both-axis certified fraction"))
        ):
            ax = axes[row_i][col]
            for backbone, color, ls, marker in (
                ("patchcore", PC, "-", "o"),
                ("dinomaly", DM, "--", "s"),
            ):
                pts = [r for r in rows if r["benchmark"] == bench and r["backbone"] == backbone]
                xs = [fnum(r["alpha_miss"]) for r in pts]
                ys = [fnum(r[field]) for r in pts]
                ax.plot(xs, ys, color=color, ls=ls, marker=marker, label=backbone)
            ax.axvline(0.10, color=INK, lw=0.8, ls=":")
            ax.set_title(f"{bench} [{tag}]", loc="left", fontsize=11)
            ax.set_ylabel(ylab)
            if row_i == 1:
                ax.set_xlabel("α_miss")
            panel_label(ax, "abcdef"[row_i * 3 + col])
    handles = [
        Line2D([0], [0], color=PC, marker="o", label="PatchCore"),
        Line2D([0], [0], color=DM, marker="s", ls="--", label="Dinomaly"),
    ]
    fig.legend(handles=handles, loc="upper center", ncol=2, bbox_to_anchor=(0.5, 1.02))
    fig.tight_layout()
    save(fig, "inspect-fig-alphafrontier-web")


def plot_calfraction() -> None:
    rows = read_csv("R/calfraction_data.csv")
    benches = ["MVTec AD", "VisA", "MPDD"]
    fig, axes = plt.subplots(2, 3, figsize=(12.4, 7.4), sharex=True)
    for col, bench in enumerate(benches):
        tag = "confirmatory" if bench == "MVTec AD" else "exploratory"
        for row_i, (field, ylab) in enumerate((("def_mean", "deferral"), ("cert_mean", "G2-certified count"))):
            ax = axes[row_i][col]
            for backbone, color, ls, marker in (
                ("patchcore", PC, "-", "o"),
                ("dinomaly", DM, "--", "s"),
            ):
                pts = [r for r in rows if r["benchmark"] == bench and r["backbone"] == backbone]
                xs = [fnum(r["fraction"]) for r in pts]
                ys = [fnum(r[field]) for r in pts]
                ax.plot(xs, ys, color=color, ls=ls, marker=marker)
            if bench == "MPDD":
                ax.axvline(0.10, color=INK, lw=0.8, ls=":")
                if field == "def_mean":
                    ax.text(0.11, 0.92, "frac 0.10 → 1.0 deferral", transform=ax.transAxes, fontsize=9)
            ax.set_title(f"{bench} [{tag}]", loc="left", fontsize=11)
            ax.set_ylabel(ylab)
            if row_i == 1:
                ax.set_xlabel("calibration fraction")
            panel_label(ax, "abcdef"[row_i * 3 + col])
    fig.tight_layout()
    save(fig, "inspect-fig-calfraction-web")


def plot_calplanning() -> None:
    req = read_csv("R/calplanning_requirement.csv")
    fig, ax = plt.subplots(figsize=(11.2, 5.2))
    xs = [fnum(r["alpha"]) for r in req]
    ys = [fnum(r["min_n_cal"]) for r in req]
    ax.plot(xs, ys, color=INK, marker="o")
    ax.scatter([0.10], [9], s=60, color=PASS, zorder=3, label="α_miss=0.10 → 9 defectives")
    ax.scatter([0.05], [19], s=60, color=DEFER, zorder=3, label="α_fr=0.05 → 19 goods")
    ax.set_xlabel("α")
    ax.set_ylabel("required n_cal")
    ax.set_title("Planning curve  n_cal >= ceil(1/alpha) - 1", loc="left")
    ax.legend(loc="upper right")
    panel_label(ax, "a")
    fig.tight_layout()
    save(fig, "inspect-fig-calplanning-web")


def plot_crc() -> None:
    a = read_csv("R/crcbaseline_panel_a.csv")
    b = read_csv("R/crcbaseline_panel_b.csv")
    c = read_csv("R/crcbaseline_panel_c.csv")
    fig, axes = plt.subplots(3, 1, figsize=(11.6, 11.2))

    benches = ["MVTec AD", "VisA", "MPDD"]
    metrics = ["Escaped", "False-reject", "Deferral"]
    x = range(len(benches))
    width = 0.12
    ax = axes[0]
    for i, metric in enumerate(metrics):
        gate = []
        crc = []
        for bench in benches:
            row = next(r for r in a if r["benchmark"] == bench and r["metric"] == metric)
            gate.append(fnum(row["gate_val"]))
            crc.append(fnum(row["crc_val"]))
        offset = (i - 1) * 0.28
        ax.bar([xi + offset - 0.06 for xi in x], gate, width=width, color=CERT, label=f"gate {metric}" if i == 0 else None)
        ax.bar([xi + offset + 0.06 for xi in x], crc, width=width, color=NAIVE, label=f"CRC {metric}" if i == 0 else None)
    ax.set_xticks(list(x), benches)
    ax.set_ylabel("percent")
    ax.set_title("Pooled rates at the same escaped-defect target", loc="left")
    ax.legend(["gate", "CRC"], loc="upper right")
    panel_label(ax, "a")

    ax = axes[1]
    for backbone, color, ls in (("patchcore", PC, "-"), ("dinomaly", DM, "--")):
        pts = [r for r in b if r["backbone"] == backbone]
        xs = [fnum(r["coverage"]) for r in pts]
        ys = [fnum(r["selective_risk"]) for r in pts]
        ax.plot(xs, ys, color=color, ls=ls, marker="o", label=backbone)
    ax.set_xlabel("coverage")
    ax.set_ylabel("selective risk (%)")
    ax.set_title("VisA risk–coverage companion [exploratory]", loc="left")
    ax.legend()
    panel_label(ax, "b")

    ax = axes[2]
    labels = [f"{r['benchmark']}\n{r['backbone']}" for r in c]
    ax.bar([i - 0.18 for i in range(len(c))], [fnum(r["gate_frac"]) for r in c], width=0.36, color=CERT, label="gate both-axis %")
    ax.bar([i + 0.18 for i in range(len(c))], [fnum(r["crc_frac"]) for r in c], width=0.36, color=NAIVE, label="CRC (no G2)")
    ax.set_xticks(range(len(c)), labels, fontsize=9)
    ax.set_ylabel("both-axis certified fraction (%)")
    ax.set_title("CRC cannot issue G2", loc="left")
    ax.legend()
    panel_label(ax, "c")
    fig.tight_layout()
    save(fig, "inspect-fig-crcbaseline-web")


def plot_binding(name: str, target: float, ylabel: str, stem: str) -> None:
    rows = read_csv(f"R/{name}")
    fig, ax = plt.subplots(figsize=(11.8, 4.8))
    labels = [r["cell"] for r in rows]
    y = range(len(rows))
    ax.barh([yi + 0.16 for yi in y], [fnum(r["b1"]) for r in rows], height=0.32, color=NAIVE, label="naive best-F1")
    ax.barh([yi - 0.16 for yi in y], [fnum(r["gate"]) for r in rows], height=0.32, color=CERT, label="certified gate")
    ax.axvline(target, color=INK, lw=1.2)
    ax.set_yticks(list(y), labels)
    ax.set_xlabel(ylabel)
    ax.legend(loc="lower right")
    ax.invert_yaxis()
    fig.tight_layout()
    save(fig, stem)


def plot_deferral() -> None:
    rows = read_csv("R/deferral.csv")
    fig, ax = plt.subplots(figsize=(11.6, 9.2))
    y = range(len(rows))
    labels = [f"{r['category']} ({r['bench']})" for r in rows]
    ax.barh([yi + 0.16 for yi in y], [fnum(r["patchcore"]) * 100 for r in rows], height=0.32, color=PC, label="PatchCore")
    ax.barh([yi - 0.16 for yi in y], [fnum(r["dinomaly"]) * 100 for r in rows], height=0.32, color=DM, label="Dinomaly")
    ax.axvline(80, color=INK, ls=":", lw=1, label="K2 0.80")
    ax.set_yticks(list(y), labels, fontsize=8)
    ax.set_xlabel("deferral (%)")
    ax.legend(loc="lower right")
    ax.invert_yaxis()
    fig.tight_layout()
    save(fig, "inspect-fig-deferral-web")


def plot_opcost() -> None:
    rows = read_csv("R/opcost_grid.csv")
    four = read_csv("R/opcost_fourmethod.csv")
    fig, axes = plt.subplots(2, 2, figsize=(11.6, 8.2))
    axes = axes.ravel()
    benches = ["MVTec-AD", "VisA", "MPDD"]
    scenarios = ["low_volume_precision", "mid_volume_general", "high_volume_commodity"]
    x = range(len(benches))
    for i, scen in enumerate(scenarios):
        ax = axes[i]
        subset = [next(r for r in rows if r["benchmark"] == b and r["scenario"] == scen) for b in benches]
        ax.bar([xi - 0.18 for xi in x], [fnum(r["gate_cost"]) for r in subset], width=0.36, color=CERT, label="gate")
        ax.bar([xi + 0.18 for xi in x], [fnum(r["crc_cost"]) for r in subset], width=0.36, color=NAIVE, label="CRC")
        ax.set_xticks(list(x), benches)
        hours = {"low_volume_precision": "100/h", "mid_volume_general": "600/h", "high_volume_commodity": "3000/h"}[scen]
        ax.set_title(f"{scen.replace('_', ' ')} (assumed {hours})", loc="left")
        if i == 0:
            ax.legend()
        panel_label(ax, "abc"[i])
    ax = axes[3]
    methods = ["gate", "crc", "b1_no_defer", "all_human"]
    labels = [r["benchmark"] for r in four if r["method"] == "gate"]
    for j, method in enumerate(methods):
        ys = []
        for bench in labels:
            row = next(r for r in four if r["benchmark"] == bench and r["method"] == method)
            ys.append(fnum(row["cost"]) or 0.0)
        ax.bar([xi + (j - 1.5) * 0.18 for xi in range(len(labels))], ys, width=0.18, label=method.replace("_", " "))
    ax.set_xticks(range(len(labels)), labels)
    ax.set_title("four-method mid-volume [illustrative]", loc="left")
    ax.legend(fontsize=8)
    panel_label(ax, "d")
    fig.tight_layout()
    save(fig, "inspect-fig-opcost-web")


def plot_jointmon() -> None:
    a = read_csv("R/jointmon_panel_a.csv")
    b = read_csv("R/jointmon_panel_b.csv")
    c = read_csv("R/jointmon_panel_c.csv")
    d = read_csv("R/jointmon_panel_d.csv")
    fig, axes = plt.subplots(2, 2, figsize=(11.6, 8.2))

    ax = axes[0][0]
    for row in a:
        catch = fnum(row["catch"])
        fa = fnum(row["false_alarm"])
        if catch is None:
            continue
        color = PC if "patchcore" in row["arm"] else DM
        marker = "o" if row["gate"] == "g1" else "s"
        ax.scatter(0.0 if fa is None else fa, catch, color=color, marker=marker)
    ax.plot([0, 1], [0, 1], color=INK, lw=0.7, ls=":")
    ax.set_xlabel("false alarm")
    ax.set_ylabel("catch")
    ax.set_title("catch ≈ false alarm", loc="left")
    panel_label(ax, "a")

    ax = axes[0][1]
    for row in b:
        catch = fnum(row["catch"])
        fa = fnum(row["false_alarm"])
        if catch is None or fa is None:
            continue
        color = PC if row["detector"] == "patchcore" else DM
        marker = "o" if row["gate"] == "g1" else "s"
        ax.scatter(fa, catch, color=color, marker=marker)
    ax.plot([0, 1], [0, 1], color=INK, lw=0.7, ls=":")
    ax.set_xlabel("false alarm")
    ax.set_ylabel("catch")
    ax.set_title("operating points [exploratory]", loc="left")
    panel_label(ax, "b")

    ax = axes[1][0]
    for row in c:
        xd = fnum(row["z_defect"])
        yg = fnum(row["z_good"])
        if xd is None or yg is None:
            continue
        exceeded = str(row["g1_exceed"]).lower() == "true"
        ax.scatter(xd, yg, s=8, color=NAIVE if exceeded else CERT, alpha=0.35)
    ax.set_xlabel("z_defect")
    ax.set_ylabel("z_good")
    ax.set_title("joint location cloud", loc="left")
    panel_label(ax, "c")

    ax = axes[1][1]
    xs = list(range(len(d)))
    ax.plot(xs, [fnum(r["catch_rate"]) for r in d], color=CERT, marker="o", label="catch")
    ax.plot(xs, [fnum(r["fa_rate"]) for r in d], color=NAIVE, marker="s", label="false alarm")
    ax.set_xticks(xs, [r["x_label"] for r in d], rotation=45, ha="right", fontsize=8)
    ax.set_ylabel("rate")
    ax.set_title("catch tracks false alarm", loc="left")
    ax.legend()
    panel_label(ax, "d")
    fig.tight_layout()
    save(fig, "inspect-fig-jointmon-web")


def plot_xdet() -> None:
    a = read_csv("R/xdet_panel_a.csv")
    b = read_csv("R/xdet_panel_b.csv")
    fig, axes = plt.subplots(1, 2, figsize=(12.0, 5.0))
    ax = axes[0]
    labels = [r["dir_label"] for r in a]
    x = range(len(a))
    ax.bar([xi - 0.18 for xi in x], [fnum(r["cert_matched"]) for r in a], width=0.36, color=CERT, label="matched")
    ax.bar([xi + 0.18 for xi in x], [fnum(r["cert_transfer"]) for r in a], width=0.36, color=NAIVE, label="transfer")
    ax.set_xticks(list(x), labels, rotation=25, ha="right", fontsize=9)
    ax.set_ylabel("certificate support (%)")
    ax.set_title("support overlap", loc="left")
    ax.legend()
    panel_label(ax, "a")
    ax = axes[1]
    labels = [f"{r['bench_label']}\n{r['dir_label']}" for r in b]
    x = range(len(b))
    ax.bar([xi - 0.18 for xi in x], [fnum(r["escaped_violations"]) for r in b], width=0.36, color=NAIVE, label="G1 violations")
    ax.bar([xi + 0.18 for xi in x], [fnum(r["fr_violations"]) for r in b], width=0.36, color=DEFER, label="G2 violations")
    ax.set_xticks(list(x), labels, fontsize=8)
    ax.set_ylabel("cells")
    ax.set_title("160/165 G1 violations PC→DM", loc="left")
    ax.legend()
    panel_label(ax, "b")
    fig.tight_layout()
    save(fig, "inspect-fig-xdet-web")


def plot_g2delta() -> None:
    mv = read_csv("R/g2delta_mvtec.csv")
    mp = read_csv("R/g2delta_mpdd.csv")
    fig, axes = plt.subplots(1, 2, figsize=(12.2, 5.6))
    for ax, rows, title, letter in (
        (axes[0], mv, "MVTec 4/15 → 13/15", "a"),
        (axes[1], mp, "MPDD 0/6 → 4/6 [exploratory]", "b"),
    ):
        colors_primary = []
        colors_promoted = []
        for r in rows:
            colors_primary.append(CERT if r["primary_status"] == "certified" else REFUSE)
            if r["promoted_status"] == "certified":
                colors_promoted.append(CERT)
            elif r["promoted_status"] == "refused-KS":
                colors_promoted.append(KS)
            else:
                colors_promoted.append(REFUSE)
        y = range(len(rows))
        ax.barh([yi + 0.16 for yi in y], [1] * len(rows), height=0.3, color=colors_primary, label="primary")
        ax.barh([yi - 0.16 for yi in y], [1] * len(rows), height=0.3, color=colors_promoted, label="promoted")
        ax.set_yticks(list(y), [r["category"] for r in rows])
        ax.set_xlim(0, 1.05)
        ax.set_xticks([])
        ax.set_title(title + " · PatchCore-only", loc="left", fontsize=11)
        ax.invert_yaxis()
        panel_label(ax, letter)
        if letter == "a":
            ax.legend(
                handles=[
                    patches.Patch(color=CERT, label="certified"),
                    patches.Patch(color=REFUSE, label="floor refuse"),
                    patches.Patch(color=KS, label="KS refuse"),
                ],
                loc="lower right",
            )
    fig.tight_layout()
    save(fig, "inspect-fig-g2delta-web")


def copy_samples() -> None:
    assets = SRC / "canonical_samples_assets"
    OUT.mkdir(parents=True, exist_ok=True)
    for index, name in SAMPLE_MAP.items():
        src = assets / f"extracted-{index:03d}.png"
        shutil.copyfile(src, OUT / name)


def main() -> None:
    setup_fonts()
    write_overview()
    plot_scoreanatomy()
    plot_alphafrontier()
    plot_calfraction()
    plot_calplanning()
    plot_crc()
    plot_binding("binding_escaped.csv", 0.10, "escaped-defect rate", "inspect-fig-binding-escaped-web")
    plot_binding("binding_fr.csv", 0.05, "false-reject rate", "inspect-fig-binding-fr-web")
    plot_deferral()
    plot_opcost()
    plot_jointmon()
    plot_xdet()
    plot_g2delta()
    copy_samples()
    print("wrote", sorted(p.name for p in OUT.iterdir()))


if __name__ == "__main__":
    main()
