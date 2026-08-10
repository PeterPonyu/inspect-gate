#!/usr/bin/env Rscript
# Normalize validity data from frozen JSON to CSV digests for TikZ rendering.
# Outputs: validity_points.csv (per-repeat points), validity_means.csv (per-benchmark means)

library(jsonlite)

script_arg <- grep("^--file=", commandArgs(), value = TRUE)
script_path <- if (length(script_arg)) sub("^--file=", "", script_arg[[1]]) else "validity.R"
script_dir <- normalizePath(dirname(script_path), mustWork = TRUE)
SRC <- normalizePath(file.path(script_dir, "../data/frozen/validity_points.json"), mustWork = TRUE)
OUT_DIR <- script_dir

pts <- fromJSON(SRC, simplifyVector = FALSE)

BENCH_ORDER <- list(
  list(key = "mvtec", label = "MVTec AD"),
  list(key = "visa", label = "VisA"),
  list(key = "mpdd", label = "MPDD")
)

BB_STYLE <- list(
  list(bb = "patchcore", marker = "o"),
  list(bb = "dinomaly", marker = "s")
)

# Collect points for panels a and b
points_escaped <- list()
points_fr <- list()
means_escaped <- list()
means_fr <- list()

for (i in seq_along(BENCH_ORDER)) {
  bench_key <- BENCH_ORDER[[i]]$key
  bench_label <- BENCH_ORDER[[i]]$label
  x_pos <- i - 1

  for (j in seq_along(BB_STYLE)) {
    bb <- BB_STYLE[[j]]$bb
    marker <- BB_STYLE[[j]]$marker

    vals_esc <- unlist(pts[[bench_key]][[bb]][["escaped"]])
    vals_fr <- unlist(pts[[bench_key]][[bb]][["fr"]])

    if (length(vals_esc) > 0) {
      for (val in vals_esc) {
        points_escaped[[length(points_escaped) + 1]] <- data.frame(
          bench = bench_label,
          backbone = bb,
          x_pos = x_pos,
          j_offset = j - 1,
          value = val,
          marker = marker,
          stringsAsFactors = FALSE
        )
      }
      means_escaped[[length(means_escaped) + 1]] <- data.frame(
        bench = bench_label,
        backbone = bb,
        x_pos = x_pos,
        j_offset = j - 1,
        mean_val = mean(vals_esc),
        marker = marker,
        stringsAsFactors = FALSE
      )
    }

    if (length(vals_fr) > 0) {
      for (val in vals_fr) {
        points_fr[[length(points_fr) + 1]] <- data.frame(
          bench = bench_label,
          backbone = bb,
          x_pos = x_pos,
          j_offset = j - 1,
          value = val,
          marker = marker,
          stringsAsFactors = FALSE
        )
      }
      means_fr[[length(means_fr) + 1]] <- data.frame(
        bench = bench_label,
        backbone = bb,
        x_pos = x_pos,
        j_offset = j - 1,
        mean_val = mean(vals_fr),
        marker = marker,
        stringsAsFactors = FALSE
      )
    }
  }
}

df_pts_esc <- do.call(rbind, points_escaped)
df_pts_fr <- do.call(rbind, points_fr)
df_means_esc <- do.call(rbind, means_escaped)
df_means_fr <- do.call(rbind, means_fr)

write.csv(df_pts_esc, file.path(OUT_DIR, "validity_escaped_points.csv"), row.names = FALSE, quote = FALSE)
write.csv(df_pts_fr, file.path(OUT_DIR, "validity_fr_points.csv"), row.names = FALSE, quote = FALSE)
write.csv(df_means_esc, file.path(OUT_DIR, "validity_escaped_means.csv"), row.names = FALSE, quote = FALSE)
write.csv(df_means_fr, file.path(OUT_DIR, "validity_fr_means.csv"), row.names = FALSE, quote = FALSE)

# Per-backbone splits so the TikZ figure can colour PatchCore vs Dinomaly
# separately without fragile pgfplots row-filtering (j_offset 0=patchcore, 1=dinomaly).
for (bb in c("patchcore", "dinomaly")) {
  write.csv(df_pts_esc[df_pts_esc$backbone == bb, ],
            file.path(OUT_DIR, sprintf("validity_escaped_points_%s.csv", bb)),
            row.names = FALSE, quote = FALSE)
  write.csv(df_pts_fr[df_pts_fr$backbone == bb, ],
            file.path(OUT_DIR, sprintf("validity_fr_points_%s.csv", bb)),
            row.names = FALSE, quote = FALSE)
  write.csv(df_means_esc[df_means_esc$backbone == bb, ],
            file.path(OUT_DIR, sprintf("validity_escaped_means_%s.csv", bb)),
            row.names = FALSE, quote = FALSE)
  write.csv(df_means_fr[df_means_fr$backbone == bb, ],
            file.path(OUT_DIR, sprintf("validity_fr_means_%s.csv", bb)),
            row.names = FALSE, quote = FALSE)
}

cat(sprintf("wrote validity CSVs: %d esc points, %d fr points\n",
            nrow(df_pts_esc), nrow(df_pts_fr)))

# ── Panels c (matched-diagonal cloud) and d (transfer-violation cloud) ────────
# These read the cross-detector transfer record. That JSON contains bare
# Infinity tokens (and boxed booleans), so we sanitise with readLines+gsub
# before fromJSON -- the same pure-R technique used in xdet.R. This keeps the
# whole inspect figure pipeline in R with no Python dependency.
XFER_SRC <- normalizePath(file.path(script_dir, "../../../cross_detector_transfer_2026-08-01/results.json"), mustWork = TRUE)
TEX_DIR <- normalizePath(file.path(OUT_DIR, "../out"), mustWork = FALSE)
dir.create(TEX_DIR, recursive = TRUE, showWarnings = FALSE)

xfer_raw <- paste(readLines(XFER_SRC, warn = FALSE), collapse = "\n")
xfer_raw <- gsub(":\\s*-?Infinity", ": null", xfer_raw, perl = TRUE)
xfer <- fromJSON(xfer_raw, simplifyVector = FALSE)
xcells <- xfer$cells

BL <- c(mvtec = "MVTec AD", visa = "VisA", mpdd = "MPDD")

# Panel c: matched-diagonal cloud -- read the NESTED matched_diagonal rates
# (NOT the cell's top-level transfer rates). matched_diagonal is a nested object.
md_rows <- list()
for (cell in xcells) {
  md <- cell$matched_diagonal
  if (!is.list(md)) next
  md_rows[[length(md_rows) + 1]] <- data.frame(
    benchmark = unname(BL[[cell$benchmark]]),
    escaped_pct = round(md$realized_escaped_defect_rate * 100, 4),
    fr_pct = round(md$realized_false_reject_rate * 100, 4),
    stringsAsFactors = FALSE
  )
}
matched <- do.call(rbind, md_rows)
write.csv(matched, file.path(OUT_DIR, "validity_matched_cloud.csv"),
          row.names = FALSE, quote = FALSE)

# Panel d: transfer-violation cloud (uses the cell's transfer-arm rates, since a
# violation is defined by the transfer arm exceeding a target).
viol_rows <- list()
for (cell in xcells) {
  if (isTRUE(cell$violation_escaped)) {
    viol_rows[[length(viol_rows) + 1]] <- data.frame(
      kind = "escaped", x = round(cell$escaped_excess_pp, 4),
      y = round(cell$realized_false_reject_rate * 100, 4), stringsAsFactors = FALSE)
  }
  if (isTRUE(cell$violation_false_reject)) {
    viol_rows[[length(viol_rows) + 1]] <- data.frame(
      kind = "fr", x = round(cell$realized_escaped_defect_rate * 100, 4),
      y = round(cell$false_reject_excess_pp, 4), stringsAsFactors = FALSE)
  }
}
viol <- do.call(rbind, viol_rows)
write.csv(viol, file.path(OUT_DIR, "validity_violation_cloud.csv"),
          row.names = FALSE, quote = FALSE)

# --- TikZ fragment: panel c (matched-diagonal per-benchmark scatter) ---------
# Correct nested rates give a genuine low-escaped/low-FR distribution, drawn as
# a per-benchmark scatter with small deterministic jitter to separate ties.
BENCH_MARK <- list(
  "MVTec AD" = list(col = "cMVTecAD", mk = "*"),
  "VisA"     = list(col = "cVisA",    mk = "square*"),
  "MPDD"     = list(col = "cMPDD",    mk = "triangle*")
)
set.seed(7)
lines_c <- c("% generated by validity.R -- panel c (matched-diagonal scatter)")
for (bl in c("MVTec AD", "VisA", "MPDD")) {
  sub <- matched[matched$benchmark == bl, ]
  sty <- BENCH_MARK[[bl]]
  jx <- runif(nrow(sub), -0.18, 0.18)
  jy <- runif(nrow(sub), -0.12, 0.12)
  coords <- paste(sprintf("(%.3f,%.3f)", sub$escaped_pct + jx, sub$fr_pct + jy),
                  collapse = " ")
  lines_c <- c(lines_c,
    sprintf("\\addplot[%s, only marks, mark=%s, mark size=1.5pt, opacity=0.55] coordinates {%s};",
            sty$col, sty$mk, coords),
    sprintf("\\addlegendentry{%s}", bl))
}
writeLines(lines_c, file.path(TEX_DIR, "validity-panel-c.tex"), useBytes = TRUE)

# --- TikZ fragment: panel d (violation count bubbles) -----------------------
# Cap mark size so axis-edge clusters (x≈0 / y≈0) stay inside the padded frame.
# Annotate only major aggregates (n>=5); tiny satellites stay as marks only
# (avoids clipped "157" and stray side labels 1/2). Count labels are plain
# black (no fill box), parked just above/ beside the mark for readability.
bubble_size <- function(n) round(2.0 + 2.4 * sqrt(n / 160.0), 2)  # n=160 → ~4.4pt
viol$xr <- round(viol$x); viol$yr <- round(viol$y)
n_esc <- sum(viol$kind == "escaped")
n_fr  <- sum(viol$kind == "fr")
lines_d <- c("% generated by validity.R -- panel d (violation count bubbles)")
# legend dummies (off-canvas); TikZ places the legend horizontally above the title
lines_d <- c(lines_d,
  sprintf("\\addplot[cReject, only marks, mark=*, mark size=2.4pt, opacity=0.85] coordinates {(-100,-100)};"),
  sprintf("\\addlegendentry{escaped (n=%d)}", n_esc),
  sprintf("\\addplot[cControl, only marks, mark=*, mark size=2.4pt, opacity=0.85] coordinates {(-100,-100)};"),
  sprintf("\\addlegendentry{FR (n=%d)}", n_fr))
for (kc in list(c("escaped", "cReject"), c("fr", "cControl"))) {
  kind <- kc[1]; col <- kc[2]
  sub <- viol[viol$kind == kind, ]
  if (!nrow(sub)) next
  agg <- aggregate(list(n = rep(1, nrow(sub))), by = list(x = sub$xr, y = sub$yr), FUN = sum)
  agg <- agg[order(-agg$n), ]
  for (i in seq_len(nrow(agg))) {
    lines_d <- c(lines_d, sprintf(
      "\\addplot[%s, only marks, mark=*, mark size=%.2fpt, opacity=0.65, forget plot] coordinates {(%.1f,%.1f)};",
      col, bubble_size(agg$n[i]), agg$x[i], agg$y[i]))
  }
  for (i in seq_len(nrow(agg))) {
    if (agg$n[i] < 5) next
    # Axis-edge bubbles: park the badge inward so it is not clipped.
    yshift <- if (agg$y[i] <= 2) 9 else if (agg$y[i] >= 100) -9 else 8
    xshift <- if (agg$x[i] <= 2) 8 else if (agg$x[i] >= 95) -8 else 0
    # House style: count badges plain black, no fill box; \tickfont (7pt).
    lines_d <- c(lines_d, sprintf(
      paste0("\\node[font=\\tickfont, anchor=center, text=black, inner sep=0.5pt]",
             " at (axis cs:%.1f,%.1f)",
             " [xshift=%dpt, yshift=%dpt] {%d};"),
      agg$x[i], agg$y[i], xshift, yshift, agg$n[i]))
  }
}
writeLines(lines_d, file.path(TEX_DIR, "validity-panel-d.tex"), useBytes = TRUE)

cat(sprintf("wrote validity panel c/d: %d matched-diagonal cells, %d violations\n",
            nrow(matched), nrow(viol)))
