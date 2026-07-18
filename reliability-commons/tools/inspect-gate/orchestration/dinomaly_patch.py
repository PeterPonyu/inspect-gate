#!/usr/bin/env python3
"""Anchored, idempotent patcher for the official Dinomaly repo's
dinomaly_mvtec_uni.py (Apache-2.0, guojiajeremy/Dinomaly) -- Branch-A needs
three capabilities the upstream script lacks, added as surgical edits so the
official training/eval code stays the single source of truth:

  P1  seed via env      setup_seed(1) -> setup_seed(int(os.environ.get('DINOMALY_SEED','1')))
  P2  iters via env     total_iters = 10000 -> int(os.environ.get('DINOMALY_ITERS','10000'))
  P3  final checkpoint save + per-image score dump (the upstream final
      torch.save is commented out and nothing dumps per-image scores; the
      dump EXACTLY mirrors evaluation_batch's scoring path -- cal_anomaly_maps
      -> resize 256 -> gaussian k5 s4 -> top-1%%-mean pooling (max_ratio=0.01)
      -- keyed by img_path, per category, the shape score_dinomaly.py
      --mode dump-ingest consumes).

Writes a unified diff next to the target (<target>.branchA.diff) for
provenance. Idempotent: re-running on a patched file is a no-op.
"""

from __future__ import annotations

import difflib
import sys
from pathlib import Path

DUMP_FN = '''
def dump_image_scores_branchA(model, item_list, test_data_list, device, out_dir, batch_size):
    """inspect-gate Branch-A addition (2026-07-10): per-image image-level
    score dump for score_dinomaly.py --mode dump-ingest. EXACTLY mirrors
    evaluation_batch's scoring (cal_anomaly_maps -> resize 256 -> gaussian
    kernel_size=5 sigma=4 -> top-1%-mean pooling, max_ratio=0.01)."""
    import json as _json
    from utils import cal_anomaly_maps as _cam, get_gaussian_kernel as _ggk
    model.eval()
    _gk = _ggk(kernel_size=5, sigma=4).to(device)
    for _item, _td in zip(item_list, test_data_list):
        _loader = torch.utils.data.DataLoader(_td, batch_size=batch_size, shuffle=False, num_workers=4)
        _scores = {}
        with torch.no_grad():
            for _img, _gt, _label, _img_path in _loader:
                _img = _img.to(device)
                _en, _de = model(_img)
                _amap, _ = _cam(_en, _de, _img.shape[-1])
                _amap = F.interpolate(_amap, size=256, mode='bilinear', align_corners=False)
                _amap = _gk(_amap).flatten(1)
                _sp = torch.sort(_amap, dim=1, descending=True)[0][:, :int(_amap.shape[1] * 0.01)].mean(dim=1)
                for _p, _s in zip(_img_path, _sp.detach().cpu().tolist()):
                    _scores[str(_p)] = float(_s)
        with open(os.path.join(out_dir, 'scores_{}.json'.format(_item)), 'w') as _f:
            _json.dump(_scores, _f)
        print('dump_image_scores_branchA: {} n={}'.format(_item, len(_scores)))


'''

FINAL_BLOCK_OLD = """    # torch.save(model.state_dict(), os.path.join(args.save_dir, args.save_name, 'model.pth'))

    return"""

FINAL_BLOCK_NEW = """    out_dir_branchA = os.path.join(args.save_dir, args.save_name)
    os.makedirs(out_dir_branchA, exist_ok=True)
    torch.save(model.state_dict(), os.path.join(out_dir_branchA, 'model.pth'))
    dump_image_scores_branchA(model, item_list, test_data_list, device, out_dir_branchA, batch_size)

    return"""


def main() -> int:
    target = Path(sys.argv[1] if len(sys.argv) > 1 else "/root/Dinomaly/dinomaly_mvtec_uni.py")
    src = target.read_text()
    orig = src

    # Each patch checks its own applied-state so a NEW patch (e.g. P4, added
    # after the first on-box application) still lands on an already-patched
    # file instead of no-opping behind a global guard.
    p1_new = "    setup_seed(int(os.environ.get('DINOMALY_SEED', '1')))"
    if p1_new not in src:
        p1_old = "    setup_seed(1)"
        if p1_old not in src:
            print("dinomaly_patch: P1 anchor missing", file=sys.stderr)
            return 1
        src = src.replace(p1_old, p1_new, 1)

    p2_new = "    total_iters = int(os.environ.get('DINOMALY_ITERS', '10000'))"
    if p2_new not in src:
        p2_old = "    total_iters = 10000"
        if p2_old not in src:
            print("dinomaly_patch: P2 anchor missing", file=sys.stderr)
            return 1
        src = src.replace(p2_old, p2_new, 1)

    if "dump_image_scores_branchA(model" not in src:
        if FINAL_BLOCK_OLD not in src:
            print("dinomaly_patch: P3 final-block anchor missing", file=sys.stderr)
            return 1
        src = src.replace(FINAL_BLOCK_OLD, FINAL_BLOCK_NEW, 1)

    if "def dump_image_scores_branchA" not in src:
        guard = "if __name__ == '__main__':"
        if guard not in src:
            print("dinomaly_patch: __main__ guard anchor missing", file=sys.stderr)
            return 1
        src = src.replace(guard, DUMP_FN + guard, 1)

    # P4 (2026-07-10, smoke incident): upstream hardcodes the authors' 2-GPU
    # machine ("cuda:1") -> "invalid device ordinal" on any single-GPU box.
    p4_new = "    device = os.environ.get('DINOMALY_DEVICE', 'cuda:0') if torch.cuda.is_available() else 'cpu'"
    if p4_new not in src:
        p4_old = "    device = 'cuda:1' if torch.cuda.is_available() else 'cpu'"
        if p4_old not in src:
            print("dinomaly_patch: P4 device anchor missing", file=sys.stderr)
            return 1
        src = src.replace(p4_old, p4_new, 1)

    # P5 (2026-07-11, seed-0 crash at iter-5000 eval): pandas 2.x removed
    # DataFrame.append; the 2021-era eval code (in utils) still calls it, and
    # pandas<2 is binary-incompatible with this env's numpy 2. Faithful
    # module-level shim, installed before any eval code runs (global on the
    # DataFrame class, so utils.py is covered too).
    p5_shim = (
        "\n# branchA P5: pandas>=2 removed DataFrame.append; restore a faithful shim\n"
        "import pandas as _branchA_pd\n"
        "if not hasattr(_branchA_pd.DataFrame, 'append'):\n"
        "    def _branchA_df_append(self, other, ignore_index=False, **kwargs):\n"
        "        if not isinstance(other, (_branchA_pd.DataFrame, _branchA_pd.Series)):\n"
        "            other = _branchA_pd.DataFrame([other])\n"
        "        elif isinstance(other, _branchA_pd.Series):\n"
        "            other = other.to_frame().T\n"
        "        return _branchA_pd.concat([self, other], ignore_index=ignore_index)\n"
        "    _branchA_pd.DataFrame.append = _branchA_df_append\n"
    )
    if "_branchA_df_append" not in src:
        p5_anchor = "import warnings\nimport copy"
        if p5_anchor not in src:
            print("dinomaly_patch: P5 import-block anchor missing", file=sys.stderr)
            return 1
        src = src.replace(p5_anchor, p5_anchor + "\n" + p5_shim, 1)

    if src == orig:
        print("dinomaly_patch: already fully patched (idempotent no-op)")
        return 0

    diff = "".join(difflib.unified_diff(
        orig.splitlines(keepends=True), src.splitlines(keepends=True),
        fromfile=str(target), tofile=str(target) + " (branchA)"))
    target.with_suffix(".py.branchA.diff").write_text(diff)
    target.write_text(src)
    print(f"dinomaly_patch: applied P1+P2+P3+dump fn; diff -> {target.with_suffix('.py.branchA.diff')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
