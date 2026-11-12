"""Serve live SWWU team scores on the local network, scraped from a public Ianseo competition page.

Example:
    uv run live.py "https://www.ianseo.net/Details.php?toId=26450" --port 8080
"""

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "Ianseo"))
sys.path.insert(0, str(ROOT / "Team Score Calculation"))

from calcTeamScore import calculate_teams  # noqa: E402
from liveScoreParser import scrape_live  # noqa: E402
from publishLive import serve  # noqa: E402


def main():
    """Parse arguments and start the live server."""
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("url", help="public Ianseo competition page, e.g. https://www.ianseo.net/Details.php?toId=26450")
    p.add_argument("--port", type=int, default=8080, help="port to serve on (default: 8080)")
    p.add_argument("--interval", type=int, default=60, help="seconds between Ianseo checks (default: 60)")
    p.add_argument("--total-arrows", type=int, default=60, help="arrows each archer shoots in the round (default: 60)")
    p.add_argument("--title", help="page title (default: the competition name from Ianseo)")
    p.add_argument("--subtitle", help="page subtitle (default: place and date from Ianseo)")
    args = p.parse_args()

    def fetch_results():
        """Scrape Ianseo and compute live team rankings."""
        archers, _, meta = scrape_live(args.url)
        return calculate_teams(archers, total_arrows=args.total_arrows), args.title or meta["title"], args.subtitle or meta["subtitle"]

    serve(fetch_results, args.port, args.interval, args.total_arrows)


if __name__ == "__main__":
    main()
