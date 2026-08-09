# ==========================================================================
# _figconst.R -- shared constants for the Inspect gate figures.
#
# The two base-R/grid figure scripts (samples.R, scoreanatomy.R) both hard-code
# the same three gate-route colours and the same serif font family. They live
# here in exactly ONE place so a change maps to one symbol:
#
#   want to change...              edit this symbol
#   ------------------------------------------------------------------
#   the figure serif font          INSPECT_FONT
#   the AUTO-PASS route colour      ROUTE_PASS
#   the DEFER route colour          ROUTE_DEFER
#   the AUTO-REJECT route colour    ROUTE_REJECT
#   all three, in pass/defer/reject order  ROUTE_COLORS
#
# NOTE: these scripts are base-R/grid + Ghostscript-normalised, NOT ggplot.
# Only the colour/font constants are shared; each script keeps its own
# cairo_pdf/gs render path. Output is verified pixel-equivalent to the
# pre-refactor scripts.
# ==========================================================================

# Serif family (LaTeX body match). Both figures render with cairo_pdf in this
# family, then Ghostscript-normalise to Type 1 embedded fonts.
INSPECT_FONT <- "Latin Modern Roman"

# The three certified-triage route colours (Okabe-Ito green/orange/vermillion).
ROUTE_PASS   <- "#009E73"  # AUTO-PASS
ROUTE_DEFER  <- "#E69F00"  # DEFER
ROUTE_REJECT <- "#D55E00"  # AUTO-REJECT

# Convenience vector in column order (AUTO-PASS, DEFER, AUTO-REJECT).
ROUTE_COLORS <- c(ROUTE_PASS, ROUTE_DEFER, ROUTE_REJECT)
