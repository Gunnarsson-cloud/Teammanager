"""
charts.py - Plotly-visualiseringar för Teammanager
Skapar heatmaps, stapeldiagram och beläggninsgrafer.
"""

import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from datetime import date, timedelta
from calendar_utils import hamta_arbetsdagar, hamta_svenska_helgdagar, MANAD_NAMN
from database import hamta_allokeringar, hamta_all_personal


def skapa_belaggnings_heatmap(fran_datum, till_datum):
    """
    Skapa en heatmap som visar beläggningsgrad per person och vecka.
    X-axel: veckor, Y-axel: personal, Färg: beläggning i %
    """
    personal = hamta_all_personal()
    if not personal:
        return None

    allokeringar = hamta_allokeringar(fran_datum=fran_datum, till_datum=till_datum)
    helgdagar = hamta_svenska_helgdagar(fran_datum.year, till_datum.year)

    # Skapa DataFrame av allokeringar
    if allokeringar:
        df = pd.DataFrame(allokeringar)
        df["datum"] = pd.to_datetime(df["datum"])
        df["vecka"] = df["datum"].dt.isocalendar().week.astype(int)
        df["ar"] = df["datum"].dt.year
    else:
        df = pd.DataFrame()

    # Beräkna alla veckor i intervallet
    alla_veckor = []
    current = fran_datum
    while current <= till_datum:
        vecka_key = f"{current.isocalendar()[0]}-V{current.isocalendar()[1]:02d}"
        if vecka_key not in alla_veckor:
            alla_veckor.append(vecka_key)
        current += timedelta(days=7)

    # Bygg matris: personal x veckor
    person_namn = [p["namn"] for p in personal]
    matris = []

    for person in personal:
        rad = []
        for vecka_label in alla_veckor:
            ar, vecka_nr = vecka_label.split("-V")
            ar = int(ar)
            vecka_nr = int(vecka_nr)

            # Hitta arbetsdagar i denna vecka
            arbetsdagar_i_vecka = 0
            allokerade_timmar = 0.0

            check_date = fran_datum
            while check_date <= till_datum:
                iso = check_date.isocalendar()
                if iso[0] == ar and iso[1] == vecka_nr:
                    if check_date.weekday() < 5 and check_date not in helgdagar:
                        arbetsdagar_i_vecka += 1
                        # Summera allokering för denna person denna dag
                        if not df.empty:
                            dag_allok = df[
                                (df["personal_id"] == person["id"]) &
                                (df["datum"].dt.date == check_date)
                            ]["timmar"].sum()
                            allokerade_timmar += dag_allok
                check_date += timedelta(days=1)

            if arbetsdagar_i_vecka > 0:
                max_timmar = arbetsdagar_i_vecka * person["kapacitet_h"]
                belaggning = (allokerade_timmar / max_timmar) * 100
            else:
                belaggning = 0

            rad.append(round(belaggning, 1))
        matris.append(rad)

    # Skapa heatmap
    fig = go.Figure(data=go.Heatmap(
        z=matris,
        x=alla_veckor,
        y=person_namn,
        colorscale=[
            [0.0, "#f0f0f0"],    # Ingen beläggning - ljusgrå
            [0.25, "#a8d5e2"],   # Låg - ljusblå
            [0.5, "#2ecc71"],    # Medel - grön
            [0.75, "#f39c12"],   # Hög - orange
            [1.0, "#e74c3c"],    # Överbelagd - röd
        ],
        zmin=0,
        zmax=120,
        text=[[f"{v}%" for v in rad] for rad in matris],
        texttemplate="%{text}",
        textfont={"size": 10},
        hovertemplate="Person: %{y}<br>Vecka: %{x}<br>Beläggning: %{text}<extra></extra>",
        colorbar=dict(title="Beläggning %")
    ))

    fig.update_layout(
        title="Beläggning per person och vecka",
        xaxis_title="Vecka",
        yaxis_title="Personal",
        height=max(400, len(personal) * 40 + 150),
        yaxis=dict(autorange="reversed"),
        margin=dict(l=120)
    )

    return fig


def skapa_team_belaggning_stapel(fran_datum, till_datum):
    """
    Skapa stapeldiagram som visar total teambeläggning per vecka,
    uppdelat per projekt.
    """
    allokeringar = hamta_allokeringar(fran_datum=fran_datum, till_datum=till_datum)
    if not allokeringar:
        return None

    df = pd.DataFrame(allokeringar)
    df["datum"] = pd.to_datetime(df["datum"])
    df["vecka"] = df["datum"].dt.strftime("%G-V%V")

    # Gruppera per vecka och projekt
    grouped = df.groupby(["vecka", "projekt_namn", "projekt_farg"])["timmar"].sum().reset_index()

    fig = go.Figure()

    for _, proj_data in grouped.groupby("projekt_namn"):
        proj_namn = proj_data["projekt_namn"].iloc[0]
        proj_farg = proj_data["projekt_farg"].iloc[0]
        fig.add_trace(go.Bar(
            x=proj_data["vecka"],
            y=proj_data["timmar"],
            name=proj_namn,
            marker_color=proj_farg,
            hovertemplate=f"{proj_namn}<br>Vecka: %{{x}}<br>Timmar: %{{y:.1f}}<extra></extra>"
        ))

    fig.update_layout(
        title="Team-allokering per vecka (timmar per projekt)",
        xaxis_title="Vecka",
        yaxis_title="Timmar",
        barmode="stack",
        height=400,
        legend=dict(orientation="h", yanchor="bottom", y=1.02)
    )

    return fig


def skapa_person_belaggning_pie(personal_id, fran_datum, till_datum):
    """
    Skapa ett cirkeldiagram som visar hur en persons tid
    fördelats mellan projekt under perioden.
    """
    allokeringar = hamta_allokeringar(
        personal_id=personal_id, fran_datum=fran_datum, till_datum=till_datum
    )
    if not allokeringar:
        return None

    df = pd.DataFrame(allokeringar)
    grouped = df.groupby(["projekt_namn", "projekt_farg"])["timmar"].sum().reset_index()

    fig = go.Figure(data=[go.Pie(
        labels=grouped["projekt_namn"],
        values=grouped["timmar"],
        marker=dict(colors=grouped["projekt_farg"]),
        textinfo="label+percent",
        hovertemplate="%{label}<br>Timmar: %{value:.1f}<br>Andel: %{percent}<extra></extra>"
    )])

    fig.update_layout(
        title="Tidsfördelning per projekt",
        height=350
    )

    return fig


def skapa_kapacitetsvarningar(fran_datum, till_datum):
    """
    Identifiera alla dagar där någon person är överbelagd.
    Returnerar en DataFrame med varningar.
    """
    personal = hamta_all_personal()
    allokeringar = hamta_allokeringar(fran_datum=fran_datum, till_datum=till_datum)

    if not allokeringar:
        return pd.DataFrame()

    df = pd.DataFrame(allokeringar)
    # Summera per person och datum
    dag_summa = df.groupby(["personal_id", "personal_namn", "datum", "kapacitet_h"])["timmar"].sum().reset_index()
    dag_summa.rename(columns={"timmar": "total_timmar"}, inplace=True)

    # Filtrera överbelastade
    varningar = dag_summa[dag_summa["total_timmar"] > dag_summa["kapacitet_h"]].copy()
    varningar["overtid"] = varningar["total_timmar"] - varningar["kapacitet_h"]
    varningar = varningar.sort_values(["datum", "personal_namn"])

    return varningar
