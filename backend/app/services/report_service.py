"""Builds the downloadable forecast report (UC5) as CSV or PDF."""
from __future__ import annotations

import csv
import io
from datetime import date

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from app.schemas.schemas import PredictionResponse


def build_csv(prediction: PredictionResponse, historical_rows: list[dict]) -> bytes:
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["Kandumas -- Fish Catch Forecast Report"])
    writer.writerow(["Region", prediction.region])
    writer.writerow(["Species", prediction.species])
    writer.writerow(["Model used", prediction.model_used])
    writer.writerow(["RMSE (kg)", prediction.rmse])
    writer.writerow(["MAPE (%)", prediction.mape])
    writer.writerow([])
    writer.writerow(["-- Forecast --"])
    writer.writerow(["Target month", "Predicted catch (kg)"])
    for p in prediction.points:
        writer.writerow([p.target_month, round(p.predicted_catch_kg, 1)])
    writer.writerow([])
    writer.writerow(["-- Historical --"])
    writer.writerow(["Month", "Catch (kg)", "SST (C)", "Wind speed (m/s)", "Salinity (PSU)"])
    for row in historical_rows:
        writer.writerow([row["month"], round(row["catch_kg"], 1), row.get("sst"), row.get("wind_speed"), row.get("salinity")])
    return buf.getvalue().encode("utf-8")


def build_pdf(prediction: PredictionResponse, historical_rows: list[dict]) -> bytes:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4)
    styles = getSampleStyleSheet()
    story = [
        Paragraph("Kandumas", styles["Title"]),
        Paragraph("Maldives Tuna Catch Forecasting Dashboard", styles["Normal"]),
        Paragraph(f"Report generated: {date.today().isoformat()}", styles["Normal"]),
        Spacer(1, 12),
        Paragraph(f"Region: {prediction.region}", styles["Normal"]),
        Paragraph(f"Species: {prediction.species}", styles["Normal"]),
        Paragraph(f"Model used: {prediction.model_used.upper()}", styles["Normal"]),
        Paragraph(
            f"Accuracy: RMSE = {prediction.rmse:.1f} kg, MAPE = {prediction.mape:.1f}%"
            if prediction.rmse is not None
            else "Accuracy: not yet evaluated",
            styles["Normal"],
        ),
        Spacer(1, 16),
        Paragraph("Forecast", styles["Heading2"]),
    ]

    forecast_table_data = [["Target month", "Predicted catch (kg)"]] + [
        [str(p.target_month), f"{p.predicted_catch_kg:,.1f}"] for p in prediction.points
    ]
    story.append(_styled_table(forecast_table_data))
    story.append(Spacer(1, 16))
    story.append(Paragraph("Recent historical data", styles["Heading2"]))

    hist_table_data = [["Month", "Catch (kg)", "SST (C)", "Wind (m/s)", "Salinity (PSU)"]] + [
        [
            str(row["month"]),
            f"{row['catch_kg']:,.1f}",
            f"{row['sst']:.2f}" if row.get("sst") is not None else "-",
            f"{row['wind_speed']:.2f}" if row.get("wind_speed") is not None else "-",
            f"{row['salinity']:.2f}" if row.get("salinity") is not None else "-",
        ]
        for row in historical_rows[-24:]
    ]
    story.append(_styled_table(hist_table_data))

    doc.build(story)
    return buf.getvalue()


def _styled_table(data: list[list[str]]) -> Table:
    table = Table(data, hAlign="LEFT")
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f6f8b")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f2f2f2")]),
            ]
        )
    )
    return table
