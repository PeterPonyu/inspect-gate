#!/usr/bin/env Rscript
# Regression checks for the sample-routing figure geometry.

script_arg <- grep("^--file=", commandArgs(), value = TRUE)
script_path <- if (length(script_arg)) sub("^--file=", "", script_arg[[1]]) else "test_samples_layout.R"
script_dir <- normalizePath(dirname(script_path), mustWork = TRUE)

layout_env <- environment()
source(file.path(script_dir, "_figconst.R"), local = layout_env)
source(file.path(script_dir, "_samples_layout.R"), local = layout_env)

required <- c(
  "canvas_width_in", "canvas_height_in", "tile_size_in", "zoom_size_in",
  "zoom_padding_in", "zoom_offset_x_npc", "zoom_offset_y_npc",
  "zoom_label", "zoom_label_fontsize_pt", "zoom_label_offset_y_npc",
  "column_x", "label_x", "label_text_x", "panel_letter_x",
  "panel_letter_offset_y", "label_text_offset_y",
  "panel_letter_fontsize_pt", "label_text_fontsize_pt",
  "panel_letter_tile_clearance_in", "tile_y_offset", "score_offset_y",
  "tile_half_npc"
)
missing <- required[!vapply(required, exists, logical(1), envir = layout_env, inherits = FALSE)]
if (length(missing)) {
  stop(sprintf(
    "FAIL: samples layout does not expose containment geometry: %s",
    paste(missing, collapse = ", ")
  ))
}

half_tile <- tile_size_in / 2
half_zoom <- zoom_size_in / 2
right_clearance <- half_tile - (zoom_offset_x_npc * canvas_width_in + half_zoom)
top_clearance <- half_tile - (zoom_offset_y_npc * canvas_height_in + half_zoom)

# "GT zoom" is placed below the inset; require it to clear the crop and stay
# inside the parent tile. Approximate line height conservatively by the point size.
label_from_zoom_center <- zoom_label_offset_y_npc * canvas_height_in
label_height_in <- zoom_label_fontsize_pt / 72
label_top_from_tile_center <- zoom_offset_y_npc * canvas_height_in + label_from_zoom_center + label_height_in / 2
label_bottom_from_tile_center <- zoom_offset_y_npc * canvas_height_in + label_from_zoom_center - label_height_in / 2
label_clearance_below_zoom <- (zoom_offset_y_npc * canvas_height_in - half_zoom) - label_top_from_tile_center
label_clearance_from_tile_bottom <- label_bottom_from_tile_center + half_tile

if (right_clearance + 1e-9 < zoom_padding_in) {
  stop(sprintf(
    "FAIL: GT zoom crosses the tile's right padding (clearance %.4f in; required %.4f in)",
    right_clearance, zoom_padding_in
  ))
}
if (top_clearance + 1e-9 < zoom_padding_in) {
  stop(sprintf(
    "FAIL: GT zoom crosses the tile's top padding (clearance %.4f in; required %.4f in)",
    top_clearance, zoom_padding_in
  ))
}
if (label_clearance_below_zoom + 1e-9 < 0) {
  stop(sprintf(
    "FAIL: GT zoom label overlaps the inset (clearance %.4f in)",
    label_clearance_below_zoom
  ))
}
if (label_clearance_from_tile_bottom + 1e-9 < 0) {
  stop(sprintf(
    "FAIL: GT zoom label falls below the tile (clearance %.4f in)",
    label_clearance_from_tile_bottom
  ))
}

# Widest row title at the left margin must clear the AUTO-PASS tile left edge.
# Empirical "MPDD - defect" @ 8.2 pt plain ≈ 0.90 in; keep 0.95 in as a
# conservative upper bound. Panel letter is short and shares the left margin.
widest_label_in <- 0.95
tile_left_in <- column_x[[1]] * canvas_width_in - half_tile
title_right_in <- label_text_x * canvas_width_in + widest_label_in
label_tile_gap <- tile_left_in - title_right_in
min_label_gap_in <- panel_letter_tile_clearance_in
if (label_tile_gap + 1e-9 < min_label_gap_in) {
  stop(sprintf(
    "FAIL: row title collides with AUTO-PASS tile (gap %.4f in; required %.4f in)",
    label_tile_gap, min_label_gap_in
  ))
}

# Panel letter must sit on the row image midline (tile centre), not on a
# combined letter+subtitle block mid.
if (abs(panel_letter_offset_y - tile_y_offset) > 1e-9) {
  stop(sprintf(
    "FAIL: panel letter offset (%.4f) must equal tile_y_offset (%.4f) for image-midline centering",
    panel_letter_offset_y, tile_y_offset
  ))
}
if (panel_letter_offset_y + 1e-9 < label_text_offset_y) {
  stop(sprintf(
    "FAIL: panel letter offset (%.4f) must sit above subtitle offset (%.4f)",
    panel_letter_offset_y, label_text_offset_y
  ))
}
if (abs(label_text_offset_y - score_offset_y) > 1e-9) {
  stop(sprintf(
    "FAIL: subtitle offset (%.4f) must track score baseline (%.4f)",
    label_text_offset_y, score_offset_y
  ))
}
if (abs(panel_letter_x - label_text_x) > 1e-9) {
  stop(sprintf(
    "FAIL: panel letter x (%.4f) must share left gutter with subtitle x (%.4f)",
    panel_letter_x, label_text_x
  ))
}
if (panel_letter_fontsize_pt + 1e-9 < label_text_fontsize_pt) {
  stop(sprintf(
    "FAIL: panel letter (%.1f pt) must be larger than title (%.1f pt)",
    panel_letter_fontsize_pt, label_text_fontsize_pt
  ))
}

cat(sprintf(
  paste0(
    "PASS: zoom contained (%.3f in pad); GT label below inset; ",
    "title/tile gap %.3f in; letter on tile mid (%.4f); subtitle at score y (%.4f)\n"
  ),
  zoom_padding_in, label_tile_gap, panel_letter_offset_y, label_text_offset_y
))
