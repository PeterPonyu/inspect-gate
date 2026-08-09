#!/usr/bin/env Rscript
# Normalize deferral data from gate_calibration JSONs to CSV digest for TikZ rendering.
# Output: deferral.csv (33 categories x 3 benchmarks, patchcore + dinomaly values)

library(jsonlite)

script_arg <- grep("^--file=", commandArgs(), value = TRUE)
script_path <- if (length(script_arg)) sub("^--file=", "", script_arg[[1]]) else "deferral.R"
script_dir <- normalizePath(dirname(script_path), mustWork = TRUE)
IG <- normalizePath(file.path(script_dir, "../../.."), mustWork = TRUE)
OUT_DIR <- script_dir

SPECS <- list(
  list(
    bench = "MVTec-AD",
    dpath = file.path(IG, "analysis_2026-07-10/gate_calibration"),
    cats = c("bottle", "cable", "capsule", "carpet", "grid", "hazelnut", "leather",
             "metal_nut", "pill", "screw", "tile", "toothbrush", "transistor",
             "wood", "zipper")
  ),
  list(
    bench = "VisA",
    dpath = file.path(IG, "visa_results_2026-07-12/gate_calibration"),
    cats = c("candle", "capsules", "cashew", "chewinggum", "fryum", "macaroni1",
             "macaroni2", "pcb1", "pcb2", "pcb3", "pcb4", "pipe_fryum")
  ),
  list(
    bench = "MPDD",
    dpath = file.path(IG, "mpdd_results_2026-07-13/gate_calibration"),
    cats = c("bracket_black", "bracket_brown", "bracket_white", "connector",
             "metal_plate", "tubes")
  )
)

rows <- list()
SEEDS <- 0:4
for (spec in SPECS) {
  # Load all five seeds per backbone; seed 0 is the plotted point, seeds 0-4
  # give the min-max band (matches the Fig. 14 caption).
  pc_seeds <- lapply(SEEDS, function(s)
    fromJSON(file.path(spec$dpath, sprintf("v1_patchcore_seed%d.json", s)))$median_deferral_by_category)
  dm_seeds <- lapply(SEEDS, function(s)
    fromJSON(file.path(spec$dpath, sprintf("v1_dinomaly_seed%d.json", s)))$median_deferral_by_category)

  seed_stats <- function(seed_list, cat) {
    vals <- unlist(lapply(seed_list, function(sd) if (is.null(sd[[cat]])) NA else sd[[cat]]))
    vals <- vals[!is.na(vals)]
    if (length(vals) == 0) return(c(seed0 = NA, lo = NA, hi = NA))
    s0 <- seed_list[[1]][[cat]]
    c(seed0 = ifelse(is.null(s0), NA, s0), lo = min(vals), hi = max(vals))
  }

  for (cat in spec$cats) {
    pc <- seed_stats(pc_seeds, cat)
    dm <- seed_stats(dm_seeds, cat)
    rows[[length(rows) + 1]] <- data.frame(
      category = cat,
      bench = spec$bench,
      patchcore = unname(pc["seed0"]),
      patchcore_lo = unname(pc["lo"]),
      patchcore_hi = unname(pc["hi"]),
      dinomaly = unname(dm["seed0"]),
      dinomaly_lo = unname(dm["lo"]),
      dinomaly_hi = unname(dm["hi"]),
      stringsAsFactors = FALSE
    )
  }
}

df <- do.call(rbind, rows)
df$row_idx <- seq(nrow(df), 1)

write.csv(df, file.path(OUT_DIR, "deferral.csv"), row.names = FALSE, quote = FALSE)
cat(sprintf("wrote deferral.csv: %d rows (seed0 + seed0-4 min/max)\n", nrow(df)))
