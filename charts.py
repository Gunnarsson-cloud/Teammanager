"""
charts.py - Plotly-visualiseringar för Teammanager v3.0
Heatmaps, stapeldiagram, Gantt-översikt, frånvarodiagram.
"""

import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from datetime import date, timedelta
from calendar_utils import hamta_arbetsdagar, hamta_svenska_helgdagar, MANAD_NAMN
from database import (
    hamta_allokeringar, hamta_all_personal, hamta_franvaro,
    hamta_teamoversikt, FRANVARO_TYPER
)


def skapa_belaggnings_heatmap(fran_datum, till_datum):
    """Heatmap: personal x veckor, färg = beläggning%."""
    personal = hamta_all_personal()
    if not personal:
        return None

    allokeringar = hamta_allokeringar(fran_datum=fran_datum, till_datum=till_datum)
    helgdagar = hamta_svenska_helgdagar(fran_datum.year, till_datum.year)

    if allokeringar:
        df = pd.DataFrame(allokeringar)
        df["datum"] = pd.to_datetime(df["datum"])
    else:
        df = pd.DataFrame()

    alla_veckor = []
    current = fran_datum
    while current <= till_datum:
        vecka_key = f"{current.isocalendar()[0]}-V{current.isocalendar()[1]:02d}"
        if vecka_key not in alla_veckor:
            alla_veckor.append(vecka_key)
        current += timedelta(days=7)

    person_namn = [p["namn"] for p in personal]
    matris = []

    for person in personal:
        rad = []
        for vecka_label in alla_veckor:
            ar, vecka_nr = vecka_label.split("-V")
            ar, vecka_nr = int(ar), int(vecka_nr)

            arbetsdagar_i_vecka = 0
            allokerade_timmar = 0.0

            check_date = fran_datum
            while check_date <= till_datum:
                iso = check_date.isocalendar()
                if iso[0] == ar and iso[1] == vecka_nr:
                    if check_date.weekday() < 5 and check_date not in helgdagar:
                        arbetsdagar_i_vecka += 1
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

    fig = go.Figure(data=go.Heatmap(
        z=matris, x=alla_veckor, y=person_namn,
        colorscale=[
            [0.0, "#f0f0f0"], [0.25, "#a8d5e2"],
            [0.5, "#2ecc71"], [0.75, "#f39c12"], [1.0, "#e74c3c"],
        ],
        zmin=0, zmax=120,
        text=[[f"{v}%" for v in rad] for rad in matris],
        texttemplate="%{text}", textfont={"size": 10},
        hovertemplate="Person: %{y}<br>Vecka: %{x}<br>Beläggning: %{text}<extra></extra>",
        colorbar=dict(title="Beläggning %")
    ))
    fig.update_layout(
        xaxis_title="Vecka", yaxis_title="Personal",
        height=max(400, len(personal) * 40 + 150),
        yaxis=dict(autorange="reversed"), margin=dict(l=120)
    )
    return fig


def skapa_team_belaggning_stapel(fran_datum, till_datum):
    """Stacked bar: teamtimmar per vecka, uppdelat per projekt."""
    allokeringar = hamta_allokeringar(fran_datum=fran_datum, till_datum=till_datum)
    if not allokeringar:
        return None

    df = pd.DataFrame(allokeringar)
    df["datum"] = pd.to_datetime(df["datum"])
    df["vecka"] = df["datum"].dt.strftime("%G-V%V")
    grouped = df.groupby(["vecka", "projekt_namn", "projekt_farg"])["timmar"].sum().reset_index()

    fig = go.Figure()
    for _, proj_data in grouped.groupby("projekt_namn"):
        proj_namn = proj_data["projekt_namn"].iloc[0]
        proj_farg = proj_data["projekt_farg"].iloc[0]
        fig.add_trace(go.Bar(
            x=proj_data["vecka"], y=proj_data["timmar"],
            name=proj_namn, marker_color=proj_farg,
            hovertemplate=f"{proj_namn}<br>Vecka: %{{x}}<br>Timmar: %{{y:.1f}}<extra></extra>"
        ))
    fig.update_layout(
        xaxis_title="Vecka", yaxis_title="Timmar",
        barmode="stack", height=400,
        legend=dict(orientation="h", yanchor="bottom", y=1.02)
    )
    return fig


def skapa_person_belaggning_pie(personal_id, fran_datum, till_datum):
    """Pie chart: tidsfördelning per projekt för en person."""
    allokeringar = hamta_allokeringar(
        personal_id=personal_id, fran_datum=fran_datum, till_datum=till_datum
    )
    if not allokeringar:
        return None

    df = pd.DataFrame(allokeringar)
    grouped = df.groupby(["projekt_namn", "projekt_farg"])["timmar"].sum().reset_index()

    fig = go.Figure(data=[go.Pie(
        labels=grouped["projekt_namn"], values=grouped["timmar"],
        marker=dict(colors=grouped["projekt_farg"]),
        textinfo="label+percent",
        hovertemplate="%{label}<br>Timmar: %{value:.1f}<br>Andel: %{percent}<extra></extra>"
    )])
    fig.update_layout(height=350)
    return fig


def skapa_kapacitetsvarningar(fran_datum, till_datum):
    """Returnerar DataFrame med alla överbelagda person+datum."""
    allokeringar = hamta_allokeringar(fran_datum=fran_datum, till_datum=till_datum)
    if not allokeringar:
        return pd.DataFrame()

    df = pd.DataFrame(allokeringar)
    dag_summa = df.groupby(
        ["personal_id", "personal_namn", "datum", "kapacitet_h"]
    )["timmar"].sum().reset_index()
    dag_summa.rename(columns={"timmar": "total_timmar"}, inplace=True)
    varningar = dag_summa[dag_summa["total_timmar"] > dag_summa["kapacitet_h"]].copy()
    varningar["overtid"] = varningar["total_timmar"] - varningar["kapacitet_h"]
    return varningar.sort_values(["datum", "personal_namn"])


def skapa_gantt_oversikt(fran_datum, till_datum, arbetsdagar):
    """
    Skapa en Gantt-liknande tidslinje för hela teamet.
    Visar projekt som färgade block per person per dag.
    """
    personal = hamta_all_personal()
    if not personal:
        return None

    oversikt = hamta_teamoversikt(fran_datum, till_datum, arbetsdagar)
    if not oversikt:
        return None

    fig = go.Figure()
    y_labels = []
    y_positions = []

    for idx, p in enumerate(personal):
        pid = p["id"]
        y_labels.append(p["namn"])
        y_pos = len(personal) - idx

        if pid not in oversikt:
            continue

        for dag in arbetsdagar:
            dag_str = str(dag)
            if dag_str not in oversikt[pid]["dagar"]:
                continue

            dag_data = oversikt[pid]["dagar"][dag_str]

            # Frånvaro
            if dag_data["franvaro"]:
                typ = dag_data["franvaro"]
                info = FRANVARO_TYPER.get(typ, FRANVARO_TYPER["ovrigt"])
                fig.add_trace(go.Bar(
                    x=[1], y=[y_pos], base=[dag.toordinal() - fran_datum.toordinal()],
                    orientation='h', marker_color=info["farg"],
                    marker_line=dict(width=1, color='white'),
                    name=info["namn"], showlegend=False,
                    hovertemplate=f"{p['namn']}<br>{dag}<br>{info['ikon']} {info['namn']}<extra></extra>"
                ))
            # Allokeringar
            elif dag_data["allokeringar"]:
                for allok in dag_data["allokeringar"]:
                    width = allok["timmar"] / p["kapacitet_h"]
                    fig.add_trace(go.Bar(
                        x=[width], y=[y_pos],
                        base=[dag.toordinal() - fran_datum.toordinal()],
                        orientation='h', marker_color=allok["farg"],
                        marker_line=dict(width=0.5, color='white'),
                        name=allok["projekt"], showlegend=False,
                        hovertemplate=(
                            f"{p['namn']}<br>{dag}<br>"
                            f"{allok['projekt']}: {allok['timmar']}h<extra></extra>"
                        )
                    ))

    dag_labels = [str(d) for d in arbetsdagar]
    fig.update_layout(
        barmode='stack', height=max(400, len(personal) * 45 + 100),
        xaxis=dict(
            tickvals=list(range(len(arbetsdagar))),
            ticktext=[f"{d.day}/{d.month}" for d in arbetsdagar],
            title="Datum"
        ),
        yaxis=dict(
            tickvals=list(range(1, len(personal) + 1)),
            ticktext=list(reversed(y_labels)),
            title=""
        ),
        margin=dict(l=120, t=20),
        showlegend=False
    )
    return fig


def skapa_franvaro_oversikt(fran_datum, till_datum):
    """Skapa stapeldiagram av frånvaro per typ och person."""
    franvaro_data = hamta_franvaro(fran_datum=fran_datum, till_datum=till_datum)
    if not franvaro_data:
        return None

    df = pd.DataFrame(franvaro_data)
    grouped = df.groupby(["personal_namn", "typ"]).size().reset_index(name="dagar")

    fig = go.Figure()
    for typ, info in FRANVARO_TYPER.items():
        typ_data = grouped[grouped["typ"] == typ]
        if not typ_data.empty:
            fig.add_trace(go.Bar(
                x=typ_data["personal_namn"], y=typ_data["dagar"],
                name=f"{info['ikon']} {info['namn']}",
                marker_color=info["farg"]
            ))

    fig.update_layout(
        barmode="stack", height=350,
        xaxis_title="Personal", yaxis_title="Dagar",
        legend=dict(orientation="h", yanchor="bottom", y=1.02)
    )
    return fig
