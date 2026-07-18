PDFLATEX := pdflatex -interaction=nonstopmode -halt-on-error
FIGS := fig-crcbaseline fig-categorymap fig-overview
CATBENCH := mvtec visa mpdd
CATTEX := $(addprefix data/categorymap_,$(addsuffix .tex,$(CATBENCH)))

.PHONY: all clean
all: $(addsuffix .pdf,$(FIGS))

# Regenerate the TikZ-readable per-category data lists from the frozen CSVs
# (categorymap_{mvtec,visa,mpdd}.csv, themselves pooled straight out of the
# gate_calibration/v1_*_seed*.json records -- no numeric recomputation here).
$(CATTEX): data/gen_categorymap_tex.py data/categorymap_mvtec.csv data/categorymap_visa.csv data/categorymap_mpdd.csv
	cd data && python3 gen_categorymap_tex.py

fig-categorymap.pdf: fig-categorymap.tex $(CATTEX)
	$(PDFLATEX) fig-categorymap.tex
	$(PDFLATEX) fig-categorymap.tex

fig-crcbaseline.pdf: fig-crcbaseline.tex data/crcbaseline.csv
	$(PDFLATEX) fig-crcbaseline.tex
	$(PDFLATEX) fig-crcbaseline.tex

# Symbolic method-overview schematic (Figure 1) -- no data dependency, TikZ only.
fig-overview.pdf: fig-overview.tex
	$(PDFLATEX) fig-overview.tex

clean:
	rm -f *.aux *.log *.out
	rm -f $(addsuffix .pdf,$(FIGS))
