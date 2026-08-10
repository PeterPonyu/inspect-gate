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

# Column centers: AUTO-PASS left edge must clear title + enlarged "(d)" tag.
# tile left edge = column_x[1] - tile_size_in / (2 * canvas_width_in)
column_x <- c(0.355, 0.590, 0.830)
row_y <- c(0.790, 0.590, 0.390, 0.190)
# Tile centre sits slightly above row_y (shared with samples.R draw loop).
tile_y_offset <- 0.016
# Row title starts at the left margin; panel letter sits at the title's
# top-right (after the title string, slightly above), enlarged, and must
# clear the AUTO-PASS tile's top-left corner.
label_text_x <- 0.012
# Align with TikZ \figfont / \panellabelfont ladder (see R/_figconst.R).
label_text_fontsize_pt <- FIG_BODY_PT
# Matches TikZ \panellabelfont (PANEL_LABEL_PT in _figconst.R).
panel_letter_fontsize_pt <- PANEL_LABEL_PT
panel_letter_gap_after_title_in <- 0.040
panel_letter_tile_clearance_in <- 0.045
# Kept for tests / callers that still name the old left-gutter slot.
label_x <- label_text_x
header_y <- 0.955
header_rule_y <- 0.928
score_offset_y <- -0.085
floor_refusal_offset_y <- 0.088
# Vertically center the letter+title block on the tile+score visual unit
# (tile top → score baseline). Preserve letter-above-title separation.
tile_half_npc <- (tile_size_in / 2) / canvas_height_in
label_row_unit_mid_y <- ((tile_y_offset + tile_half_npc) + score_offset_y) / 2
panel_letter_title_sep_y <- 0.048
panel_letter_offset_y <- label_row_unit_mid_y + panel_letter_title_sep_y / 2
label_text_offset_y <- label_row_unit_mid_y - panel_letter_title_sep_y / 2

# Zoom sits in the upper-right of each tile with a fixed padding.
zoom_offset_x_npc <- (tile_size_in / 2 - zoom_size_in / 2 - zoom_padding_in) / canvas_width_in
zoom_offset_y_npc <- (tile_size_in / 2 - zoom_size_in / 2 - zoom_padding_in) / canvas_height_in

# "GT zoom" label sits just below the inset (outside the raster), not on top
# of the defect crop. Negative = below the zoom centre.
zoom_label <- "GT zoom"
zoom_label_fontsize_pt <- FIG_TICK_PT
zoom_label_offset_y_npc <- -(zoom_size_in / 2 + 0.055) / canvas_height_in
