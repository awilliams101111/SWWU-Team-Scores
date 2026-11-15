"""Publish live SWWU team scores as a web page on the local network.

A background thread calls `fetch_results` every `interval` seconds and keeps the last good result; the
HTTP server (all network interfaces) renders that result as a self-refreshing page. Scraping and
scoring are not done here: `fetch_results` supplies the ranked rows from `calculate_teams`.
"""

import html
import socket
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

LOGO_PATH = Path(__file__).resolve().parent.parent / "Data" / "SWWU Logo.png"
PAGE_REFRESH_SECONDS = 30

CSS = """
* { box-sizing:border-box; }
body { margin:0; background:#fff; color:#333; font-family:Roboto, 'Segoe UI', Arial, sans-serif; font-weight:300; line-height:1.2; }
main { max-width:1100px; margin:0 auto; padding:15px 10px 32px; }
.banner { display:flex; align-items:center; justify-content:space-between; background:#007db3; border-radius:10px; }
.banner img { height:100px; width:100px; object-fit:contain; background:#fff; border-radius:10px; margin:2px; }
.banner div { flex:1 0 0; text-align:center; color:#fff; font-size:18px; padding:0 8px; }
.note { margin:12px 2px 4px; font-size:13px; color:#777; } .err { margin:8px 2px; color:#c52d2f; font-weight:400; }
.scroll { overflow-x:auto; margin-top:10px; }
table { border-collapse:collapse; width:100%; background:#fff; border-radius:10px; overflow:hidden; }
thead tr { background:#007db3; } thead th { color:#fff; font-size:18px; font-weight:300; padding:6px 8px 8px; text-align:left; white-space:nowrap; }
thead tr.title th { text-align:center; padding:6px 8px 2px; }
td { padding:4px 8px; font-size:15px; white-space:nowrap; }
tbody tr:hover td { background:#b1d8f3; }
tbody tr.alt td { background:#e1e0e1; } tbody tr.alt:hover td { background:#b1d8f3; }
td.num, th.num { text-align:right; } td.mid, th.mid { text-align:center; }
td.team { font-weight:400; vertical-align:middle; }
@media (max-width:767px) { .banner img { height:50px; width:50px; } .banner div { font-size:15px; } }
"""


def lan_address():
    """Best-guess LAN IPv4 address of this machine (no traffic is sent)."""
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        try:
            sock.connect(("10.255.255.255", 1))
            return sock.getsockname()[0]
        except OSError:
            return "127.0.0.1"


def _team_table(rows, title):
    """HTML table for one team type.

    Args:
        rows (list[dict]): ranked rows from `calculate_teams(..., total_arrows=N)`.
        title (str): team name shown in the table heading.
    Returns:
        str: HTML. Team cells (position, club, average, total, arrows) span the team's archer rows.
    """
    head = (
        f"<tr class=title><th colspan=11>{html.escape(title)}</th></tr>"
        "<tr><th class=num>Pos.</th><th>Club</th><th>Athletes</th><th class=mid>Div.</th><th class=mid>Class</th>"
        "<th class=num>Arrows</th><th class=num>Score</th><th class=num>Avg</th>"
        "<th class=num>Projected</th><th class=num>Team avg</th><th class=num>Team score</th></tr>"
    )
    body = []
    for n, row in enumerate(rows):
        span = len(row["members"])
        for i, a in enumerate(row["members"]):
            cells = [
                f"<td class=num>{a['arrows']}</td>",
                f"<td class=num>{a['score']}</td>",
                f"<td class=num>{a['score'] / a['arrows']:.2f}</td>",
            ]
            lead = ""
            if i == 0:
                lead = f"<td class='team num' rowspan={span}>{row['rank']}</td><td class=team rowspan={span}>{html.escape(row['club'])}</td>"
            athlete = f"<td>{html.escape(a['name'])}</td><td class=mid>{a['division']}</td><td class=mid>{a['class']}</td>"
            tail = ""
            if i == 0:
                tail = "".join(
                    f"<td class='team num' rowspan={span}>{v}</td>" for v in (f"{row['projected']:.1f}", f"{row['average']:.3f}", row["score"])
                )
            body.append(f"<tr{' class=alt' if n % 2 else ''}>{lead}{athlete}{''.join(cells)}{tail}</tr>")
    return f"<div class=scroll><table><thead>{head}</thead><tbody>{''.join(body)}</tbody></table></div>"


def render_page(results, title, subtitle, updated, error=None, interval=60, total_arrows=60):
    """Render the full live page.

    Args:
        results (dict[str, list[dict]] | None): team name -> ranked rows; None before the first successful fetch.
        title (str): page title.
        subtitle (str): subtitle line.
        updated (float | None): epoch time of the last successful fetch.
        error (str | None): message from the latest failed fetch, shown as a warning.
        interval (int): seconds between fetches, shown to the reader.
        total_arrows (int): arrows each archer shoots in total, shown in the ranking note.
    Returns:
        str: complete HTML document.
    """
    sections = []
    for team, rows in (results or {}).items():
        sections.append(_team_table(rows, team) if rows else f"<p class=note>{html.escape(team)}: No eligible teams.</p>")
    if results is None:
        sections.append("<p class=note>Waiting for the first results...</p>")
    stamp = time.strftime("%H:%M:%S", time.localtime(updated)) if updated else "never"
    warning = f"<p class=err>Could not update from Ianseo ({html.escape(error)}). Showing the last good results.</p>" if error else ""
    logo = "<img src=/logo.png alt=''>" if LOGO_PATH.exists() else "<span></span>"
    return (
        f"<!doctype html><html lang=en><head><meta charset=utf-8><meta name=viewport content='width=device-width,initial-scale=1'>"
        f"<meta http-equiv=refresh content={PAGE_REFRESH_SECONDS}><title>{html.escape(title)} - live team scores</title><style>{CSS}</style></head>"
        f"<body><main><div class=banner>{logo}<div><div>{html.escape(title)}</div><div>{html.escape(subtitle)}</div>"
        f"<div>Live Team Scores</div></div>{logo}</div>"
        f"<p class=note>Ranked by projected score: each archer's average arrow value multiplied up to the {total_arrows} arrows they will shoot, summed over the team. Last updated from Ianseo at {stamp}; "
        f"checked every {interval}s, and Ianseo itself publishes every few minutes.</p>{warning}{''.join(sections)}</main></body></html>"
    )


def serve(fetch_results, port=8080, interval=60, total_arrows=60):
    """Run the live page until interrupted.

    Args:
        fetch_results (Callable[[], tuple[dict, str, str]]): returns (results, title, subtitle), where results is
            `calculate_teams(..., total_arrows=N)` output. Exceptions are caught and shown on the page.
        port (int): TCP port to listen on (all interfaces).
        interval (int): seconds between calls of `fetch_results`.
        total_arrows (int): arrows each archer shoots in total, shown on the page.
    Returns:
        None: blocks serving requests.
    """
    state = {"results": None, "title": "SWWU", "subtitle": "", "updated": None, "error": None}

    def refresh_loop():
        """Fetch repeatedly, keeping the last good results if a fetch fails."""
        while True:
            try:
                results, title, subtitle = fetch_results()
                state.update(results=results, title=title, subtitle=subtitle, updated=time.time(), error=None)
            except Exception as exc:  # network or parse failures must not stop the server
                state["error"] = f"{type(exc).__name__}: {exc}"
                print(f"Update failed: {state['error']}")
            time.sleep(interval)

    class Handler(BaseHTTPRequestHandler):
        """Serves the live page at / and the logo at /logo.png."""

        def do_GET(self):
            """Respond to a GET request."""
            if self.path.split("?")[0] == "/logo.png" and LOGO_PATH.exists():
                body, kind = LOGO_PATH.read_bytes(), "image/png"
            elif self.path.split("?")[0] == "/":
                page = render_page(state["results"], state["title"], state["subtitle"], state["updated"], state["error"], interval, total_arrows)
                body, kind = page.encode("utf-8"), "text/html; charset=utf-8"
            else:
                self.send_error(404)
                return
            self.send_response(200)
            self.send_header("Content-Type", kind)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *args):
            """Silence per-request logging."""

    threading.Thread(target=refresh_loop, daemon=True).start()
    server = ThreadingHTTPServer(("0.0.0.0", port), Handler)
    print(f"Live team scores: http://{lan_address()}:{port}/  (this machine: http://localhost:{port}/). Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("Stopped.")
