"""Generate an Ianseo-style PDF report of SWWU team scores."""

from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import BaseDocTemplate, Frame, PageBreak, PageTemplate, Paragraph, Spacer, Table, TableStyle

LOGO_PATH = Path(__file__).resolve().parent.parent / "Data" / "SWWU Logo.png"
HEADER_HEIGHT = 32 * mm


def _make_page_decorator(title, subtitle, date_text):
    """Build the per-page header drawing function.

    Args:
        title (str): main report title.
        subtitle (str): report subtitle.
        date_text (str): date string shown in the header.
    Returns:
        Callable: reportlab onPage callback (canvas, doc) that draws logo, titles and page number.
    """

    def draw(canvas, doc):
        """Draw the header and footer on one page."""
        width, height = A4
        canvas.saveState()
        if LOGO_PATH.exists():
            canvas.drawImage(str(LOGO_PATH), 15 * mm, height - 28 * mm, 22 * mm, 22 * mm, mask="auto")
        canvas.setFont("Helvetica-Bold", 16)
        canvas.drawCentredString(width / 2, height - 14 * mm, title)
        canvas.setFont("Helvetica", 11)
        canvas.drawCentredString(width / 2, height - 21 * mm, subtitle)
        canvas.drawRightString(width - 15 * mm, height - 14 * mm, date_text)
        canvas.setStrokeColor(colors.black)
        canvas.line(15 * mm, height - 30 * mm, width - 15 * mm, height - 30 * mm)
        canvas.setFont("Helvetica", 8)
        canvas.drawRightString(width - 15 * mm, 10 * mm, f"Page {doc.page}")
        canvas.restoreState()

    return draw


def _team_table(rows, tb_names):
    """Build the table for one team type.

    Args:
        rows (list[dict]): ranked team rows from `calculate_teams` (rank, club, members, score, tiebreaks).
        tb_names (list[str]): tie-break column names used as headers.
    Returns:
        Table: reportlab table with a club row then one row per member.
    """
    header = ["Rank", "Team / Archer", "Score", *tb_names]
    data = [header]
    styles = [
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#dddddd")),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("ALIGN", (2, 0), (-1, -1), "RIGHT"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]
    for row in rows:
        r = len(data)
        data.append([row["rank"], row["club"], row["score"], *row["tiebreaks"]])
        styles += [("FONTNAME", (0, r), (-1, r), "Helvetica-Bold"), ("LINEABOVE", (0, r), (-1, r), 0.5, colors.grey)]
        for a in row["members"]:
            data.append(["", f"    {a['name']}", a["score"], *a["tiebreaks"]])
    widths = [15 * mm, 70 * mm, 22 * mm] + [18 * mm] * len(tb_names)
    table = Table(data, colWidths=widths, repeatRows=1)
    table.setStyle(TableStyle(styles))
    return table


def generate_pdf(results, tb_names, output_path, title, subtitle, date_text):
    """Write the team score report.

    Args:
        results (dict[str, list[dict]]): team name -> ranked rows from `calculate_teams`.
        tb_names (list[str]): tie-break column names, in priority order.
        output_path (str | Path): PDF file to write (parent directory is created).
        title (str): report title.
        subtitle (str): report subtitle.
        date_text (str): date shown in the header.
    Returns:
        Path: the written PDF path.
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    doc = BaseDocTemplate(str(output_path), pagesize=A4, title=f"{title} - {subtitle}")
    frame = Frame(15 * mm, 15 * mm, A4[0] - 30 * mm, A4[1] - 15 * mm - HEADER_HEIGHT - 5 * mm, id="body")
    doc.addPageTemplates([PageTemplate(id="main", frames=[frame], onPage=_make_page_decorator(title, subtitle, date_text))])

    heading = ParagraphStyle("heading", parent=getSampleStyleSheet()["Heading2"], spaceAfter=6)
    story = []
    for i, (team_name, rows) in enumerate(results.items()):
        if i:
            story.append(PageBreak())
        story.append(Paragraph(team_name, heading))
        story.append(_team_table(rows, tb_names) if rows else Paragraph("No eligible teams.", getSampleStyleSheet()["Normal"]))
        story.append(Spacer(1, 4 * mm))
    doc.build(story)
    return output_path
