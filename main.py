"""Calculate SWWU team scores from an Ianseo qualification export and write a PDF report.

Example:
    uv run main.py Data/ianseoExports/SWWU26L1.txt --title "SWWU League" --subtitle "Leg 1 - Portsmouth"
"""

import argparse
import re
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "Ianseo"))
sys.path.insert(0, str(ROOT / "Team Score Calculation"))

from calcTeamScore import calculate_teams  # noqa: E402
from generatePDF import generate_pdf  # noqa: E402
from parseQualiExport import parse_quali_export  # noqa: E402


def resolve_output(output, title, date_text):
    """Work out the PDF path.

    Args:
        output (str | None): user-supplied file path or directory, or None for the default folder.
        title (str): report title, used in the default filename.
        date_text (str): report date, used in the default filename.
    Returns:
        Path: a .pdf path. The default name is "<title> <date>.pdf" with illegal filename characters removed.
    """
    name = re.sub(r'[<>:"/\\|?*]', "", f"{title} {date_text}").strip() + ".pdf"
    if output is None:
        return ROOT / "Data" / "Team Score Reports" / name
    path = Path(output)
    return path if path.suffix.lower() == ".pdf" else path / name


def main():
    """Parse arguments, calculate team scores and write the PDF."""
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("input", help="path or URL of the Ianseo qualification export (.txt)")
    p.add_argument("--title", required=True, help="report title")
    p.add_argument("--subtitle", required=True, help="report subtitle")
    p.add_argument("--date", default=date.today().strftime("%d %B %Y"), help="report date (default: today)")
    p.add_argument(
        "--tiebreak",
        help='comma-separated export column names in priority order, e.g. "Hits,10,9" '
        "(default: all columns from Hits up to Category Rank)",
    )
    p.add_argument("--output", help="output PDF path, or a directory (default: Data/Team Score Reports)")
    p.add_argument("--notes", default="", help="optional footer notes shown on every page")
    args = p.parse_args()

    tb = [c.strip() for c in args.tiebreak.split(",")] if args.tiebreak else None
    archers, tb_names = parse_quali_export(args.input, tb)
    results = calculate_teams(archers)
    out = resolve_output(args.output, args.title, args.date)
    print(f"Wrote {generate_pdf(results, tb_names, out, args.title, args.subtitle, args.date, args.notes)}")


if __name__ == "__main__":
    main()
