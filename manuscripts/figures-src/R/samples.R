#!/usr/bin/env Rscript
# Render the frozen four-row gate-decision sample grid with R/Cairo.

suppressPackageStartupMessages({
  library(grid)
  library(png)
})

script_arg <- grep("^--file=", commandArgs(), value = TRUE)
script_path <- if (length(script_arg)) sub("^--file=", "", script_arg[[1]]) else "samples.R"
script_dir <- normalizePath(dirname(script_path), mustWork = TRUE)
assets_dir <- file.path(script_dir, "../canonical_samples_assets")
manifest_path <- file.path(assets_dir, "manifest.txt")
output_path <- file.path(script_dir, "../fig-samples.pdf")
source(file.path(script_dir, "_figconst.R"))  # INSPECT_FONT, ROUTE_COLORS
source(file.path(script_dir, "_samples_layout.R"))
font_family <- INSPECT_FONT

if (!dir.exists(assets_dir)) {
  stop(sprintf("FATAL: canonical sample assets not found: %s", assets_dir))
}
if (!file.exists(manifest_path)) {
  stop(sprintf("FATAL: canonical asset manifest not found: %s", manifest_path))
}

asset_path <- function(index) {
  path <- file.path(assets_dir, sprintf("extracted-%03d.png", index))
  if (!file.exists(path)) stop(sprintf("FATAL: missing canonical sample asset: %s", path))
  path
}

# pdfimages object order in the frozen source: 12 full tiles and six GT zooms.
rows <- list(
  list(
    panel = "a", label = "MPDD - good", scores = c(0.02, 0.00, 0.57),
    tiles = c(0L, 1L, 2L), zooms = c(NA, NA, NA)
  ),
  list(
    panel = "b", label = "MPDD - defect", scores = c(0.32, 0.52, 0.57),
    tiles = c(3L, 5L, 7L), zooms = c(4L, 6L, 8L)
  ),
  list(
    panel = "c", label = "VisA - good", scores = c(0.29, 0.44, 0.68),
    tiles = c(9L, 10L, 11L), zooms = c(NA, NA, NA)
  ),
  list(
    panel = "d", label = "VisA - defect", scores = c(0.42, 0.49, 0.57),
    tiles = c(12L, 14L, 16L), zooms = c(13L, 15L, 17L)
  )
)

raw_pdf <- tempfile(fileext = ".pdf")
cairo_pdf(
  raw_pdf, width = canvas_width_in, height = canvas_height_in,
  family = font_family, pointsize = 12
)
grid.newpage()

column_labels <- c("AUTO-PASS", "DEFER", "AUTO-REJECT")
route_colours <- ROUTE_COLORS
tile_size <- unit(tile_size_in, "in")

for (j in seq_along(column_x)) {
  grid.text(
    column_labels[[j]], x = column_x[[j]], y = header_y,
    gp = gpar(fontsize = FIG_AXIS_PT, fontface = "plain", fontfamily = font_family, col = route_colours[[j]])
  )
  grid.lines(
    x = unit(column_x[[j]] + c(-0.100, 0.100), "npc"),
    y = unit(c(header_rule_y, header_rule_y), "npc"),
    gp = gpar(col = route_colours[[j]], lwd = 1.3)
  )
}

for (i in seq_along(rows)) {
  row <- rows[[i]]
  # House style: only panel letters are bold; row titles stay medium/plain.
  # Letter and subtitle are separate nodes: letter at upper-left of the row
  # image band; subtitle vertically centered on the row of images.
  title_gp <- gpar(
    fontsize = label_text_fontsize_pt, fontface = "plain", fontfamily = font_family
  )
  letter_gp <- gpar(
    fontsize = panel_letter_fontsize_pt, fontface = PANEL_LABEL_FACE,
    col = PANEL_LABEL_COLOR, fontfamily = font_family
  )
  panel_tag <- panel_label_text(row$panel)
  grid.text(
    panel_tag,
    x = panel_letter_x, y = row_y[[i]] + panel_letter_offset_y,
    just = c("left", "top"),
    gp = letter_gp
  )
  grid.text(
    row$label,
    x = label_text_x, y = row_y[[i]] + label_text_offset_y, just = "left",
    gp = title_gp
  )

  for (j in seq_along(column_x)) {
    tile_y <- row_y[[i]] + tile_y_offset
    tile <- readPNG(asset_path(row$tiles[[j]]))
    grid.raster(tile, x = column_x[[j]], y = tile_y, width = tile_size, height = tile_size)
    grid.rect(
      x = column_x[[j]], y = tile_y, width = tile_size, height = tile_size,
      gp = gpar(fill = NA, col = route_colours[[j]], lwd = 1.3)
    )

    zoom_index <- row$zooms[[j]]
    if (!is.na(zoom_index)) {
      zoom <- readPNG(asset_path(zoom_index))
      zoom_x <- column_x[[j]] + zoom_offset_x_npc
      zoom_y <- tile_y + zoom_offset_y_npc
      grid.raster(
        zoom, x = zoom_x, y = zoom_y,
        width = unit(zoom_size_in, "in"), height = unit(zoom_size_in, "in")
      )
      grid.rect(
        x = zoom_x, y = zoom_y,
        width = unit(zoom_size_in, "in"), height = unit(zoom_size_in, "in"),
        gp = gpar(fill = NA, col = "white", lwd = 0.9)
      )
      # Label below the inset so it never occludes the GT crop.
      # Plain white only (no outline/halo).
      zoom_label_y <- zoom_y + zoom_label_offset_y_npc
      grid.text(
        zoom_label, x = zoom_x, y = zoom_label_y,
        gp = gpar(
          fontsize = zoom_label_fontsize_pt, fontfamily = font_family,
          col = zoom_label_color
        )
      )
    }

    grid.text(
      sprintf("s = %.2f", row$scores[[j]]),
      x = column_x[[j]], y = row_y[[i]] + score_offset_y,
      gp = gpar(fontsize = FIG_BODY_PT, fontface = "plain", fontfamily = font_family, col = ANNOT_TEXT_COLOR)
    )
    if (i == 1L && j == 2L) {
      grid.text(
        "floor refusal", x = column_x[[j]],
        y = row_y[[i]] + floor_refusal_offset_y,
        gp = gpar(fontsize = FIG_TICK_PT, fontface = "plain", fontfamily = font_family, col = "white")
      )
    }
  }
}

dev.off()

status <- system2(
  "gs",
  c(
    "-q", "-dBATCH", "-dNOPAUSE", "-sDEVICE=pdfwrite",
    "-dCompatibilityLevel=1.5",
    sprintf("-sOutputFile=%s", shQuote(output_path)),
    shQuote(raw_pdf)
  )
)
unlink(raw_pdf)
if (!identical(status, 0L) || !file.exists(output_path)) {
  stop("FATAL: Ghostscript PDF normalization failed")
}

cat(sprintf("Wrote %s from 18 manifest-tracked image objects\n", output_path))
