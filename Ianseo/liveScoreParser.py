"""Scrape live qualification results from a public Ianseo competition page into archer records.

Data sources on the public competition page (https://www.ianseo.net/Details.php?toId=<id>):
  - Individual class result lists (IQ<division><experience><gender>.php): name, club code + name,
    score, tie-break columns, and the heading "After N Arrows (Session: ...)". The class a list is for is the
    class the archer actually shot in.
  - Start list by session (ENS.pdf): archer ID (Bib), session, club code and the class each archer was entered in.

The archer dicts match `parse_quali_export` and add `id`, `arrows` (arrows shot so far) and `session`.
Class results carry no IDs, so an archer is linked to their start list entry by (name, club code).
"""

import io
import re
import urllib.request
from urllib.parse import urljoin, urlparse

from lxml import html
from pypdf import PdfReader

USER_AGENT = "Mozilla/5.0 (SWWU team score viewer)"
CLASS_LINK = re.compile(r"/TourData/(\d{4})/(\d+)/(IQ([RCBL])([ENA])([OWF]))\.php")
HEADING_ARROWS = re.compile(r"After\s+(\d+)\s+Arrows(?:\s*\(Sessions?:\s*([\d,\s]+)\))?", re.I)


def fetch(url, timeout=20):
    """Download a page as text.

    Args:
        url (str): page URL.
        timeout (float): seconds before giving up.
    Returns:
        str: decoded HTML.
    """
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read().decode("utf-8", errors="replace")


def fetch_bytes(url, timeout=20):
    """Download a file as bytes (same arguments as `fetch`)."""
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read()


def _text(element):
    """Whitespace-normalised text of an lxml element (non-breaking spaces become spaces)."""
    return re.sub(r"\s+", " ", element.text_content().replace("\xa0", " ")).strip()


def _split_club(country_text):
    """Split an Ianseo country cell such as "1342 - Bath" into (code, name)."""
    code, _, name = country_text.partition(" - ")
    return code.strip(), name.strip()


def _format_name(ianseo_name):
    """Convert Ianseo's "FAMILY Given" to "Given FAMILY" (family name = the upper-case leading words)."""
    words = ianseo_name.split()
    split = next((i for i, w in enumerate(words) if not w.isupper()), len(words))
    return " ".join(words[split:] + words[:split]) if 0 < split < len(words) else ianseo_name


def _parse_headings(title):
    """Extract the arrow counts in a class heading.

    Args:
        title (str): e.g. "Recurve Experienced Open [After 60 Arrows (Session: 1, 2, 3)]".
    Returns:
        list[tuple[int, set[int] | None]]: (arrows shot, sessions it applies to). Sessions is None
            when the heading names no session.
    """
    found = []
    for arrows, sessions in HEADING_ARROWS.findall(title):
        found.append((int(arrows), {int(s) for s in re.findall(r"\d+", sessions)} or None))
    return found


def arrows_for(sessions, headings):
    """Arrows shot by an archer, from the heading arrow counts and the archer's session.

    Args:
        sessions (set[int]): sessions the archer is entered in (empty if unknown).
        headings (list[tuple[int, set[int] | None]]): output of `_parse_headings`.
    Returns:
        int: arrows from the heading naming the archer's session; else the heading that names no session;
            else the largest heading count; 0 if there are no headings.
    """
    for arrows, heading_sessions in headings:
        if heading_sessions and sessions & heading_sessions:
            return arrows
    for arrows, heading_sessions in headings:
        if heading_sessions is None:
            return arrows
    return max((a for a, _ in headings), default=0)


def parse_class_page(page_html):
    """Parse one class result list.

    Args:
        page_html (str): HTML of an IQ<class>.php page.
    Returns:
        tuple[str, list[str], list[dict]]: heading text, tie-break column names (columns after "Tot."),
            and one dict per archer with name, club_code, club, score, tiebreaks (tuple[int, ...]).
    """
    doc = html.fromstring(page_html)
    table = doc.xpath("//table")[0]
    title = _text(table.xpath(".//th")[0])
    headers = [_text(th) for th in table.xpath(".//thead/tr[2]/th")]
    tot = headers.index("Tot.")
    tb_names = [h for h in headers[tot + 1 :] if h]
    rows = []
    for tr in table.xpath(".//tr[contains(@class,'compressed-group')]"):
        cells = [_text(td) for td in tr.xpath("./td")]
        code, club = _split_club(cells[headers.index("Country")])

        def number(i):
            """Integer in cell i, 0 if blank."""
            return int(cells[i]) if cells[i].isdigit() else 0

        rows.append(
            {
                "name": _format_name(cells[headers.index("Athlete")]),
                "ianseo_name": cells[headers.index("Athlete")],
                "club_code": code,
                "club": club,
                "score": number(tot),
                "tiebreaks": tuple(number(tot + 1 + i) for i in range(len(tb_names))),
            }
        )
    return title, tb_names, rows


START_ENTRY = re.compile(r"^(?:\d+\s+)?[A-Z]\s+(\d+)\s+(.+?)\s+(\d{4})\s+.+?\s+([ENA][OWF])\s+([RCBL])\b")


def parse_start_list(pdf_bytes):
    """Parse the start list PDF (ENS.pdf) into entries.

    Args:
        pdf_bytes (bytes): contents of the PDF.
    Returns:
        dict[tuple[str, str], list[dict]]: (Ianseo name "FAMILY Given", club code) -> entries, each with
            id (str, the Bib), category (e.g. "REO": division + class entered in) and session (int | None).
    """
    entries = {}
    session = None
    for page in PdfReader(io.BytesIO(pdf_bytes)).pages:
        for line in page.extract_text().splitlines():
            heading = re.match(r"Session\s+(\d+)\b", line)
            if heading:
                session = int(heading.group(1))
                continue
            entry = START_ENTRY.match(line.strip())
            if entry:
                bib, name, code, klass, division = entry.groups()
                entries.setdefault((name, code), []).append({"id": bib, "category": division + klass, "session": session})
    return entries


def match_entry(entries, category):
    """Choose the start list entry for an archer who shot in `category`.

    Args:
        entries (list[dict]): the archer's start list entries (may be empty).
        category (str): class actually shot in, e.g. "REO".
    Returns:
        tuple[str | None, set[int]]: ID and sessions. Entries in the class shot are preferred; if the archer
            shot in a different class from the one entered, all their entries are used.
    """
    same_class = [e for e in entries if e["category"] == category]
    chosen = same_class or entries
    return (chosen[0]["id"] if chosen else None), {e["session"] for e in chosen if e["session"] is not None}


def scrape_live(details_url):
    """Scrape the current qualification results of a competition from its public Ianseo page.

    Args:
        details_url (str): e.g. "https://www.ianseo.net/Details.php?toId=26450".
    Returns:
        tuple[list[dict], list[str], dict]: archers (as `parse_quali_export`, plus `id`, `arrows` and
            `session`), tie-break column names, and metadata with `title` and `subtitle` from the page header.
    """
    details = fetch(details_url)
    doc = html.fromstring(details)
    header = [_text(d) for d in doc.xpath("//div[@class='results-header-center']/div")]
    meta = {"title": header[0] if header else "", "subtitle": header[2] if len(header) > 2 else ""}

    classes = {}
    for href in doc.xpath("//a/@href"):
        match = CLASS_LINK.search(href)
        if match:
            classes[match.group(3)[2:]] = urljoin(details_url, urlparse(href).path)
    start_link = next((urljoin(details_url, urlparse(h).path) for h in doc.xpath("//a/@href") if h.split("?")[0].endswith("/ENS.pdf")), None)
    start_list = parse_start_list(fetch_bytes(start_link)) if start_link else {}

    archers, tb_names = [], []
    for category, url in sorted(classes.items()):
        title, tb_names, rows = parse_class_page(fetch(url))
        headings = _parse_headings(title)
        division, experience, gender = category[0], category[1], "F" if category[2] in "WF" else "O"
        for row in rows:
            archer_id, archer_sessions = match_entry(start_list.get((row.pop("ianseo_name"), row["club_code"]), []), category)
            archers.append(
                {
                    **row,
                    "id": archer_id,
                    "division": division,
                    "experience": experience,
                    "gender": gender,
                    "class": f"{experience}{gender}",
                    "session": min(archer_sessions) if archer_sessions else None,
                    "arrows": arrows_for(archer_sessions, headings),
                }
            )
    return archers, tb_names, meta
