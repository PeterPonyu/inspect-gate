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

# Fig-scoreanatomy page-readability ladder (scoped to this figure only).
# House ladder in _figconst / TikZ remains tick 7 / body 8 / axis 9 / panel 9.
# Aim for a coherent ~9–11 pt family after include scale: modest bump on
# ticks/body, titles one step up, panel tags bold but not huge vs body.
# layout() resets par("cex") to ~0.66 — we force cex=1 after layout so
# axis/text/legend (cex-relative) match mtext (absolute) sizes.
FIG_TICK_PT <- 9.5
FIG_BODY_PT <- 9.5
FIG_AXIS_PT <- 10
PANEL_LABEL_PT <- 11

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

# White halo under annotation text so dashed/dotted spines and bar tops do not
# strike through t_lo / t_hi labels.
halo_text <- function(x, y, labels, ..., col = ANNOT_TEXT_COLOR, halo = "white",
                      r_frac = 0.018) {
  usr <- par("usr")
  rx <- r_frac * diff(usr[1:2])
  ry <- r_frac * diff(usr[3:4])
  angles <- seq(0, 2 * pi, length.out = 17L)[-17L]
  for (a in angles) {
    text(x + cos(a) * rx, y + sin(a) * ry, labels, ..., col = halo)
  }
  text(x, y, labels, ..., col = col)
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
  # Extra headroom when the defer band is narrow (panel d): labels sit above
  # tall bars instead of crowding bar tops / spines.
  close_thresholds <- is.finite(lo) && is.finite(hi) && ((hi - lo) < 0.08 * diff(limits))
  ymax <- max(c(good_hist$counts, defect_hist$counts, 1)) * if (close_thresholds) 1.55 else 1.28
  x_span <- diff(limits)
  # Data-coord gap so label glyphs clear the spine (pos/offset=~char-width is too tight).
  spine_gap <- if (close_thresholds) 0.055 * x_span else 0.045 * x_span

  # Left column (a,c): tighter right margin + titles pulled left so they do not
  # reach into the gutter where (b)/(d) panel letters sit. Right column (b,d):
  # wider left margin so those letters clear the a/c titles.
  # X-axis title is drawn once per column in a dedicated strip below the grid
  # (not via plot xlab), so descenders are never clipped by the panel cell.
  if (identical(side, "left")) {
    # Wider left for full-size "images" ylab after cex=1; top for titles/tags.
    # Bottom mar kept modest so C/D sit closer to the xlab strip + legend.
    par(mar = c(1.55, 4.15, 3.20, 0.15))
    title_frac <- 0.06
    tag_adj <- 1.65
  } else {
    # Keep enough left margin for the "images" ylab after the narrow gutter.
    par(mar = c(1.55, 3.25, 3.20, 0.55))
    title_frac <- 0.22
    tag_adj <- 1.40
  }

  # Size ladder vs cairo_pdf(pointsize=12): tick / body / axis+title
  # (Fig 2 overrides; see top-of-file FIG_* / PANEL_LABEL_PT).
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
  # t_lo / t_hi use axis size (matches titles); expression() subscripts read a
  # touch smaller optically, so do not drop to tick size.
  # Before: a/b pos offset=0.28 @ ymax*0.96 (flush to spines); d adj (1.45/-0.35),
  # hi @ ymax*0.28. After: explicit spine_gap in data coords + halo; panel d
  # both labels in raised headroom (ymax×1.55), outward of their spines.
  if (is.finite(lo)) {
    abline(v = lo, lty = 2, lwd = 1.1)
    if (close_thresholds) {
      halo_text(lo - spine_gap, ymax * 0.93, expression(t[lo]),
                adj = c(1, 0.5), cex = axis_cex, xpd = NA)
    } else {
      halo_text(lo - spine_gap, ymax * 0.96, expression(t[lo]),
                adj = c(1, 0.5), cex = axis_cex)
    }
  }
  if (is.finite(hi)) {
    abline(v = hi, lty = 3, lwd = 1.1)
    if (close_thresholds) {
      halo_text(hi + spine_gap, ymax * 0.82, expression(t[hi]),
                adj = c(0, 0.5), cex = axis_cex, xpd = NA)
    } else {
      halo_text(hi + spine_gap, ymax * 0.96, expression(t[hi]),
                adj = c(0, 0.5), cex = axis_cex)
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
# Slightly wider canvas so larger fonts keep readable at column width.
# Slightly shorter canvas after tightening row spacer + plot-to-legend band.
cairo_pdf(raw_pdf, width = 6.5, height = 5.30, pointsize = 12, family = font_family)
# Regions: 1=a 2=b 3=c 4=d 5=xlab strip 6=legend;
# 7=row spacer (never plotted); 8=column gutter (never plotted).
layout(
  matrix(c(1, 8, 2,
           7, 7, 7,
           3, 8, 4,
           5, 5, 5,
           6, 6, 6), nrow = 5, byrow = TRUE),
  widths = c(1, 0.04, 1),
  # heights: panels | row-gap | panels | xlab | legend
  # Tighten inter-row (was 0.16) and plot→legend band (xlab 0.26→0.18, legend 0.18→0.16).
  heights = c(1, 0.08, 1, 0.18, 0.16)
)
# layout() drops cex to ~0.66; restore 1 so FIG_*_PT / 12 maps to true pt
# for axis / text / legend (mtext cex is already absolute).
par(oma = c(0, 1.15, 0, 0), mgp = c(2.0, 0.55, 0), tcl = -0.25,
    family = font_family, cex = 1)
sides <- c("left", "right", "left", "right")
for (i in seq_along(frozen$cells)) {
  render_cell(frozen$cells[[i]], side = sides[[i]])
}
# One "anomaly score" label per column, with full descender clearance.
par(mar = c(0, 0, 0, 0))
plot.new()
text(x = c(0.26, 0.78), y = 0.55, labels = c("anomaly score", "anomaly score"),
     cex = FIG_AXIS_PT / 12, col = ANNOT_TEXT_COLOR, xpd = NA, adj = c(0.5, 0.5))
par(mar = c(0, 0, 0, 0))
plot.new()
# Bottom strip legend: uses FIG_BODY_PT (raised for page readability).
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
