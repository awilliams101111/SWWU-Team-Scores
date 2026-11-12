# SWWU Team Scores

Calculates SWWU league team scores (Sighted, Unsighted, Novice; see `Team Score Calculation/TeamSpec.md`) from an Ianseo qualification export and writes an Ianseo-style PDF report.

## Running

0. Install [`uv` python package manager](https://docs.astral.sh/uv/getting-started/installation/)
1. Install dependencies once from the repo root: `uv sync`
2. Export the qualification results from Ianseo as a semicolon-delimited `.txt` and save it in `Data/ianseoExports/`.
3. Run from the repo root:

```
uv run main.py Data/ianseoExports/SWWU26L1.txt --title "SWWU 2026 Indoor Championship" --subtitle "Leg 6, University of Exeter"
```

The PDF is saved to `Data/Team Score Reports/<title> <date>.pdf`.

| Argument | Required | Description |
|---|---|---|
| `input` | yes | Path (or URL) of the Ianseo export |
| `--title` | yes | Report title |
| `--subtitle` | yes | Report subtitle |
| `--date` | no | Date shown in the header and filename. Default: today, e.g. `12 November 2026` |
| `--output` | no | Output `.pdf` path, or a directory (the default filename is then used) |
| `--notes` | no | Footer notes printed on every page, to clarify results. Blank by default |
| `--tiebreak` | no | Export column names in tie-break priority order, comma separated, e.g. `"Hits,10,9"`. Default: every column from `Hits` up to `Category Rank` |

Example with all options:

```
uv run main.py Data/ianseoExports/SWWU26L1.txt --title "SWWU League" --subtitle "Leg 1" --date "07 March 2026" --output "C:/Reports" --notes "Bath score corrected after recount." --tiebreak "Hits,10,9"
```

Quote any argument containing spaces. Team ties are broken by the tie-break columns summed over the team, in order; teams still level share a rank.

## Layout

- `Ianseo/parseQualiExport.py` - reads the export
- `Team Score Calculation/calcTeamScore.py` - selects and ranks teams
- `Team Score Calculation/generatePDF.py` - builds the PDF (logo from `Data/SWWU Logo.png`)
- `main.py` - command-line entry point
