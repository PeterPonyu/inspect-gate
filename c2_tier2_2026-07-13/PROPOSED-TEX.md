# Proposed TeX for later integration (NOT applied — a polish agent owns paper.tex)

Drop-in replacements for the `\todo{}` scaffolds already in paper.tex. Confirmatory-vs-one-shot
status is stated inline. **MVTec = confirmatory family; VisA = post-freeze exploratory** — do not
merge them. Verify counts against `c2_*.json` / `tier2_*.json` before committing.

---

## 1. Confirmatory audit family (C2) — fills the paper.tex "Confirmatory audit family (C2)" \todo

```latex
\subsection{Confirmatory audit verdict (C2)}
The confirmatory family is the four tests $\{\text{B1 fixed},\text{B2 tuned}\}\times\{\text{PatchCore},\text{Dinomaly}\}$;
B3 (train-good quantile) is dropped for want of a held-out train-good score pool, the degradation
$6\!\to\!4$ preregistered in the frozen amendment set. For each (practice, backbone) we pool the
$15$ MVTec categories into one evaluation half (repeat-$0$ split), fit B1 on the pooled calibration
half and B2 per category, and test the excess area under the risk--coverage curve against the
closed-form random-deferral null with a matched-abstention permutation test ($n_{\text{perm}}=2000$,
strata $=$ category) and a category-blocked bootstrap CI. Every one of the four tests rejects the
random-deferral null at the permutation floor $p=1/2001=5\times10^{-4}$ (Holm-adjusted $p=2\times10^{-3}$)
in \emph{all five} backbone seeds, with pooled excess-AURC in $[0.024,0.050]$ and every bootstrap CI
excluding zero. The per-seed four-member Holm verdict is confirmatory; a single cross-seed rollup
(seed-max of the per-seed $p$-values) is a post-freeze one-shot convenience and is moot here, as the
verdict is identical under seed-min, seed-median, and seed-max. \textbf{The constructive arm of C2
publishes: field-standard threshold practice earns deferral skill over honest random deferral.} This
is the higher-powered pooled counterpart of the per-category exploratory audit above, which the
saturated MVTec backbones render mixed at the single-category level.
```

## 2. VisA exploratory audit note (keep separate from the confirmatory family)

```latex
On VisA (post-freeze, exploratory), the same pooled construction rejects the random-deferral null in
all four practice$\times$backbone tests across all five seeds (Holm $p=2\times10^{-3}$), with larger
pooled excess-AURC $[0.044,0.106]$ --- the headroom the near-saturated MVTec backbones deny. These
VisA tests are exploratory and are not part of the MVTec confirmatory Holm family.
```

## 3. V1 tier-2 verdict (A1/A2/A3) — fills the paper.tex "V1 tier-2 as a verdict" \todo

```latex
\subsection{V1 tier-2 verdict}
Under the frozen amendments the tier-2 power floor is per repeat, not pooled over repeats. On MVTec
the escaped-defect axis is per-repeat powered in $13/15$ categories (underpowered in toothbrush and
transistor, $n_{\text{eval,def}}=15,20<22$). Graded on a per-repeat one-sided $95\%$
Clopper--Pearson upper bound against the $0.13$ threshold, the powered cells overwhelmingly fail
($115/130$ cells; the $15$ passes are the near-zero-miss cells cable and hazelnut). This is the
preregistered expectation of amendment~A2, not a certificate failure: split conformal targets
$\alpha_{\text{miss}}$ exactly, so a one-sided CP upper bound at a per-repeat $n\!\approx\!30$--$70$
sits well above the target plus a $3$pp tolerance whenever the realized miss rate is near the target.
The certificate-validity statistic is tier-1, which passes in all $150$ MVTec cells; tier-2 is
reported as a stringent estimator-variance readout. The tier-2 false-reject axis is
\emph{structurally ungraded} on MVTec: it is evaluated only over G2-certified categories
(amendment~A3), and those four (cable, hazelnut, screw, transistor) are themselves per-repeat
underpowered ($n_{\text{eval,good}}\le 30<36$), so $0/150$ cells are gradeable --- exactly the
amendment A1$+$A3 outcome. The largest MVTec per-repeat eval-good count is $30$, below the required
$36$; no MVTec category can support a tier-2 false-reject check under the primary protocol.
```

## 4. Table T-audit (C2) — drop-in

```latex
\begin{table}[t]\centering
\caption{Confirmatory pooled excess-AURC audit (C2). Family $=\{$B1,B2$\}\times\{$PatchCore,Dinomaly$\}$;
Holm $\alpha=0.05$. All tests reject in every seed; per-seed values are the frozen confirmatory verdict.}
\label{tab:c2}
\begin{tabular}{llccc}
\toprule
Backbone & Practice & excess-AURC (seed range) & perm.\ $p$ & Holm $p$ / reject \\
\midrule
PatchCore & B1 fixed & $0.023$--$0.030$ & $5\times10^{-4}$ & $2\times10^{-3}$ / \checkmark \\
PatchCore & B2 tuned & $0.036$--$0.046$ & $5\times10^{-4}$ & $2\times10^{-3}$ / \checkmark \\
Dinomaly  & B1 fixed & $0.045$--$0.050$ & $5\times10^{-4}$ & $2\times10^{-3}$ / \checkmark \\
Dinomaly  & B2 tuned & $0.027$--$0.035$ & $5\times10^{-4}$ & $2\times10^{-3}$ / \checkmark \\
\midrule
\multicolumn{5}{l}{\footnotesize Verdict: constructive arm. All four reject in all 5 seeds; CIs exclude 0.}\\
\bottomrule
\end{tabular}
\end{table}
```

## 5. Table T3 (tier-2 verdict, MVTec) — drop-in

```latex
\begin{table}[t]\centering
\caption{V1 tier-2 grading on MVTec under amendments A1/A2/A3 (150 cells $=15\times2\times5$).}
\label{tab:tier2}
\begin{tabular}{lccc}
\toprule
Axis & pass & fail & excluded \\
\midrule
Escaped-defect & $15$ & $115$ & $20$ underpowered (toothbrush, transistor) \\
False-reject   & $0$  & $0$   & $110$ G2-refused $+$ $40$ underpowered \\
\midrule
\multicolumn{4}{l}{\footnotesize Tier-1 passes $150/150$; tier-2 escaped fails are the A2-expected}\\
\multicolumn{4}{l}{\footnotesize variance readout, not certificate failures. False-reject structurally ungraded.}\\
\bottomrule
\end{tabular}
\end{table}
```

---

### Status labels for the writer

- **Table T-audit / C2 subsection:** MVTec = **confirmatory** (frozen per-seed construction);
  the single cross-seed rollup line is **one-shot post-freeze** but moot. VisA = **exploratory**.
- **Table T3 / tier-2 subsection:** power partition and false-reject buckets are **exact**; the
  escaped pass/fail split (15/115) uses a **per-repeat CP UB reconstruction** from cached pooled
  summaries — label it as such, and lead with tier-1's 150/150 pass.
