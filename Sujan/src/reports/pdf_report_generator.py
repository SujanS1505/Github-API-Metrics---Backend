from reportlab.lib.pagesizes import A4
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
)
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
import csv
import os


def read_csv(path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.reader(f))


def styled_table(data):
    table = Table(data, repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2C3E50")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONT", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("BACKGROUND", (0, 1), (-1, -1), colors.whitesmoke),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 10),
        ("TOPPADDING", (0, 0), (-1, 0), 10),
    ]))
    return table


def generate_pdf_report(csv_files, output_pdf):
    doc = SimpleDocTemplate(
        output_pdf,
        pagesize=A4,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36,
    )

    styles = getSampleStyleSheet()
    elements = []

    # Title
    elements.append(Paragraph(
        "<b>GitHub Repository Metrics Report</b>",
        styles["Title"]
    ))
    elements.append(Spacer(1, 20))

    for section, csv_path in csv_files.items():
        if not os.path.exists(csv_path):
            continue

        elements.append(Paragraph(
            f"<b>{section}</b>",
            styles["Heading2"]
        ))
        elements.append(Spacer(1, 10))

        data = read_csv(csv_path)
        elements.append(styled_table(data))
        elements.append(Spacer(1, 25))

    doc.build(elements)
