#!/usr/bin/env Rscript
# Normalize jointmon data for TikZ rendering (full a–d design-space figure).
# Frozen source: drift_joint_monitor_2026-08-01/results.json
#
# Outputs (CSV digests + explicit TikZ fragments; never hand-edit out/*.tex):
#   jointmon_panel_a.csv / out/jointmon-panel-a.tex   dumbbells
#   jointmon_panel_b.csv / out/jointmon-panel-b.tex   ROC operating points
#   jointmon_panel_c.csv / out/jointmon-panel-c.tex   z_good vs z_defect cloud
#   jointmon_panel_d.csv / out/jointmon-panel-d.tex   catch/FA heatmap cells

library(jsonlite)

script_arg <- grep("^--file=", commandArgs(), value = TRUE)
script_path <- if (length(script_arg)) sub("^--file=", "", script_arg[[1]]) else "jointmon.R"
script_dir <- normalizePath(dirname(script_path), mustWork = TRUE)
SRC <- normalizePath(file.path(script_dir, "../../../drift_joint_monitor_2026-08-01/results.json"), mustWork = TRUE)
OUT_DIR <- script_dir
TEX_DIR <- normalizePath(file.path(OUT_DIR, "../out"), mustWork = FALSE)
dir.create(TEX_DIR, recursive = TRUE, showWarnings = FALSE)

d <- fromJSON(SRC, simplifyVector = FALSE)
h2h <- d$head_to_head
res <- d$results

G1_TARGET <- 0.10

VARIANTS <- list(
  list(key = "frozen_defect_shift_detected", label = "defect KS (frozen)", short = "defect KS"),
  list(key = "paired_good_detected", label = "paired good", short = "paired good"),
  list(key = "paired_defect_detected", label = "paired defect", short = "paired defect"),
  list(key = "cal_joint_max_detected", label = "joint max (cal-half)", short = "joint max (cal)"),
  list(key = "joint_max_detected", label = "joint max", short = "joint max")
)

# Colour = gate; marker/linestyle = detector (matches historical make_fig_jointmon.py).
# Tight within-row offsets so five categorical bands stay compact in panel a.
ARMS <- list(
  list(arm = "patchcore/g1", label = "PatchCore G1", gate = "g1",
       detector = "patchcore", yoff = 0.16, col = "cG1",
       mark_fill = "*", mark_open = "o", ls = "solid"),
  list(arm = "patchcore/g2", label = "PatchCore G2", gate = "g2",
       detector = "patchcore", yoff = 0.05, col = "cG2",
       mark_fill = "*", mark_open = "o", ls = "solid"),
  list(arm = "dinomaly/g1", label = "Dinomaly G1", gate = "g1",
       detector = "dinomaly", yoff = -0.05, col = "cG1",
       mark_fill = "square*", mark_open = "square", ls = "dashed"),
  list(arm = "dinomaly/g2", label = "Dinomaly G2", gate = "g2",
       detector = "dinomaly", yoff = -0.16, col = "cG2",
       mark_fill = "square*", mark_open = "square", ls = "dashed")
)

FA_KEY <- list(
  frozen_defect_shift_detected = "fa_frozen_defect_shift_detected",
  paired_defect_detected = "fa_paired_defect_detected",
  joint_max_detected = "fa_joint_max_detected"
)

fmt <- function(x) format(x, digits = 12, scientific = FALSE, trim = TRUE)

# ── Panel a: dumbbell data + TikZ ───────────────────────────────────────────
panel_a_rows <- list()
panel_a_tikz <- character(0)
for (i in seq_along(VARIANTS)) {
  vkey <- VARIANTS[[i]]$key
  vlabel <- VARIANTS[[i]]$label
  y_pos <- -(i - 1)

  for (arm_spec in ARMS) {
    arm <- arm_spec$arm
    e <- h2h[[arm]]
    n_ex <- ifelse(is.null(e$good_accepted_exceed), 0, e$good_accepted_exceed)
    n_no <- ifelse(is.null(e$no_exceed), 0, e$no_exceed)
    fa_key <- FA_KEY[[vkey]]
    yoff <- y_pos + arm_spec$yoff
    col <- arm_spec$col

    if (n_ex > 0) {
      catch_val <- ifelse(is.null(e[[vkey]]), 0, e[[vkey]]) / n_ex
    } else {
      catch_val <- NA
    }

    if (!is.null(fa_key) && n_no > 0) {
      fa_val <- ifelse(is.null(e[[fa_key]]), 0, e[[fa_key]]) / n_no
    } else {
      fa_val <- NA
    }

    panel_a_rows[[length(panel_a_rows) + 1]] <- data.frame(
      variant = vlabel,
      variant_key = vkey,
      y_pos = y_pos,
      y_off = yoff,
      arm = arm,
      arm_label = arm_spec$label,
      gate = arm_spec$gate,
      detector = arm_spec$detector,
      catch = catch_val,
      false_alarm = fa_val,
      stringsAsFactors = FALSE
    )

    if (is.na(catch_val)) next
    if (is.na(fa_val)) {
      # Catch-only (no FA column): open mark at catch
      panel_a_tikz <- c(panel_a_tikz, sprintf(
        "\\addplot[%s, only marks, mark=%s, mark size=1.7pt, forget plot] coordinates {(%s,%s)};",
        col, arm_spec$mark_open, fmt(catch_val), fmt(yoff)))
    } else {
      panel_a_tikz <- c(panel_a_tikz,
        sprintf("\\draw[%s, %s, line width=0.75pt, opacity=0.85] (axis cs:%s,%s) -- (axis cs:%s,%s);",
                col, arm_spec$ls, fmt(fa_val), fmt(yoff), fmt(catch_val), fmt(yoff)),
        # open = false-alarm, filled = catch
        sprintf("\\addplot[%s, only marks, mark=%s, mark size=1.7pt, forget plot] coordinates {(%s,%s)};",
                col, arm_spec$mark_open, fmt(fa_val), fmt(yoff)),
        sprintf("\\addplot[%s, only marks, mark=%s, mark size=1.9pt, forget plot] coordinates {(%s,%s)};",
                col, arm_spec$mark_fill, fmt(catch_val), fmt(yoff)))
    }
  }
}

df_a <- do.call(rbind, panel_a_rows)
write.csv(df_a, file.path(OUT_DIR, "jointmon_panel_a.csv"), row.names = FALSE, quote = FALSE)
writeLines(c("% generated by jointmon.R — panel a dumbbells", panel_a_tikz),
           file.path(TEX_DIR, "jointmon-panel-a.tex"), useBytes = TRUE)

# ── Panel b: ROC operating points (variants with FA) + connector lines ──────
panel_b_rows <- list()
panel_b_tikz <- character(0)
# Chance diagonal drawn in TikZ; here emit connectors then marks.
for (i in seq_along(VARIANTS)) {
  vkey <- VARIANTS[[i]]$key
  if (is.null(FA_KEY[[vkey]])) next
  xs <- numeric(0)
  ys <- numeric(0)
  for (arm_spec in ARMS) {
    row <- df_a[df_a$variant_key == vkey & df_a$arm == arm_spec$arm, , drop = FALSE]
    if (nrow(row) == 0 || is.na(row$catch[[1]]) || is.na(row$false_alarm[[1]])) next
    xs <- c(xs, row$false_alarm[[1]])
    ys <- c(ys, row$catch[[1]])
    panel_b_rows[[length(panel_b_rows) + 1]] <- data.frame(
      variant_key = vkey,
      arm = arm_spec$arm,
      gate = arm_spec$gate,
      detector = arm_spec$detector,
      false_alarm = row$false_alarm[[1]],
      catch = row$catch[[1]],
      stringsAsFactors = FALSE
    )
  }
  if (length(xs) >= 2) {
    coords <- paste(sprintf("(%s,%s)", fmt(xs), fmt(ys)), collapse = " ")
    panel_b_tikz <- c(panel_b_tikz, sprintf(
      "\\addplot[gray!50, line width=0.6pt, solid, opacity=0.65, forget plot, mark=none] coordinates {%s};",
      coords))
  }
}
for (arm_spec in ARMS) {
  rows <- df_a[df_a$arm == arm_spec$arm & !is.na(df_a$false_alarm), , drop = FALSE]
  if (nrow(rows) == 0) next
  coords <- paste(sprintf("(%s,%s)", fmt(rows$false_alarm), fmt(rows$catch)), collapse = "\n")
  panel_b_tikz <- c(panel_b_tikz, sprintf(
    "\\addplot[%s, only marks, mark=%s, mark size=2.2pt, mark options={draw=black, line width=0.35pt}, forget plot] coordinates {\n%s\n};",
    arm_spec$col, arm_spec$mark_fill, coords))
}

df_b <- if (length(panel_b_rows)) do.call(rbind, panel_b_rows) else
  data.frame(variant_key = character(), arm = character(), gate = character(),
             detector = character(), false_alarm = numeric(), catch = numeric(),
             stringsAsFactors = FALSE)
write.csv(df_b, file.path(OUT_DIR, "jointmon_panel_b.csv"), row.names = FALSE, quote = FALSE)
writeLines(c("% generated by jointmon.R — panel b operating points", panel_b_tikz),
           file.path(TEX_DIR, "jointmon-panel-b.tex"), useBytes = TRUE)

# ── Panel c: per-cell z_good vs z_defect (G1 exceedance colouring) ──────────
panel_c_rows <- list()
for (config_key in names(res)) {
  for (category in names(res[[config_key]])) {
    cell <- res[[config_key]][[category]]
    zg <- cell$z_good
    zd <- cell$z_defect
    if (is.null(zg) || is.null(zd)) next
    g1_cert <- ifelse(is.null(cell$g1_certified), FALSE, cell$g1_certified)
    escaped <- ifelse(is.null(cell$escaped), 0, cell$escaped)
    exceed <- isTRUE(g1_cert) && escaped > G1_TARGET
    panel_c_rows[[length(panel_c_rows) + 1]] <- data.frame(
      config = config_key,
      category = category,
      z_defect = as.numeric(zd),
      z_good = as.numeric(zg),
      g1_exceed = exceed,
      stringsAsFactors = FALSE
    )
  }
}
df_c <- do.call(rbind, panel_c_rows)
write.csv(df_c, file.path(OUT_DIR, "jointmon_panel_c.csv"), row.names = FALSE, quote = FALSE)

# Split exceed / certified for two compact \addplot coordinate blocks.
ex_c <- df_c[df_c$g1_exceed, , drop = FALSE]
ok_c <- df_c[!df_c$g1_exceed, , drop = FALSE]
chunk_coords <- function(df) {
  if (nrow(df) == 0) return("% (empty)")
  paste(sprintf("(%s,%s)", fmt(df$z_defect), fmt(df$z_good)), collapse = "\n")
}
panel_c_tikz <- c(
  "% generated by jointmon.R — panel c scatter",
  sprintf("\\addplot[black!55, only marks, mark=*, mark size=0.85pt, opacity=0.40, forget plot] coordinates {\n%s\n};",
          chunk_coords(ok_c)),
  sprintf("\\addplot[cFalseAlarm, only marks, mark=*, mark size=0.95pt, opacity=0.55, forget plot] coordinates {\n%s\n};",
          chunk_coords(ex_c))
)
writeLines(panel_c_tikz, file.path(TEX_DIR, "jointmon-panel-c.tex"), useBytes = TRUE)

# ── Panel d: 2×12 catch / false-alarm heatmap by corruption × level ─────────
CORRS <- c("brightness", "contrast", "gaussian", "defocus")
LEVELS <- c("level1", "level2", "level3")
SHORT <- c(brightness = "brig", contrast = "cont", gaussian = "gaus", defocus = "defo")

# Red intensity scale (match historical Reds imshow): light → dark with value.
cell_fill <- function(v) {
  if (is.na(v)) return("black!8")
  pct <- max(8, min(100, round(100 * v)))
  sprintf("cHeat!%d!white", pct)
}
cell_textcol <- function(v) {
  if (is.na(v) || v <= 0.50) "black" else "white"
}

panel_d_rows <- list()
panel_d_tikz <- character(0)
panel_d_tikz <- c(panel_d_tikz, "% generated by jointmon.R — panel d heatmap cells")
for (ci in seq_along(CORRS)) {
  corr <- CORRS[[ci]]
  for (li in seq_along(LEVELS)) {
    lv <- LEVELS[[li]]
    j <- (ci - 1) * length(LEVELS) + (li - 1)  # 0-based column
    ex_cells <- 0L
    ex_hit <- 0L
    ok_cells <- 0L
    ok_hit <- 0L

    for (config_key in names(res)) {
      parts <- strsplit(config_key, "/")[[1]]
      if (length(parts) < 4) next
      if (parts[3] != corr || parts[4] != lv) next
      for (category in names(res[[config_key]])) {
        cell <- res[[config_key]][[category]]
        g1_cert <- ifelse(is.null(cell$g1_certified), FALSE, cell$g1_certified)
        if (!isTRUE(g1_cert)) next
        escaped <- ifelse(is.null(cell$escaped), 0, cell$escaped)
        jm <- isTRUE(cell$joint_max_detected)
        if (escaped > G1_TARGET) {
          ex_cells <- ex_cells + 1L
          if (jm) ex_hit <- ex_hit + 1L
        } else {
          ok_cells <- ok_cells + 1L
          if (jm) ok_hit <- ok_hit + 1L
        }
      }
    }

    catch_rate <- if (ex_cells > 0) ex_hit / ex_cells else NA
    fa_rate <- if (ok_cells > 0) ok_hit / ok_cells else NA
    xlab <- sprintf("%s-%s", SHORT[[corr]], substr(lv, nchar(lv), nchar(lv)))

    panel_d_rows[[length(panel_d_rows) + 1]] <- data.frame(
      corruption = corr,
      level = lv,
      col_idx = j,
      x_label = xlab,
      caught = ex_hit,
      eligible = ex_cells,
      catch_rate = catch_rate,
      fa_caught = ok_hit,
      fa_eligible = ok_cells,
      fa_rate = fa_rate,
      stringsAsFactors = FALSE
    )

    # Row 1 = catch (y=1), row 0 = false alarm (y=0); cell as [j,j+1] x [y,y+1]
    for (row_spec in list(
      list(y = 1, v = catch_rate),
      list(y = 0, v = fa_rate)
    )) {
      v <- row_spec$v
      y <- row_spec$y
      fill <- cell_fill(v)
      tcol <- cell_textcol(v)
      label <- if (is.na(v)) "—" else sprintf("%.2f", v)
      panel_d_tikz <- c(panel_d_tikz,
        sprintf("\\fill[%s] (axis cs:%d,%d) rectangle (axis cs:%d,%d);",
                fill, j, y, j + 1, y + 1),
        sprintf("\\node[font=\\tickfont, text=%s, inner sep=0pt] at (axis cs:%s,%s) {%s};",
                tcol, fmt(j + 0.5), fmt(y + 0.5), label))
    }
  }
}

df_d <- do.call(rbind, panel_d_rows)
write.csv(df_d, file.path(OUT_DIR, "jointmon_panel_d.csv"), row.names = FALSE, quote = FALSE)
writeLines(panel_d_tikz, file.path(TEX_DIR, "jointmon-panel-d.tex"), useBytes = TRUE)

cat(sprintf("wrote jointmon_panel_a.csv: %d rows (+ jointmon-panel-a.tex)\n", nrow(df_a)))
cat(sprintf("wrote jointmon_panel_b.csv: %d rows (+ jointmon-panel-b.tex)\n", nrow(df_b)))
cat(sprintf("wrote jointmon_panel_c.csv: %d rows (+ jointmon-panel-c.tex)\n", nrow(df_c)))
cat(sprintf("wrote jointmon_panel_d.csv: %d rows (+ jointmon-panel-d.tex)\n", nrow(df_d)))
