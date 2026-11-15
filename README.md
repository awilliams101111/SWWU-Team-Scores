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

## Live team scores during the event

Serves a self-refreshing page on the local network, scraped from the public Ianseo competition page (needs internet access on the laptop):

```
uv run live.py "https://www.ianseo.net/Details.php?toId=26450" --port 8080
```

The console prints the address to give archers, e.g. `http://192.168.1.20:8080/`. Archers must be on the same network, and Windows may ask to allow Python through the firewall for private networks on first run. Options: `--interval` (seconds between Ianseo checks, default 60), `--total-arrows`, `--title`, `--subtitle` (default: taken from Ianseo). Stop with Ctrl+C.

Teams use the same rules and the same `SWWU_CLUBS` filter as the final report, but are ranked by projected score: each archer's current average arrow value (score / arrows shot) multiplied up to the arrows they will shoot in total (`--total-arrows`, default 60), summed over the team, so a team with fewer archers ranks correctly. Archers are also chosen for a team by average arrow value, not total score, so an archer from an earlier session with a lower average does not displace one who has shot fewer arrows so far. Arrow counts come from the "After N Arrows (Session: ...)" headings on the Ianseo class result lists, matched to each archer's session in the start list PDF (`ENS.pdf`), which also supplies archer IDs. An archer is counted in the class they actually shot in (the class result list they appear in), even if the start list entered them in another. Archers with no arrows or a zero score are ignored until they score. If Ianseo is unreachable the last good results stay on screen with a warning.

## Club filter and excluding archers

Only the SWWU clubs listed in `SWWU_CLUBS` (club code -> name) in `Team Score Calculation/calcTeamScore.py` count towards team scores. An archer is excluded unless both their Ianseo club code (`Noc` in the export) and club name (`Country`) match an entry, so a different code or name removes them. To add a club or change a name, edit that dictionary.

This is also how to exclude a specific archer from team scores (for example one who shot in two sessions of the same event): edit the club code or club name on their row in the export `.txt` to anything not in `SWWU_CLUBS` (e.g. set the code to `0000`), then rerun.

## Layout

- `Ianseo/parseQualiExport.py` - reads the export
- `Team Score Calculation/calcTeamScore.py` - selects and ranks teams
- `Team Score Calculation/generatePDF.py` - builds the PDF (logo from `Data/SWWU Logo.png`)
- `Ianseo/liveScoreParser.py` - scrapes live results from the public Ianseo page
- `Team Score Calculation/publishLive.py` - serves the live page
- `main.py` - command-line entry point for the final PDF; `live.py` - entry point for the live page
