#!/usr/bin/env Rscript
# Normalize xdet (cross-detector transfer) data for TikZ rendering.
# Outputs: xdet_panel_a.csv (certification bars), xdet_panel_b.csv (violation matrix),
#          xdet_panel_c.csv (score-scale support), xdet_panel_d.csv (cell shifts)

library(jsonlite)

script_arg <- grep("^--file=", commandArgs(), value = TRUE)
script_path <- if (length(script_arg)) sub("^--file=", "", script_arg[[1]]) else "xdet.R"
script_dir <- normalizePath(dirname(script_path), mustWork = TRUE)
SRC <- normalizePath(file.path(script_dir, "../../../cross_detector_transfer_2026-08-01/results.json"), mustWork = TRUE)
OUT_DIR <- script_dir

# Read JSON and replace Infinity/-Infinity with null (R can't parse Infinity in JSON).
raw_json <- paste(readLines(SRC, warn = FALSE), collapse = "\n")
raw_json <- gsub(":\\s*-?Infinity", ": null", raw_json, perl = TRUE)
d <- fromJSON(raw_json, simplifyVector = FALSE)

bd <- d$summary$by_benchmark_direction
overall <- d$summary$overall

BENCH <- c("mvtec", "visa", "mpdd")
BLAB <- list(mvtec = "MVTec AD", visa = "VisA", mpdd = "MPDD")
# Direction order matches the frozen summary convention (PC->DM first, then
# DM->PC) so panel-a bar order and x labels are stable and reproducible.
DIRS <- c("patchcore->dinomaly", "dinomaly->patchcore")
DLAB <- list(
  "dinomaly->patchcore" = "DM to PC",
  "patchcore->dinomaly" = "PC to DM"
)

# Panel a: certification bars
panel_a_rows <- list()
x_pos <- 0
for (b in BENCH) {
  for (dr in DIRS) {
    key <- paste0(b, "|", dr)
    entry <- bd[[key]]
    panel_a_rows[[length(panel_a_rows) + 1]] <- data.frame(
      benchmark = b,
      bench_label = BLAB[[b]],
      direction = dr,
      dir_label = DLAB[[dr]],
      x_pos = x_pos,
      cert_matched = entry$cert_rate_tier1_matched_diagonal * 100,
      cert_transfer = entry$cert_rate_tier1_transfer * 100,
      stringsAsFactors = FALSE
    )
    x_pos <- x_pos + 1
  }
}

# Add pooled non-vacuous
panel_a_rows[[length(panel_a_rows) + 1]] <- data.frame(
  benchmark = "pooled",
  bench_label = "Pooled",
  direction = "non-vacuous",
  dir_label = "pool",
  x_pos = x_pos + 0.75,
  cert_matched = overall$cert_rate_non_vacuous_matched_diagonal * 100,
  cert_transfer = overall$cert_rate_non_vacuous_transfer * 100,
  stringsAsFactors = FALSE
)

df_a <- do.call(rbind, panel_a_rows)
write.csv(df_a, file.path(OUT_DIR, "xdet_panel_a.csv"), row.names = FALSE, quote = FALSE)

# Panel b: violation matrix
panel_b_rows <- list()
for (b in BENCH) {
  for (dr in DIRS) {
    key <- paste0(b, "|", dr)
    entry <- bd[[key]]
    panel_b_rows[[length(panel_b_rows) + 1]] <- data.frame(
      benchmark = b,
      bench_label = BLAB[[b]],
      direction = dr,
      dir_label = DLAB[[dr]],
      n_cells = entry$n_cells,
      escaped_violations = entry$n_violation_escaped,
      fr_violations = entry$n_violation_false_reject,
      escaped_frac = entry$n_violation_escaped / entry$n_cells,
      fr_frac = entry$n_violation_false_reject / entry$n_cells,
      stringsAsFactors = FALSE
    )
  }
}

df_b <- do.call(rbind, panel_b_rows)
write.csv(df_b, file.path(OUT_DIR, "xdet_panel_b.csv"), row.names = FALSE, quote = FALSE)

# Panel c: score-scale support diagnostics
ssd <- d$score_scale_diagnostic
DETS <- c("patchcore", "dinomaly")
panel_c_rows <- list()
for (b in BENCH) {
  overlap <- ssd[[b]]$support_overlap$overlap_fraction_of_union
  for (det in DETS) {
    entry <- ssd[[b]][[det]]
    panel_c_rows[[length(panel_c_rows) + 1]] <- data.frame(
      bench = b,
      detector = det,
      min = entry$min,
      max = entry$max,
      p05 = entry$p05,
      p95 = entry$p95,
      median = entry$median,
      overlap = overlap,
      stringsAsFactors = FALSE
    )
  }
}
df_c <- do.call(rbind, panel_c_rows)
write.csv(df_c, file.path(OUT_DIR, "xdet_panel_c.csv"), row.names = FALSE, quote = FALSE)

# Panel d: per-cell transfer shifts relative to matched diagonal
panel_d_rows <- lapply(d$cells, function(cell) {
  delta <- cell$delta_vs_matched_diagonal
  data.frame(
    direction = cell$direction,
    escaped_pp = delta$escaped_pp,
    false_reject_pp = delta$false_reject_pp,
    stringsAsFactors = FALSE
  )
})
df_d <- do.call(rbind, panel_d_rows)
write.csv(df_d, file.path(OUT_DIR, "xdet_panel_d.csv"), row.names = FALSE, quote = FALSE)

# Emit explicit TikZ cell rectangles + count labels for the violation matrix
# (proven pattern: no runtime \pgfplotstablegetelem iteration, which bound the
# wrong row and rendered a constant value in every cell). \input in panel b.
# Compact y packing (pair gap < group gap) so cells read as a dense matrix;
# every cell gets a pale base + border so zero-count cells stay visible.
TEX_DIR <- normalizePath(file.path(OUT_DIR, "../out"), mustWork = FALSE)
dir.create(TEX_DIR, recursive = TRUE, showWarnings = FALSE)
fmt <- function(x) format(x, digits = 12, scientific = FALSE, trim = TRUE)
# y centers bottom→top: MVTec pair, VisA pair, MPDD pair (matches df_b order).
# Pair spacing ≈ 2*half + 0.04 (nearly flush); group gap ≈ 0.18.
y_centers <- c(0.00, 0.76, 1.68, 2.44, 3.36, 4.12)
half <- 0.36
panel_b_tikz <- character(0)
nb <- nrow(df_b)
stopifnot(nb == length(y_centers))
for (i in seq_len(nb)) {
  y <- y_centers[[i]]
  escpct <- min(100, df_b$escaped_frac[[i]] * 100)
  frpct <- min(100, df_b$fr_frac[[i]] * 100)
  esccount <- df_b$escaped_violations[[i]]
  frcount <- df_b$fr_violations[[i]]
  # Pale base keeps zero cells visible; orange overlay encodes intensity.
  cell <- function(x0, x1, pct, count) {
    c(
      sprintf("\\fill[black!5] (axis cs:%s,%s) rectangle (axis cs:%s,%s);",
              fmt(x0), fmt(y - half), fmt(x1), fmt(y + half)),
      sprintf("\\fill[orange!%s!white] (axis cs:%s,%s) rectangle (axis cs:%s,%s);",
              fmt(pct), fmt(x0), fmt(y - half), fmt(x1), fmt(y + half)),
      sprintf("\\draw[black!25, line width=0.35pt] (axis cs:%s,%s) rectangle (axis cs:%s,%s);",
              fmt(x0), fmt(y - half), fmt(x1), fmt(y + half)),
      sprintf("\\node[font=\\axislabelfont, text=black] at (axis cs:%s,%s) {%d};",
              fmt((x0 + x1) / 2), fmt(y), as.integer(count))
    )
  }
  panel_b_tikz <- c(panel_b_tikz,
                    cell(0.08, 0.92, escpct, esccount),
                    cell(1.08, 1.92, frpct, frcount))
}
# Group separators between benchmarks (midway between pairs).
panel_b_tikz <- c(panel_b_tikz,
  sprintf("\\draw[gray!40, line width=0.45pt] (axis cs:0.05,%s) -- (axis cs:1.95,%s);",
          fmt(1.32), fmt(1.32)),
  sprintf("\\draw[gray!40, line width=0.45pt] (axis cs:0.05,%s) -- (axis cs:1.95,%s);",
          fmt(3.18), fmt(3.18)))
# Tick positions for fig-xdet.tex (must stay in sync with y_centers).
writeLines(c(
  "% generated by R/xdet.R — y tick centers for panel b",
  sprintf("\\def\\xdetBYticks{%s}", paste(fmt(y_centers), collapse = ",")),
  sprintf("\\def\\xdetBYmax{%s}", fmt(max(y_centers) + half + 0.06)),
  sprintf("\\def\\xdetBYmin{%s}", fmt(min(y_centers) - half - 0.06)),
  sprintf("\\def\\xdetBGroupA{%s}", fmt(mean(y_centers[1:2]))),
  sprintf("\\def\\xdetBGroupB{%s}", fmt(mean(y_centers[3:4]))),
  sprintf("\\def\\xdetBGroupC{%s}", fmt(mean(y_centers[5:6])))
), file.path(TEX_DIR, "xdet-panel-b-meta.tex"), useBytes = TRUE)
writeLines(panel_b_tikz, file.path(TEX_DIR, "xdet-panel-b.tex"), useBytes = TRUE)

# Explicit TikZ for panel c (whisker min-max, thick p05-p95, median marker).
det_xoff <- list(patchcore = -0.14, dinomaly = 0.14)
det_col <- list(patchcore = "cPatchcore", dinomaly = "cDinomaly")
panel_c_tikz <- character(0)
for (b_i in seq_along(BENCH)) {
  b <- BENCH[[b_i]]
  bx <- b_i - 1
  overlap <- ssd[[b]]$support_overlap$overlap_fraction_of_union
  # Overlap labels sit just under the top spine (axis ymax=1.10 in fig-xdet.tex).
  panel_c_tikz <- c(panel_c_tikz,
    sprintf("\\node[anchor=south, font=\\tickfont, text=black] at (axis cs:%s,1.015) {ovlp %d\\%%};",
            fmt(bx), as.integer(round(overlap * 100))))
  for (det in DETS) {
    entry <- ssd[[b]][[det]]
    x <- bx + det_xoff[[det]]
    col <- det_col[[det]]
    panel_c_tikz <- c(panel_c_tikz,
      sprintf("\\draw[%s, line width=0.45pt] (axis cs:%s,%s) -- (axis cs:%s,%s);",
              col, fmt(x), fmt(entry$min), fmt(x), fmt(entry$max)),
      sprintf("\\draw[%s, line width=0.45pt] (axis cs:%s,%s) -- (axis cs:%s,%s);",
              col, fmt(x - 0.045), fmt(entry$min), fmt(x + 0.045), fmt(entry$min)),
      sprintf("\\draw[%s, line width=0.45pt] (axis cs:%s,%s) -- (axis cs:%s,%s);",
              col, fmt(x - 0.045), fmt(entry$max), fmt(x + 0.045), fmt(entry$max)),
      sprintf("\\draw[%s, line width=2.2pt, line cap=round] (axis cs:%s,%s) -- (axis cs:%s,%s);",
              col, fmt(x), fmt(entry$p05), fmt(x), fmt(entry$p95)))
    if (det == "patchcore") {
      panel_c_tikz <- c(panel_c_tikz,
        sprintf("\\node[circle, fill=%s, draw=white, line width=0.25pt, inner sep=1.55pt] at (axis cs:%s,%s) {};",
                col, fmt(x), fmt(entry$median)))
    } else {
      panel_c_tikz <- c(panel_c_tikz,
        sprintf("\\node[rectangle, fill=%s, draw=white, line width=0.25pt, inner sep=1.45pt] at (axis cs:%s,%s) {};",
                col, fmt(x), fmt(entry$median)))
    }
  }
}
writeLines(panel_c_tikz, file.path(TEX_DIR, "xdet-panel-c.tex"), useBytes = TRUE)

# Explicit TikZ coordinates for panel d, grouped by transfer direction.
# L-shape is structural (one arm per direction); use small marks + partial
# opacity so axis crowding remains honest but readable — no jitter/fake spread.
coords_for <- function(direction) {
  sub <- df_d[df_d$direction == direction, , drop = FALSE]
  paste(sprintf("(%s,%s)", fmt(sub$escaped_pp), fmt(sub$false_reject_pp)), collapse = "\n")
}
panel_d_tikz <- c(
  paste0(
    "\\addplot+[only marks, mark=*, mark size=0.72pt, ",
    "draw=cDinomaly, fill=cDinomaly, fill opacity=0.38, draw opacity=0.55] coordinates {"
  ),
  coords_for("patchcore->dinomaly"),
  "};",
  "\\addlegendentry{PC to DM}",
  # Hollow+fill square (not square*) — square* pulls MSAM7 and fails the LM font gate.
  paste0(
    "\\addplot+[only marks, mark=square, mark size=0.65pt, ",
    "draw=cPatchcore, fill=cPatchcore, fill opacity=0.38, draw opacity=0.55] coordinates {"
  ),
  coords_for("dinomaly->patchcore"),
  "};",
  "\\addlegendentry{DM to PC}"
)
writeLines(panel_d_tikz, file.path(TEX_DIR, "xdet-panel-d.tex"), useBytes = TRUE)

cat(sprintf("wrote xdet_panel_a.csv: %d rows\n", nrow(df_a)))
cat(sprintf("wrote xdet_panel_b.csv: %d rows\n", nrow(df_b)))
cat(sprintf("wrote xdet_panel_c.csv: %d rows\n", nrow(df_c)))
cat(sprintf("wrote xdet_panel_d.csv: %d rows\n", nrow(df_d)))
