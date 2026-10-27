# IEEE paper: C-- (C Minus Minus)

**PDF:** [`C--_IEEE_Paper.pdf`](C--_IEEE_Paper.pdf), a 5-page IEEE two-column conference paper
(`IEEEtran`, US Letter).

*C-- (C Minus Minus): A Statically Checked Imperative Language Achieving Memory Safety by Removal*

| File | Purpose |
|---|---|
| `main.tex` | Paper source (IEEEtran conference format) |
| `references.bib` | Bibliography (IEEEtran style) |
| `examples/` | The C-- programs shown as Listings 1 and 2; the build checks their output |
| `bench/` | Benchmark programs (C-- and hand-written C) and `run_bench.py` |
| `generated/` | Files produced by the build: benchmark table rows and macros, the real compiler diagnostic for Listing 2 |
| `build.sh` | Builds the PDF |

## Building

Requirements: Python 3.10+, GCC, and TeX Live with `IEEEtran`, TikZ and `latexmk`
(Debian/Ubuntu: `texlive-latex-extra texlive-publishers texlive-pictures latexmk`).

```bash
./paper/build.sh           # build the PDF, reusing the committed benchmark results
./paper/build.sh --bench   # re-run the benchmark first (takes about a minute)
```

The build fails if the output of Listing 1 changes or Listing 2 no longer shows the
"did you mean" suggestion, so the paper cannot drift from the implementation. Every
number in Table V and in the performance discussion comes from `generated/`.

To submit to a venue that requires A4 paper, change the first line of `main.tex` to
`\documentclass[conference,a4paper]{IEEEtran}`. For Overleaf, upload the whole
`paper/` folder; `generated/` already contains everything the source needs.
