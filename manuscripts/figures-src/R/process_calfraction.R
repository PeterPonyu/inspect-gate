#!/usr/bin/env Rscript
# Process calfraction sweep data for fig-calfraction.
# Reads (preferred): calfraction_sweep_2026-07-19/results.json
# Fallback SSOT:     data/frozen/calfraction_data.csv (outside clean-data wipe)
# Writes: R/calfraction_data.csv + out/calfraction-*-{cert,def}.tex
#
# cert_mean is already a category COUNT (mean of
# certification_counts_per_repeat$both). Do NOT multiply by n_cats again.
#
# When sweep JSON is absent, FRACS and panel inputs come from the frozen CSV;
# git-restore of R/calfraction_data.csv is seed-only for data/frozen/, not an
# acceptance path.

library(jsonlite)

options(warn = 1)

script_arg <- grep("^--file=", commandArgs(), value = TRUE)
script_path <- if (length(script_arg)) sub("^--file=", "", script_arg[[1]]) else "process_calfraction.R"
script_dir <- normalizePath(dirname(script_path), mustWork = TRUE)
setwd(script_dir)

json_path <- normalizePath(
  file.path(script_dir, "../../../calfraction_sweep_2026-07-19/results.json"),
  mustWork = FALSE
)
frozen_csv <- normalizePath(
  file.path(script_dir, "../data/frozen/calfraction_data.csv"),
  mustWork = FALSE
)
local_csv <- file.path(script_dir, "calfraction_data.csv")

SPECS <- list(
  list(label = "MVTec AD", key = "mvtecad", json = "mvtec", ncats = 15L),
  list(label = "VisA",     key = "visa",    json = "visa",  ncats = 12L),
  list(label = "MPDD",     key = "mpdd",    json = "mpdd",  ncats = 6L)
)
BACKBONES <- c("patchcore", "dinomaly")

load_from_json <- function(json_path) {
  d <- fromJSON(json_path, simplifyVector = FALSE, simplifyDataFrame = FALSE)

  # Frozen sweep order (left→right on the figure): large budget → small budget.
  FRACS <- as.numeric(unlist(d$meta$fracs))
  if (!length(FRACS)) stop("FATAL: meta$fracs missing from calfraction sweep JSON")

  rows <- list()
  for (spec in SPECS) {
    for (bb in BACKBONES) {
      cell <- d[[spec$json]][[bb]]
      for (f in FRACS) {
        fkey <- sprintf("frac%g", f)
        frac_data <- cell[[fkey]]
        if (is.null(frac_data) || is.null(frac_data$per_seed)) next

        seeds <- frac_data$per_seed
        both_vals <- numeric()
        dfr_vals <- numeric()
        for (seed_name in names(seeds)) {
          seed_data <- seeds[[seed_name]]
          if (!is.null(seed_data$certification_counts_per_repeat$both)) {
            both_raw <- seed_data$certification_counts_per_repeat$both
            both_vec <- if (is.list(both_raw)) unlist(both_raw) else as.numeric(both_raw)
            both_vals <- c(both_vals, mean(both_vec))
          }
          if (!is.null(seed_data$overall_mean_deferral)) {
            dfr_vals <- c(dfr_vals, as.numeric(seed_data$overall_mean_deferral))
          }
        }
        if (!length(both_vals) || !length(dfr_vals)) next

        rows[[length(rows) + 1L]] <- data.frame(
          benchmark = spec$label,
          backbone = bb,
          fraction = f,
          cert_mean = mean(both_vals),
          cert_min = min(both_vals),
          cert_max = max(both_vals),
          def_mean = mean(dfr_vals),
          def_min = min(dfr_vals),
          def_max = max(dfr_vals),
          stringsAsFactors = FALSE
        )
      }
    }
  }

  df <- do.call(rbind, rows)
  write.csv(df, local_csv, row.names = FALSE)
  cat(sprintf("Wrote %d rows to R/calfraction_data.csv (from sweep JSON)\n", nrow(df)))
  list(df = df, FRACS = FRACS)
}

load_from_frozen <- function(frozen_csv) {
  if (!file.exists(frozen_csv)) {
    stop(paste0(
      "FATAL: calfraction sweep JSON absent and frozen SSOT missing: ",
      "manuscripts/figures-src/data/frozen/calfraction_data.csv"
    ))
  }
  if (!file.copy(frozen_csv, local_csv, overwrite = TRUE)) {
    stop("FATAL: failed to copy frozen calfraction_data.csv into R/")
  }
  df <- read.csv(local_csv, stringsAsFactors = FALSE)
  required <- c(
    "benchmark", "backbone", "fraction",
    "cert_mean", "cert_min", "cert_max",
    "def_mean", "def_min", "def_max"
  )
  missing <- setdiff(required, names(df))
  if (length(missing)) {
    stop(sprintf("FATAL: frozen calfraction CSV missing columns: %s", paste(missing, collapse = ", ")))
  }
  if (!nrow(df)) stop("FATAL: frozen calfraction CSV is empty")
  # Match JSON meta order: large budget → small budget.
  FRACS <- sort(unique(as.numeric(df$fraction)), decreasing = TRUE)
  if (!length(FRACS)) stop("FATAL: frozen calfraction CSV has no fraction values")
  cat(sprintf(
    "Loaded %d rows from frozen SSOT data/frozen/calfraction_data.csv (JSON absent)\n",
    nrow(df)
  ))
  list(df = df, FRACS = FRACS)
}

if (file.exists(json_path)) {
  loaded <- load_from_json(json_path)
} else {
  loaded <- load_from_frozen(frozen_csv)
}

df <- loaded$df
FRACS <- loaded$FRACS

TEX_DIR <- normalizePath(file.path(getwd(), "../out"), mustWork = FALSE)
dir.create(TEX_DIR, recursive = TRUE, showWarnings = FALSE)

frac_to_x <- function(f) {
  idx <- which(abs(FRACS - f) < 1e-9)
  if (!length(idx)) stop(sprintf("FATAL: fraction %s not in FRACS", f))
  as.integer(idx[[1]] - 1L)
}
fmt4 <- function(x) format(round(x, 4), nsmall = 4, scientific = FALSE, trim = TRUE)

for (spec in SPECS) {
  bdf <- df[df$benchmark == spec$label, ]

  cert_lines <- c("% generated by process_calfraction.R")
  def_lines <- c("% generated by process_calfraction.R")
  for (bb in BACKBONES) {
    bb_data <- bdf[bdf$backbone == bb, ]
    bb_data <- bb_data[order(vapply(bb_data$fraction, frac_to_x, integer(1))), ]
    if (!nrow(bb_data)) next

    xs <- vapply(bb_data$fraction, frac_to_x, integer(1))
    # Counts already — never rescale by n_cats.
    style <- if (identical(bb, "patchcore")) {
      "cPatchcore, mark=o, line width=1.2pt, mark size=3.5pt"
    } else {
      "cDinomaly, mark=square, line width=1.2pt, mark size=3.5pt"
    }
    cert_coords <- paste(sprintf("(%d,%s)", xs, fmt4(bb_data$cert_mean)), collapse = " ")
    def_coords <- paste(sprintf("(%d,%s)", xs, fmt4(bb_data$def_mean)), collapse = " ")
    cert_lines <- c(
      cert_lines,
      sprintf("\\addplot[%s] coordinates {", style),
      paste0("  ", cert_coords),
      "};"
    )
    def_lines <- c(
      def_lines,
      sprintf("\\addplot[%s] coordinates {", style),
      paste0("  ", def_coords),
      "};"
    )
  }

  writeLines(cert_lines, file.path(TEX_DIR, sprintf("calfraction-%s-cert.tex", spec$key)), useBytes = TRUE)
  writeLines(def_lines, file.path(TEX_DIR, sprintf("calfraction-%s-def.tex", spec$key)), useBytes = TRUE)
  cat(sprintf("wrote calfraction fragments for %s (x = %s)\n",
              spec$label, paste(FRACS, collapse = ",")))
}
