# Shared physical geometry for the R/Cairo sample-routing figure.
#
# All containment arithmetic lives here so samples.R and the regression test
# share one source of truth. Units: inches for physical sizes; npc for
# fractional canvas coordinates (origin bottom-left).

canvas_width_in <- 5.25
# Cropped from 5.45: prior canvas left ~0.72 in empty below row-(d) scores,
# which pushed the LaTeX \caption far below the grid. Keep scores visible with
# a short bottom pad (~0.10 in under score glyphs).
canvas_height_in <- 4.85

# Tile / inset sizes
tile_size_in <- 0.90
zoom_size_in <- 0.30
zoom_padding_in <- 0.035

# Column centers: AUTO-PASS left edge must clear the left-gutter row title
# (panel letter is short and sits at the same left margin).
# tile left edge = column_x[1] - tile_size_in / (2 * canvas_width_in)
column_x <- c(0.355, 0.590, 0.830)
# Row centres: top-anchored remap from old height 5.45 → 4.85
# (absolute positions from the page top unchanged; bottom waste removed).
row_y <- c(0.763, 0.549, 0.334, 0.120)
# Tile centre sits slightly above row_y (shared with samples.R draw loop).
# Inch-preserving remap of prior 0.016 npc @ 5.45 in.
tile_y_offset <- 0.018
# Left-gutter labels: panel letter and row subtitle are SEPARATE elements.
# Letter at the upper-left of each row image band (top of tile strip).
# Subtitle at the left margin, vertically centered on the row of images.
# Nudge left-gutter tags further right toward the image grid / s= titles.
label_text_x <- 0.078
panel_letter_x <- label_text_x
# Align with TikZ \figfont / \panellabelfont ladder (see R/_figconst.R).
label_text_fontsize_pt <- FIG_BODY_PT
# Matches TikZ \panellabelfont (PANEL_LABEL_PT in _figconst.R).
panel_letter_fontsize_pt <- PANEL_LABEL_PT
# Title (not letter) must clear the AUTO-PASS tile's left edge.
panel_letter_tile_clearance_in <- 0.045
# Kept for tests / callers that still name the old left-gutter slot.
label_x <- label_text_x
header_y <- 0.949
header_rule_y <- 0.919
# Inch-preserving remap of prior -0.078 / 0.088 npc @ 5.45 in.
score_offset_y <- -0.088
floor_refusal_offset_y <- 0.099
tile_half_npc <- (tile_size_in / 2) / canvas_height_in
# Letter anchored at the top edge of the row's picture strip (use just=top).
panel_letter_offset_y <- tile_y_offset + tile_half_npc
# Subtitle on the horizontal midline of the row's picture strip (tile centre).
label_text_offset_y <- tile_y_offset

# Zoom sits in the upper-right of each tile with a fixed padding.
zoom_offset_x_npc <- (tile_size_in / 2 - zoom_size_in / 2 - zoom_padding_in) / canvas_width_in
zoom_offset_y_npc <- (tile_size_in / 2 - zoom_size_in / 2 - zoom_padding_in) / canvas_height_in

# "GT zoom" label sits just below the inset (outside the raster), not on top
# of the defect crop. Negative = below the zoom centre.
zoom_label <- "GT zoom"
zoom_label_fontsize_pt <- FIG_TICK_PT
zoom_label_offset_y_npc <- -(zoom_size_in / 2 + 0.055) / canvas_height_in
# Plain white only — no outline/halo.
zoom_label_color <- "white"
