#!/usr/bin/env Rscript
# Render the frozen four-panel score-anatomy figure with R/Cairo.

suppressPackageStartupMessages(library(jsonlite))

script_arg <- grep("^--file=", commandArgs(), value = TRUE)
script_path <- if (length(script_arg)) sub("^--file=", "", script_arg[[1]]) else "scoreanatomy.R"
script_dir <- normalizePath(dirname(script_path), mustWork = TRUE)
inspect_gate <- normalizePath(file.path(script_dir, "../../.."), mustWork = TRUE)
input_path <- normalizePath(file.path(script_dir, "../data/frozen/scoreanatomy_points.json"), mustWork = FALSE)
output_path <- file.path(script_dir, "../fig-scoreanatomy.pdf")
source(file.path(script_dir, "_figconst.R"))  # INSPECT_FONT, ROUTE_* colours

if (!file.exists(input_path)) {
  stop(sprintf("FATAL: frozen score-anatomy input not found: %s", input_path))
}

frozen <- fromJSON(input_path, simplifyVector = FALSE)
if (length(frozen$cells) != 4L) {
  stop(sprintf("FATAL: expected four frozen score-anatomy cells, found %d", length(frozen$cells)))
}

pass_col <- ROUTE_PASS
defect_col <- ROUTE_REJECT
defer_col <- ROUTE_DEFER
font_family <- INSPECT_FONT

cell_status <- function(cell) {
  if (is.null(cell$thresholds$t_lo) && is.null(cell$thresholds$t_hi)) {
    return("floor refusal: all defer")
  }
  g1 <- if (isTRUE(cell$certification$g1)) "G1" else "no G1"
  g2 <- if (isTRUE(cell$certification$g2)) "G2" else "no G2"
  sprintf("%s + %s certified", g1, g2)
}

score_limits <- function(good, defect, lo, hi) {
  finite_thresholds <- c(lo, hi)
  finite_thresholds <- finite_thresholds[is.finite(finite_thresholds)]
  values <- c(good, defect, finite_thresholds)
  span <- diff(range(values))
  padding <- max(0.02, span * 0.08)
  c(max(0, min(values) - padding), min(1, max(values) + padding))
}

render_cell <- function(cell, side = c("left", "right")) {
  side <- match.arg(side)
  good <- as.numeric(unlist(cell$eval_scores$good))
  defect <- as.numeric(unlist(cell$eval_scores$defect))
  lo <- if (is.null(cell$thresholds$t_lo)) NA_real_ else as.numeric(cell$thresholds$t_lo)
  hi <- if (is.null(cell$thresholds$t_hi)) NA_real_ else as.numeric(cell$thresholds$t_hi)
  limits <- score_limits(good, defect, lo, hi)
  breaks <- seq(limits[[1]], limits[[2]], length.out = 25L)
  good_hist <- hist(good, breaks = breaks, plot = FALSE)
  defect_hist <- hist(defect, breaks = breaks, plot = FALSE)
  ymax <- max(c(good_hist$counts, defect_hist$counts, 1)) * 1.22

  # Left column (a,c): tighter right margin + titles pulled left so they do not
  # reach into the gutter where (b)/(d) panel letters sit. Right column (b,d):
  # wider left margin so those letters clear the a/c titles.
  # X-axis title is drawn once per column in a dedicated strip below the grid
  # (not via plot xlab), so descenders are never clipped by the panel cell.
  if (identical(side, "left")) {
    par(mar = c(1.90, 3.45, 3.05, 0.15))
    title_frac <- 0.04
    tag_adj <- 1.45
  } else {
    # Keep enough left margin for the "images" ylab after the narrow gutter.
    par(mar = c(1.90, 2.55, 3.05, 0.55))
    title_frac <- 0.18
    tag_adj <- 1.20
  }

  # Size ladder vs cairo_pdf(pointsize=12): tick 7 / body 8 / axis+title 9
  # (mirrors \tickfont / \figfont / \axislabelfont in inspect_style.tex).
  tick_cex <- FIG_TICK_PT / 12
  body_cex <- FIG_BODY_PT / 12
  axis_cex <- FIG_AXIS_PT / 12
  plot(NA, xlim = limits, ylim = c(0, ymax), xlab = "", ylab = "images",
       axes = FALSE, xaxs = "i", yaxs = "i", cex.lab = axis_cex)
  if (!is.finite(lo) && !is.finite(hi)) {
    rect(limits[[1]], 0, limits[[2]], ymax, col = adjustcolor(defer_col, 0.16), border = NA)
  } else {
    if (is.finite(lo)) rect(limits[[1]], 0, lo, ymax, col = adjustcolor(pass_col, 0.12), border = NA)
    rect(if (is.finite(lo)) lo else limits[[1]], 0, if (is.finite(hi)) hi else limits[[2]], ymax,
         col = adjustcolor(defer_col, 0.15), border = NA)
    if (is.finite(hi)) rect(hi, 0, limits[[2]], ymax, col = adjustcolor(defect_col, 0.09), border = NA)
  }
  plot(good_hist, add = TRUE, col = adjustcolor(pass_col, 0.72), border = NA)
  plot(defect_hist, add = TRUE, col = adjustcolor(defect_col, 0.62), border = NA)
  axis(1, cex.axis = tick_cex)
  axis(2, las = 1, cex.axis = tick_cex)
  box()
  # Stack / stagger when the defer band is narrow (panel d: ~0.008 vs span).
  close_thresholds <- is.finite(lo) && is.finite(hi) && ((hi - lo) < 0.08 * diff(limits))
  if (is.finite(lo)) {
    abline(v = lo, lty = 2, lwd = 1.1)
    if (close_thresholds) {
      text(lo, ymax * 0.97, expression(t[lo]),
           adj = c(1.45, 0.5), cex = body_cex, col = ANNOT_TEXT_COLOR, xpd = NA)
    } else {
      text(lo, ymax * 0.96, expression(t[lo]),
           pos = 2, offset = 0.28, cex = axis_cex, col = ANNOT_TEXT_COLOR)
    }
  }
  if (is.finite(hi)) {
    abline(v = hi, lty = 3, lwd = 1.1)
    if (close_thresholds) {
      # Drop into the lower third and push right of the line to avoid collision.
      text(hi, ymax * 0.28, expression(t[hi]),
           adj = c(-0.35, 0.5), cex = body_cex, col = ANNOT_TEXT_COLOR, xpd = NA)
    } else {
      text(hi, ymax * 0.96, expression(t[hi]),
           pos = 4, offset = 0.28, cex = axis_cex, col = ANNOT_TEXT_COLOR)
    }
  }
  backbone_label <- if (is.null(cell$backbone)) "" else sprintf(" / %s", cell$backbone)
  ttl <- sprintf("%s %s%s", cell$benchmark, cell$category, backbone_label)
  dx <- diff(par("usr")[1:2])
  mtext(panel_label_text(cell$panel), side = 3, line = 1.70, font = 2,
        cex = panel_label_cex(12), col = PANEL_LABEL_COLOR,
        at = par("usr")[1], adj = tag_adj)
  mtext(ttl, side = 3, line = 1.70, adj = 0, cex = axis_cex, col = ANNOT_TEXT_COLOR,
        at = par("usr")[1] + title_frac * dx)
  mtext(cell_status(cell), side = 3, line = 0.75, cex = body_cex, col = ANNOT_TEXT_COLOR)
}

raw_pdf <- file.path(script_dir, "../review-scoreanatomy-build.pdf")
# Wider canvas (more landscape) + modest height trim → less vertical whitespace
# when scaled to column width in the paper.
cairo_pdf(raw_pdf, width = 6.3, height = 5.55, pointsize = 12, family = font_family)
# Regions: 1=a 2=b 3=c 4=d 5=xlab strip 6=legend;
# 7=row spacer (never plotted); 8=column gutter (never plotted).
layout(
  matrix(c(1, 8, 2,
           7, 7, 7,
           3, 8, 4,
           5, 5, 5,
           6, 6, 6), nrow = 5, byrow = TRUE),
  widths = c(1, 0.05, 1),
  heights = c(1, 0.16, 1, 0.22, 0.14)
)
par(oma = c(0, 1.05, 0, 0), mgp = c(2.0, 0.55, 0), tcl = -0.25, family = font_family)
sides <- c("left", "right", "left", "right")
for (i in seq_along(frozen$cells)) {
  render_cell(frozen$cells[[i]], side = sides[[i]])
}
# One "anomaly score" label per column, with full descender clearance.
par(mar = c(0, 0, 0, 0))
plot.new()
text(x = c(0.26, 0.78), y = 0.70, labels = c("anomaly score", "anomaly score"),
     cex = FIG_AXIS_PT / 12, col = ANNOT_TEXT_COLOR, xpd = NA, adj = c(0.5, 0.5))
par(mar = c(0, 0, 0, 0))
plot.new()
# Bottom strip legend: body 8 pt (TikZ in-axis legends use \tickfont 7 pt;
# this shared horizontal legend needs the larger body size to stay readable).
legend("center", legend = c("good (evaluation)", "defective (evaluation)", "defer region"),
       fill = c(adjustcolor(pass_col, 0.72), adjustcolor(defect_col, 0.62), adjustcolor(defer_col, 0.15)),
       border = NA, horiz = TRUE, bty = "n", cex = FIG_BODY_PT / 12,
       text.col = ANNOT_TEXT_COLOR)
dev.off()

status <- system2("gs", c("-q", "-dSAFER", "-dBATCH", "-dNOPAUSE", "-sDEVICE=pdfwrite",
                           "-dCompatibilityLevel=1.5",
                           sprintf("-sOutputFile=%s", shQuote(output_path)), shQuote(raw_pdf)))
unlink(raw_pdf)
if (!identical(status, 0L) || !file.exists(output_path)) stop("FATAL: Ghostscript PDF normalization failed")
cat(sprintf("Wrote %s from %s\n", output_path, input_path))
