"""
export_utils.py - Export-funktioner för Teammanager
Hanterar export till CSV och PDF.
"""

import pandas as pd
import io
from datetime import date
from database import hamta_allokeringar, hamta_all_personal, hamta_alla_projekt, hamta_kompetenser
from calendar_utils import hamta_arbetsdagar


def exportera_allokeringar_csv(fran_datum, till_datum):
    """
    Exportera allokeringsdata som CSV.
    Returnerar en bytes-buffer redo för nedladdning.
    """
    allokeringar = hamta_allokeringar(fran_datum=fran_datum, till_datum=till_datum)

    if not allokeringar:
        df = pd.DataFrame(columns=["Personal", "Projekt", "Datum", "Timmar"])
    else:
        df = pd.DataFrame(allokeringar)
        df = df[["personal_namn", "projekt_namn", "datum", "timmar"]].rename(columns={
            "personal_namn": "Personal",
            "projekt_namn": "Projekt",
            "datum": "Datum",
            "timmar": "Timmar"
        })

    buffer = io.BytesIO()
    df.to_csv(buffer, index=False, encoding="utf-8-sig", sep=";")
    buffer.seek(0)
    return buffer.getvalue()


def exportera_personal_csv():
    """Exportera personalregister som CSV."""
    personal = hamta_all_personal(bara_aktiva=False)

    rows = []
    for p in personal:
        kompetenser = hamta_kompetenser(p["id"])
        rows.append({
            "Namn": p["namn"],
            "Roll": p["roll"],
            "Kapacitet (h/dag)": p["kapacitet_h"],
            "Aktiv": "Ja" if p["aktiv"] else "Nej",
            "Kompetenser": ", ".join(kompetenser),
            "Skapad": p["skapad_datum"]
        })

    df = pd.DataFrame(rows)
    buffer = io.BytesIO()
    df.to_csv(buffer, index=False, encoding="utf-8-sig", sep=";")
    buffer.seek(0)
    return buffer.getvalue()


def exportera_belaggningsrapport_csv(fran_datum, till_datum):
    """
    Exportera beläggningsrapport per person som CSV.
    Visar tillgängliga timmar, allokerade timmar, beläggningsgrad.
    """
    personal = hamta_all_personal()
    arbetsdagar = hamta_arbetsdagar(fran_datum, till_datum)
    antal_dagar = len(arbetsdagar)

    rows = []
    for p in personal:
        allokeringar = hamta_allokeringar(
            personal_id=p["id"], fran_datum=fran_datum, till_datum=till_datum
        )
        allokerade = sum(a["timmar"] for a in allokeringar)
        tillgangliga = antal_dagar * p["kapacitet_h"]
        belaggning = (allokerade / tillgangliga * 100) if tillgangliga > 0 else 0

        rows.append({
            "Personal": p["namn"],
            "Roll": p["roll"],
            "Arbetsdagar": antal_dagar,
            "Kapacitet (h/dag)": p["kapacitet_h"],
            "Tillgangliga timmar": tillgangliga,
            "Allokerade timmar": round(allokerade, 1),
            "Belaggning %": round(belaggning, 1)
        })

    df = pd.DataFrame(rows)
    buffer = io.BytesIO()
    df.to_csv(buffer, index=False, encoding="utf-8-sig", sep=";")
    buffer.seek(0)
    return buffer.getvalue()


def generera_pdf_rapport(fran_datum, till_datum):
    """
    Generera en PDF-rapport med beläggningsöversikt.
    Returnerar bytes-buffer.
    """
    from fpdf import FPDF

    personal = hamta_all_personal()
    arbetsdagar = hamta_arbetsdagar(fran_datum, till_datum)
    antal_dagar = len(arbetsdagar)

    pdf = FPDF()
    pdf.add_page()

    # Titel
    pdf.set_font("Helvetica", "B", 18)
    pdf.cell(0, 15, "Teammanager - Belaggningsrapport", ln=True, align="C")

    # Period
    pdf.set_font("Helvetica", "", 11)
    pdf.cell(0, 8, f"Period: {fran_datum} till {till_datum}", ln=True, align="C")
    pdf.cell(0, 8, f"Antal arbetsdagar: {antal_dagar}", ln=True, align="C")
    pdf.ln(10)

    # Tabell-rubrik
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_fill_color(52, 152, 219)
    pdf.set_text_color(255, 255, 255)

    col_widths = [50, 40, 30, 30, 30]
    headers = ["Personal", "Roll", "Tillg. (h)", "Allok. (h)", "Belaggn. %"]

    for i, header in enumerate(headers):
        pdf.cell(col_widths[i], 8, header, border=1, fill=True, align="C")
    pdf.ln()

    # Tabellinnnehall
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(0, 0, 0)

    for idx, p in enumerate(personal):
        allokeringar = hamta_allokeringar(
            personal_id=p["id"], fran_datum=fran_datum, till_datum=till_datum
        )
        allokerade = sum(a["timmar"] for a in allokeringar)
        tillgangliga = antal_dagar * p["kapacitet_h"]
        belaggning = (allokerade / tillgangliga * 100) if tillgangliga > 0 else 0

        # Varannan rad ljusgrå bakgrund
        if idx % 2 == 0:
            pdf.set_fill_color(245, 245, 245)
        else:
            pdf.set_fill_color(255, 255, 255)

        # Färgkod beläggning
        if belaggning > 100:
            belagg_text = f"{belaggning:.1f} (!)"
        else:
            belagg_text = f"{belaggning:.1f}"

        namn = p["namn"][:20]  # Trunkera vid behov
        roll = p["roll"][:15]

        pdf.cell(col_widths[0], 7, namn, border=1, fill=True)
        pdf.cell(col_widths[1], 7, roll, border=1, fill=True, align="C")
        pdf.cell(col_widths[2], 7, f"{tillgangliga:.0f}", border=1, fill=True, align="C")
        pdf.cell(col_widths[3], 7, f"{allokerade:.1f}", border=1, fill=True, align="C")
        pdf.cell(col_widths[4], 7, belagg_text, border=1, fill=True, align="C")
        pdf.ln()

    # Sammanfattning
    pdf.ln(10)
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 8, "Sammanfattning", ln=True)
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 7, f"Antal resurser: {len(personal)}", ln=True)

    total_allok = sum(
        sum(a["timmar"] for a in hamta_allokeringar(
            personal_id=p["id"], fran_datum=fran_datum, till_datum=till_datum
        ))
        for p in personal
    )
    total_tillg = sum(antal_dagar * p["kapacitet_h"] for p in personal)
    snitt_belaggning = (total_allok / total_tillg * 100) if total_tillg > 0 else 0

    pdf.cell(0, 7, f"Total allokerad tid: {total_allok:.0f} timmar", ln=True)
    pdf.cell(0, 7, f"Total tillganglig tid: {total_tillg:.0f} timmar", ln=True)
    pdf.cell(0, 7, f"Genomsnittlig belaggning: {snitt_belaggning:.1f}%", ln=True)

    # Footer
    pdf.ln(15)
    pdf.set_font("Helvetica", "I", 8)
    pdf.cell(0, 5, f"Genererad: {date.today()}", ln=True, align="C")

    buffer = io.BytesIO()
    pdf.output(buffer)
    buffer.seek(0)
    return buffer.getvalue()
