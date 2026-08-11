# Shared physical geometry for the R/Cairo sample-routing figure.
#
# All containment arithmetic lives here so samples.R and the regression test
# share one source of truth. Units: inches for physical sizes; npc for
# fractional canvas coordinates (origin bottom-left).

canvas_width_in <- 5.25
canvas_height_in <- 5.45

# Tile / inset sizes
tile_size_in <- 0.90
zoom_size_in <- 0.30
zoom_padding_in <- 0.035

# Column centers: AUTO-PASS left edge must clear the left-gutter row title
# (panel letter is short and sits at the same left margin).
# tile left edge = column_x[1] - tile_size_in / (2 * canvas_width_in)
column_x <- c(0.355, 0.590, 0.830)
row_y <- c(0.790, 0.590, 0.390, 0.190)
# Tile centre sits slightly above row_y (shared with samples.R draw loop).
tile_y_offset <- 0.016
# Left-gutter labels: panel letter and row subtitle are SEPARATE elements.
# Letter at the left margin, vertically centered on the row image band.
# Subtitle also at the left margin, in the lower-left (score baseline).
label_text_x <- 0.012
panel_letter_x <- label_text_x
# Align with TikZ \figfont / \panellabelfont ladder (see R/_figconst.R).
label_text_fontsize_pt <- FIG_BODY_PT
# Matches TikZ \panellabelfont (PANEL_LABEL_PT in _figconst.R).
panel_letter_fontsize_pt <- PANEL_LABEL_PT
# Title (not letter) must clear the AUTO-PASS tile's left edge.
panel_letter_tile_clearance_in <- 0.045
# Kept for tests / callers that still name the old left-gutter slot.
label_x <- label_text_x
header_y <- 0.955
header_rule_y <- 0.928
score_offset_y <- -0.085
floor_refusal_offset_y <- 0.088
tile_half_npc <- (tile_size_in / 2) / canvas_height_in
# Letter on the horizontal midline of the row's picture strip (tile centre).
panel_letter_offset_y <- tile_y_offset
# Subtitle on its own node in the lower-left, sharing the score baseline.
label_text_offset_y <- score_offset_y

# Zoom sits in the upper-right of each tile with a fixed padding.
zoom_offset_x_npc <- (tile_size_in / 2 - zoom_size_in / 2 - zoom_padding_in) / canvas_width_in
zoom_offset_y_npc <- (tile_size_in / 2 - zoom_size_in / 2 - zoom_padding_in) / canvas_height_in

# "GT zoom" label sits just below the inset (outside the raster), not on top
# of the defect crop. Negative = below the zoom centre.
zoom_label <- "GT zoom"
zoom_label_fontsize_pt <- FIG_TICK_PT
zoom_label_offset_y_npc <- -(zoom_size_in / 2 + 0.055) / canvas_height_in
