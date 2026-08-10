# ==========================================================================
# _figconst.R -- shared constants for the Inspect gate figures.
#
# The two base-R/grid figure scripts (samples.R, scoreanatomy.R) both hard-code
# the same three gate-route colours and the same serif font family. They live
# here in exactly ONE place so a change maps to one symbol:
#
#   want to change...              edit this symbol
#   ------------------------------------------------------------------
#   the figure font family         INSPECT_FONT  ("" = device default)
#   the AUTO-PASS route colour      ROUTE_PASS
#   the DEFER route colour          ROUTE_DEFER
#   the AUTO-REJECT route colour    ROUTE_REJECT
#   all three, in pass/defer/reject order  ROUTE_COLORS
#   panel tag (a)/(b)/… style+size   PANEL_LABEL_*  (mirrors TikZ SSOT)
#
# NOTE: these scripts are base-R/grid, NOT ggplot.
# Only the colour/font constants are shared; each script keeps its own
# cairo_pdf render path.
#
# Panel-label house style (must match tikz/inspect_style.tex):
#   format (a), 9 pt, bold, black.
# Bold weight policy: ONLY panel letters may be bold. Row/column headers,
# titles, legends, score annotations, and other figure text stay plain.
# ==========================================================================

# Generic serif for Cairo (FreeSerif). Not a figure-only face like Latin
# Modern — TikZ/LaTeX figures use Computer Modern defaults (no lmodern).
INSPECT_FONT <- "FreeSerif"

# The three certified-triage route colours (Okabe-Ito green/orange/vermillion).
ROUTE_PASS   <- "#009E73"  # AUTO-PASS
ROUTE_DEFER  <- "#E69F00"  # DEFER
ROUTE_REJECT <- "#D55E00"  # AUTO-REJECT

# Convenience vector in column order (AUTO-PASS, DEFER, AUTO-REJECT).
ROUTE_COLORS <- c(ROUTE_PASS, ROUTE_DEFER, ROUTE_REJECT)

# Panel tags — keep in lockstep with \panellabelfont / \panellabeltext.
PANEL_LABEL_PT <- 9
PANEL_LABEL_FACE <- "bold"
PANEL_LABEL_COLOR <- "black"
panel_label_text <- function(letter) sprintf("(%s)", as.character(letter))
# cex relative to the cairo_pdf/pdf pointsize (default 12 → 9 pt ⇒ 0.75).
panel_label_cex <- function(pointsize = 12) PANEL_LABEL_PT / pointsize

# Non-panel figure text (annotations, zoom labels, scores): plain black.
# Mirrors TikZ house style (prefer text=black, never grey35 / black!NN).
ANNOT_TEXT_COLOR <- "black"
# Approximate TikZ ladder for Cairo FreeSerif (pt):
#   tick/legend ≈ 7, body/fig ≈ 8, axis/title/panel ≈ 9
FIG_TICK_PT <- 7
FIG_BODY_PT <- 8
FIG_AXIS_PT <- 9
