# Shared physical geometry for the R/Cairo sample-routing figure.
#
# All containment arithmetic lives here so samples.R and the regression test
# share one source of truth. Units: inches for physical sizes; npc for
# fractional canvas coordinates (origin bottom-left).

canvas_width_in <- 5.15
canvas_height_in <- 5.45

# Tile / inset sizes
tile_size_in <- 0.90
zoom_size_in <- 0.30
zoom_padding_in <- 0.035

# Column centers chosen so the AUTO-PASS tile's left edge clears the widest
# left-margin row label ("MPDD - defect" at 8.2 pt bold ≈ 0.95 in).
# tile left edge = column_x[1] - tile_size_in / (2 * canvas_width_in)
column_x <- c(0.335, 0.580, 0.825)
row_y <- c(0.790, 0.590, 0.390, 0.190)
# Panel letter (a–d) and the row annotation are drawn separately so the
# letter can sit higher while the annotation shifts right of the letter.
label_x <- 0.012
label_text_x <- 0.042
panel_letter_offset_y <- 0.034
label_text_offset_y <- -0.006
header_y <- 0.955
header_rule_y <- 0.928
score_offset_y <- -0.085
floor_refusal_offset_y <- 0.088

# Zoom sits in the upper-right of each tile with a fixed padding.
zoom_offset_x_npc <- (tile_size_in / 2 - zoom_size_in / 2 - zoom_padding_in) / canvas_width_in
zoom_offset_y_npc <- (tile_size_in / 2 - zoom_size_in / 2 - zoom_padding_in) / canvas_height_in

# "GT zoom" label sits just below the inset (outside the raster), not on top
# of the defect crop. Negative = below the zoom centre.
zoom_label <- "GT zoom"
zoom_label_fontsize_pt <- 7.0
zoom_label_offset_y_npc <- -(zoom_size_in / 2 + 0.055) / canvas_height_in
