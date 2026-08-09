#!/usr/bin/env Rscript
# Normalize binding data from frozen JSON to CSV digests for TikZ rendering.
# Outputs: binding_escaped.csv (7 rows), binding_fr.csv (33 rows)

library(jsonlite)

script_arg <- grep("^--file=", commandArgs(), value = TRUE)
script_path <- if (length(script_arg)) sub("^--file=", "", script_arg[[1]]) else "binding.R"
script_dir <- normalizePath(dirname(script_path), mustWork = TRUE)
SRC <- normalizePath(file.path(script_dir, "../../../binding_demo_2026-07-13/results.json"), mustWork = TRUE)
OUT_DIR <- script_dir
TEX_DIR <- normalizePath(file.path(script_dir, "../out"), mustWork = FALSE)
dir.create(TEX_DIR, recursive = TRUE, showWarnings = FALSE)

d <- fromJSON(SRC, simplifyVector = FALSE)

collect <- function(axis) {
  rows <- list()
  for (bench in c("MVTec", "VisA")) {
    binding_key <- paste0(axis, "_binding")
    for (e in d[[bench]][[binding_key]]) {
      rows[[length(rows) + 1]] <- data.frame(
        cell = e$cell,
        bench = bench,
        b1 = e[[paste0("b1_", axis)]],
        gate = e[[paste0("gate_", axis)]],
        deferral = e$gate_deferral,
        stringsAsFactors = FALSE
      )
    }
  }
  df <- do.call(rbind, rows)
  df <- df[order(-df$b1), ]
  df$row_idx <- seq(nrow(df), 1)
  return(df)
}

tex_escape <- function(x) {
  x
}

write_tikz_rows <- function(df, path) {
  rows <- vapply(seq_len(nrow(df)), function(i) {
    bench_tag <- if (identical(df$bench[[i]], "MVTec")) "MV" else "VA"
    sprintf(
      "\\BindingRow{%s}{%s}{%d}{%s}{%s}{%d}",
      format(df$gate[[i]], digits = 16, scientific = FALSE, trim = TRUE),
      format(df$b1[[i]], digits = 16, scientific = FALSE, trim = TRUE),
      df$row_idx[[i]] - 1L,
      tex_escape(df$cell[[i]]),
      bench_tag,
      round(100 * df$deferral[[i]])
    )
  }, character(1))
  writeLines(rows, path, useBytes = TRUE)
}

# Escaped-defect binding (7 rows)
escaped <- collect("escaped")
write.csv(escaped, file.path(OUT_DIR, "binding_escaped.csv"), row.names = FALSE, quote = FALSE)
write_tikz_rows(escaped, file.path(TEX_DIR, "binding-escaped-rows.tex"))
cat(sprintf("wrote binding_escaped.csv: %d rows\n", nrow(escaped)))

# False-reject binding (33 rows)
fr <- collect("fr")
write.csv(fr, file.path(OUT_DIR, "binding_fr.csv"), row.names = FALSE, quote = FALSE)
write_tikz_rows(fr, file.path(TEX_DIR, "binding-fr-rows.tex"))
cat(sprintf("wrote binding_fr.csv: %d rows\n", nrow(fr)))
