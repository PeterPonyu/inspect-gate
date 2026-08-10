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

# Cairo typeface — closest available match to TikZ / elsarticle Computer Modern
# (inspect_style.tex uses default CM, no lmodern):
#   1. CMU Serif  — Computer Modern Unicode (TeXLive cm-unicode / cmunrm.otf).
#                   Preferred: same design family as paper body CM, not Times.
#   2. FreeSerif  — fallback when CMU is not on the fontconfig path.
# Do NOT use TeX Gyre Termes / Times clones (paper body is CM, not Times).
# Latin Modern is optically close but the manuscript deliberately omits
# lmodern; CMU is the Unicode CM face for Cairo.
#
# Impact: samples.R (Fig 3) sources this file too — both R/Cairo figures stay
# on the same face. Rebuild fig-samples.pdf whenever INSPECT_FONT changes.
# Makefile R/Cairo recipes set FONTCONFIG_FILE=../fontconfig/fonts.conf so
# TeXLive's cm-unicode dir is visible even when not registered system-wide.
.inspect_figconst_dir <- function() {
  # Directory containing this file when sourced (R/_figconst.R).
  src <- NULL
  if (sys.nframe() >= 1L) {
    for (i in seq_len(sys.nframe())) {
      of <- sys.frame(i)$ofile
      if (!is.null(of)) src <- of
    }
  }
  if (is.null(src)) {
    return(NA_character_)
  }
  dirname(normalizePath(src, mustWork = FALSE))
}

.inspect_ensure_fontconfig <- function() {
  # Makefile sets FONTCONFIG_FILE for `make fig-*.pdf`. Also wire it when
  # scripts are sourced directly so Cairo can see TeXLive cm-unicode.
  # Always normalize to an absolute path (relative paths break fc-match/Cairo).
  cur <- Sys.getenv("FONTCONFIG_FILE", unset = "")
  if (nzchar(cur)) {
    abs <- suppressWarnings(normalizePath(cur, mustWork = FALSE))
    if (nzchar(abs) && file.exists(abs)) {
      Sys.setenv(FONTCONFIG_FILE = abs)
      return(invisible(TRUE))
    }
  }
  fig_dir <- .inspect_figconst_dir()
  if (is.na(fig_dir)) {
    return(invisible(FALSE))
  }
  cand <- normalizePath(
    file.path(fig_dir, "..", "fontconfig", "fonts.conf"),
    mustWork = FALSE
  )
  if (file.exists(cand)) {
    Sys.setenv(FONTCONFIG_FILE = cand)
    return(invisible(TRUE))
  }
  invisible(FALSE)
}

.inspect_fc_has_family <- function(family) {
  # fc-match returns the best match; require the requested family name.
  # Do not put a literal newline in -f (R "\n" breaks the argv).
  out <- tryCatch(
    suppressWarnings(
      system2(
        "fc-match",
        args = c("-f", "%{family[0]}", family),
        stdout = TRUE,
        stderr = TRUE
      )
    ),
    error = function(e) character()
  )
  if (!length(out)) {
    return(FALSE)
  }
  # Drop fontconfig warnings; keep the last non-empty line as the family.
  lines <- trimws(out)
  lines <- lines[nzchar(lines) & !grepl("^Fontconfig", lines)]
  length(lines) > 0L && identical(lines[[length(lines)]], family)
}

.inspect_pick_font <- function() {
  .inspect_ensure_fontconfig()
  # Prefer CMU Serif when fontconfig resolves it (local fonts.conf → TeXLive
  # cm-unicode). Fall back to FreeSerif size ladder if CMU is unavailable.
  if (.inspect_fc_has_family("CMU Serif")) {
    return("CMU Serif")
  }
  cmu_otf <- "/usr/share/texlive/texmf-dist/fonts/opentype/public/cm-unicode/cmunrm.otf"
  if (file.exists(cmu_otf) && nzchar(Sys.getenv("FONTCONFIG_FILE", unset = ""))) {
    # fonts.conf is wired; trust TeXLive even if fc-match is noisy.
    return("CMU Serif")
  }
  if (.inspect_fc_has_family("FreeSerif")) {
    return("FreeSerif")
  }
  ""
}

INSPECT_FONT <- .inspect_pick_font()

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
# TikZ ladder (inspect_style.tex) for Cairo:
#   \tickfont / legend ≈ 7, \figfont / body ≈ 8, \axislabelfont / title / panel ≈ 9
FIG_TICK_PT <- 7
FIG_BODY_PT <- 8
FIG_AXIS_PT <- 9
