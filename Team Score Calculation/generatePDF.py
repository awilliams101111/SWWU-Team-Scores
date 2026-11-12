"""Generate an Ianseo-style PDF report of SWWU team scores."""

from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.platypus import BaseDocTemplate, Frame, PageBreak, PageTemplate, Paragraph, Spacer, Table, TableStyle

LOGO_PATH = Path(__file__).resolve().parent.parent / "Data" / "SWWU Logo.png"
HEADER_HEIGHT = 32 * mm
PAGE_MARGIN = 15 * mm
TABLE_WIDTH = A4[0] - 2 * PAGE_MARGIN
FONT_SIZE = 10
CELL_PAD = 4  # points, left and right
LONGEST_CLUB = "Aberystwyth"


def _make_page_decorator(title, subtitle, date_text, notes_para=None):
    """Build the per-page header/footer drawing function.

    Args:
        title (str): main report title.
        subtitle (str): report subtitle.
        date_text (str): date string shown in the header.
        notes_para (Paragraph | None): footer notes drawn bottom-left on every page.
    Returns:
        Callable: reportlab onPage callback (canvas, doc) drawing logos, titles, date, page number and notes.
    """

    def draw(canvas, doc):
        """Draw the header (logos, titles, date), page number and optional notes on one page."""
        width, height = A4
        canvas.saveState()
        if LOGO_PATH.exists():
            canvas.drawImage(str(LOGO_PATH), 15 * mm, height - 28 * mm, 22 * mm, 22 * mm, mask="auto")
            canvas.drawImage(str(LOGO_PATH), width - 37 * mm, height - 28 * mm, 22 * mm, 22 * mm, mask="auto")
        canvas.setFont("Helvetica-Bold", 16)
        canvas.drawCentredString(width / 2, height - 14 * mm, title)
        canvas.setFont("Helvetica", 11)
        canvas.drawCentredString(width / 2, height - 21 * mm, subtitle)
        canvas.setFont("Helvetica", 9)
        canvas.drawCentredString(width / 2, height - 27 * mm, date_text)
        canvas.setStrokeColor(colors.black)
        canvas.line(15 * mm, height - 30 * mm, width - 15 * mm, height - 30 * mm)
        canvas.setFont("Helvetica", 8)
        canvas.drawRightString(width - 15 * mm, 8 * mm, f"Page {doc.page}")
        if notes_para is not None:
            notes_para.wrap(width - 60 * mm, 40 * mm)
            notes_para.drawOn(canvas, 15 * mm, 8 * mm)
        canvas.restoreState()

    return draw


def _team_table(rows, tb_names):
    """Build the table for one team type, with one sub-row per archer in each team.

    Args:
        rows (list[dict]): ranked team rows from `calculate_teams` (rank, club, members, score, tiebreaks).
        tb_names (list[str]): tie-break column names used as headers.
    Returns:
        Table: columns Pos, Club, Athlete, Div, Class, Score (individual), Total, then team
            tie-break totals. Pos, Club, Total and tie-break cells span the team's archer rows.
    """
    n_tb = len(tb_names)
    last = 6 + n_tb
    data = [["Pos.", "Club", "Athletes", "Div.", "Class", "Score", "Total", *tb_names]]
    styles = [
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#dddddd")),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), FONT_SIZE),
        ("LEFTPADDING", (0, 0), (-1, -1), CELL_PAD),
        ("RIGHTPADDING", (0, 0), (-1, -1), CELL_PAD),
        ("ALIGN", (3, 0), (4, -1), "CENTER"),
        ("ALIGN", (5, 0), (-1, -1), "RIGHT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("BOX", (0, 0), (-1, -1), 0.8, colors.black),
        ("INNERGRID", (2, 1), (5, -1), 0.25, colors.lightgrey),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ]
    for row in rows:
        r0 = len(data)
        for i, a in enumerate(row["members"]):
            first = i == 0
            data.append(
                [
                    row["rank"] if first else "",
                    row["club"] if first else "",
                    a["name"],
                    a["division"],
                    a["class"],
                    a["score"],
                    row["score"] if first else "",
                    *(t if first else "" for t in row["tiebreaks"]),
                ]
            )
        r1 = len(data) - 1
        styles.append(("LINEABOVE", (0, r0), (-1, r0), 0.8, colors.black))
        styles.append(("FONTNAME", (0, r0), (1, r0), "Helvetica-Bold"))
        styles.append(("FONTNAME", (6, r0), (6, r0), "Helvetica-Bold"))
        if r1 > r0:
            for c in (0, 1, *range(6, last + 1)):
                styles.append(("SPAN", (c, r0), (c, r1)))
    def fit(text, bold=True):
        """Column width in points needed for `text` plus cell padding."""
        font = "Helvetica-Bold" if bold else "Helvetica"
        return stringWidth(text, font, FONT_SIZE) + 2 * CELL_PAD

    fixed = [
        fit("Pos."),
        fit(LONGEST_CLUB),
        None,  # athlete name takes the remaining width
        fit("Div."),
        fit("Class"),
        fit("Score"),  # individual scores are under 1000, narrower than the header
        fit("9999"),  # team total is under 10000; header "Total" is narrower
        *(max(fit(name), fit("999")) for name in tb_names),
    ]
    fixed[6] = max(fixed[6], fit("Total"))
    name_width = TABLE_WIDTH - sum(w for w in fixed if w is not None)
    widths = [name_width if w is None else w for w in fixed]
    table = Table(data, colWidths=widths, repeatRows=1, hAlign="LEFT")
    table.setStyle(TableStyle(styles))
    return table


def generate_pdf(results, tb_names, output_path, title, subtitle, date_text, notes=""):
    """Write the team score report.

    Args:
        results (dict[str, list[dict]]): team name -> ranked rows from `calculate_teams`.
        tb_names (list[str]): tie-break column names, in priority order.
        output_path (str | Path): PDF file to write (parent directory is created).
        title (str): report title.
        subtitle (str): report subtitle.
        date_text (str): date shown in the header.
        notes (str): optional footer notes shown on every page; blank for none.
    Returns:
        Path: the written PDF path.
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    doc = BaseDocTemplate(str(output_path), pagesize=A4, title=f"{title} - {subtitle}")
    notes_para, notes_h = None, 0
    if notes.strip():
        notes_para = Paragraph(notes.replace("\n", "<br/>"), ParagraphStyle("notes", fontSize=8, leading=10))
        _, notes_h = notes_para.wrap(A4[0] - 60 * mm, 40 * mm)
    bottom = 15 * mm + (notes_h + 4 * mm if notes_h else 0)
    frame = Frame(
        PAGE_MARGIN, bottom, TABLE_WIDTH, A4[1] - bottom - HEADER_HEIGHT - 5 * mm, id="body",
        leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0,
    )
    decorator = _make_page_decorator(title, subtitle, date_text, notes_para)
    doc.addPageTemplates([PageTemplate(id="main", frames=[frame], onPage=decorator)])

    heading = ParagraphStyle("heading", parent=getSampleStyleSheet()["Heading2"], spaceAfter=6, leftIndent=0, firstLineIndent=0)
    story = []
    for i, (team_name, rows) in enumerate(results.items()):
        if i:
            story.append(PageBreak())
        story.append(Paragraph(team_name, heading))
        story.append(_team_table(rows, tb_names) if rows else Paragraph("No eligible teams.", getSampleStyleSheet()["Normal"]))
        story.append(Spacer(1, 4 * mm))
    doc.build(story)
    return output_path
