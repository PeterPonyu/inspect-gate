#!/usr/bin/env python3
"""Build TWO MVTec-style VisA layouts from the raw VisA_20220922 extraction
using the OFFICIAL spot-diff split_csv/1cls.csv -- symlinks only.

Both consumers PIL-open files (content, not extension), but they GLOB
differently (discovered 2026-07-12, first VisA run):
  ROOT_A (anomalib/PatchCore): images symlinked AS ``<stem>.png`` (anomalib +
    Dinomaly both glob ``*.png``; the raw files are .JPG); masks at
    ``ground_truth/bad/<stem>_mask.png`` (anomalib MVTec convention -- the
    original ``<stem>.png`` naming crashed make_mvtec_ad_dataset with a
    pandas length-mismatch).
  ROOT_B (Dinomaly): same png-named image symlinks; masks at
    ``ground_truth/bad/<stem>/000.png`` (dataset.py globs
    ``gt_path/<defect>/*/000.png`` -- one DIRECTORY per anomalous image).
Refuses loudly on any count mismatch."""
import csv, sys
from pathlib import Path

RAW, CSV, OUT_A, OUT_B = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3]), Path(sys.argv[4])
counts, n_masks = {}, {}
with open(CSV) as f:
    for row in csv.DictReader(f):
        cat, split, label = row["object"], row["split"], row["label"]
        img = RAW / row["image"]
        if not img.exists():
            print(f"REFUSE: csv image missing: {img}", file=sys.stderr); sys.exit(1)
        sub = "good" if label == "normal" else "bad"
        stem = img.stem
        for root in (OUT_A, OUT_B):
            d = root / cat / ("train" if split == "train" else "test") / sub
            d.mkdir(parents=True, exist_ok=True)
            dst = d / f"{stem}.png"          # png-NAME, content stays JPEG (PIL reads content)
            if not dst.exists():
                dst.symlink_to(img.resolve())
        counts[(cat, split, sub)] = counts.get((cat, split, sub), 0) + 1
        if row.get("mask"):
            m = RAW / row["mask"]
            if not m.exists():
                print(f"REFUSE: csv mask missing: {m}", file=sys.stderr); sys.exit(1)
            ga = OUT_A / cat / "ground_truth" / "bad" / f"{stem}_mask.png"
            ga.parent.mkdir(parents=True, exist_ok=True)
            if not ga.exists(): ga.symlink_to(m.resolve())
            # dinomaly_visa_uni's MVTecDataset (dataset.py ~line 83) globs gt as
            # FLAT files ground_truth/<defect>/*.png (the per-image-dir
            # convention belongs to a DIFFERENT class in the same file --
            # 2026-07-12 all-5-seeds pairing-assert failure).
            gb = OUT_B / cat / "ground_truth" / "bad" / f"{stem}.png"
            gb.parent.mkdir(parents=True, exist_ok=True)
            if not gb.exists(): gb.symlink_to(m.resolve())
            n_masks[cat] = n_masks.get(cat, 0) + 1
cats = sorted({c for c, _, _ in counts})
total = sum(counts.values())
print(f"visa_prep: {len(cats)} categories, {total} images linked (x2 roots)")
assert len(cats) == 12, f"REFUSE: expected 12 categories, got {len(cats)}"
assert total == 10821, f"REFUSE: expected 10821 images, got {total}"
for c in cats:
    tr = counts.get((c, "train", "good"), 0); tg = counts.get((c, "test", "good"), 0)
    tb = counts.get((c, "test", "bad"), 0);   mk = n_masks.get(c, 0)
    print(f"  {c}: train/good={tr} test/good={tg} test/bad={tb} masks={mk}")
    assert tr > 0 and tg > 0 and tb > 0, f"REFUSE: empty split cell in {c}"
    assert mk == tb, f"REFUSE: {c} mask count {mk} != test/bad {tb} (anomalib pairs them 1:1)"
print("VISA_PREP_OK")
