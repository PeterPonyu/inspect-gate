"""Torch-free unit tests for mpdd_results_2026-07-13/scripts/mpdd_floor_table.py.

Verifies the certifiability-floor PREDICTION against the exact boundaries of
the frozen primary protocol (alpha_miss=0.10 -> G1 needs n_cal_defect>=9;
alpha_fr=0.05 -> G2 needs n_cal_good>=19), including the banker's-rounding
50/50 split edges, by driving the REAL splits+gate code path (which is what
makes the prediction bit-for-bit equal to the box)."""
import importlib.util
from pathlib import Path

_FLOOR = (Path(__file__).resolve().parents[1]
          / "mpdd_results_2026-07-13" / "scripts" / "mpdd_floor_table.py")
_spec = importlib.util.spec_from_file_location("mpdd_floor_table", _FLOOR)
mft = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(mft)


# n_test -> n_cal via int(round(0.5*n)) (banker's rounding); certified iff
# n_cal_good>=19 (G2) / n_cal_defect>=9 (G1).
COUNTS = {
    "cat_both":    {"n_test_good": 40, "n_test_defect": 20},  # cal 20 / 10 -> G1 T, G2 T
    "cat_edge_yes": {"n_test_good": 38, "n_test_defect": 18},  # cal 19 /  9 -> G1 T, G2 T
    "cat_edge_no":  {"n_test_good": 37, "n_test_defect": 17},  # cal 18 /  8 -> G1 F, G2 F
    "cat_g1only":  {"n_test_good": 10, "n_test_defect": 20},  # cal  5 / 10 -> G1 T, G2 F
    "cat_neither": {"n_test_good": 4,  "n_test_defect": 2},   # cal  2 /  1 -> G1 F, G2 F
}


def test_split_rounding_and_certified_flags():
    r = mft.predict_floors(COUNTS)
    pc = r["per_category"]

    assert pc["cat_both"]["n_cal_good"] == 20 and pc["cat_both"]["n_cal_defect"] == 10
    assert pc["cat_both"]["g1_certified"] and pc["cat_both"]["g2_certified"]

    assert pc["cat_edge_yes"]["n_cal_good"] == 19 and pc["cat_edge_yes"]["n_cal_defect"] == 9
    assert pc["cat_edge_yes"]["g1_certified"] and pc["cat_edge_yes"]["g2_certified"]

    # 37/17 -> banker's rounds 18.5->18 and 8.5->8, both just below the floors
    assert pc["cat_edge_no"]["n_cal_good"] == 18 and pc["cat_edge_no"]["n_cal_defect"] == 8
    assert not pc["cat_edge_no"]["g1_certified"] and not pc["cat_edge_no"]["g2_certified"]

    assert pc["cat_g1only"]["g1_certified"] and not pc["cat_g1only"]["g2_certified"]
    assert not pc["cat_neither"]["g1_certified"] and not pc["cat_neither"]["g2_certified"]


def test_alpha_min_values():
    r = mft.predict_floors(COUNTS)
    pc = r["per_category"]
    # alpha_min = 1/(n_cal+1)
    assert abs(pc["cat_both"]["alpha_min_g2"] - 1 / 21) < 1e-12
    assert abs(pc["cat_both"]["alpha_min_g1"] - 1 / 11) < 1e-12
    assert abs(pc["cat_edge_yes"]["alpha_min_g1"] - 1 / 10) < 1e-12  # == 0.10 exactly, certified


def test_certifiable_counts():
    r = mft.predict_floors(COUNTS)
    assert r["n_g2_certifiable"] == 2   # cat_both, cat_edge_yes
    assert r["n_g1_certifiable"] == 3   # cat_both, cat_edge_yes, cat_g1only
    assert r["n_categories"] == 5


def test_markdown_renders_headline():
    r = mft.predict_floors(COUNTS)
    md = mft.to_markdown(r)
    assert "Predicted G2-certifiable: 2/5" in md
    assert "| cat_both |" in md
