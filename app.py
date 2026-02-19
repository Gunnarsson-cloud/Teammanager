"""
Teammanager - Resursplaneringsapplikation v2.0
================================================
Modern UI (2026) med glassmorphism, gradient-accenter och responsiv design.
Kör med: streamlit run app.py
"""

import streamlit as st
import pandas as pd
from datetime import date, timedelta, datetime
from database import (
    init_db, hamta_all_personal, lagg_till_personal, uppdatera_personal,
    ta_bort_personal, hamta_alla_projekt, lagg_till_projekt, uppdatera_projekt,
    ta_bort_projekt, hamta_allokeringar, satt_allokering, hamta_dagsbelastning,
    hamta_kompetenser, hamta_alla_kompetenser, satt_kompetenser
)
from calendar_utils import (
    skapa_manadskalender, ar_arbetsdag, hamta_arbetsdagar,
    hamta_svenska_helgdagar, antal_arbetsdagar_i_manad,
    VECKODAG_NAMN, MANAD_NAMN
)
from charts import (
    skapa_belaggnings_heatmap, skapa_team_belaggning_stapel,
    skapa_person_belaggning_pie, skapa_kapacitetsvarningar
)
from export_utils import (
    exportera_allokeringar_csv, exportera_personal_csv,
    exportera_belaggningsrapport_csv, generera_pdf_rapport
)

# ============================================================
# KONFIGURATION
# ============================================================

st.set_page_config(
    page_title="Teammanager",
    page_icon="https://em-content.zobj.net/source/apple/391/bar-chart_1f4ca.png",
    layout="wide",
    initial_sidebar_state="expanded"
)

init_db()

# ============================================================
# MODERN 2026 STYLING
# ============================================================

st.markdown("""
<style>
/* ── Google Font ── */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

/* ── Root variabler ── */
:root {
    --accent: #6C5CE7;
    --accent2: #00B894;
    --bg-card: rgba(255,255,255,0.65);
    --bg-card-dark: rgba(30,30,46,0.55);
    --shadow: 0 8px 32px rgba(0,0,0,0.08);
    --radius: 16px;
    --radius-sm: 10px;
    --gradient-main: linear-gradient(135deg, #6C5CE7 0%, #a29bfe 50%, #00B894 100%);
    --gradient-warm: linear-gradient(135deg, #fd79a8 0%, #fdcb6e 100%);
    --gradient-cool: linear-gradient(135deg, #74b9ff 0%, #a29bfe 100%);
}

/* ── Global typografi ── */
html, body, [class*="css"] { font-family: 'Inter', -apple-system, sans-serif !important; }

/* ── Sidebar ── */
section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #1e1e2e 0%, #2d2b55 100%) !important;
    border-right: 1px solid rgba(108,92,231,0.2);
}
section[data-testid="stSidebar"] * {
    color: #cdd6f4 !important;
}
section[data-testid="stSidebar"] .stRadio label {
    font-size: 15px !important;
    font-weight: 500 !important;
    padding: 6px 0 !important;
    transition: all 0.2s ease;
}
section[data-testid="stSidebar"] .stRadio label:hover {
    color: #ffffff !important;
    padding-left: 4px !important;
}
section[data-testid="stSidebar"] hr { border-color: rgba(108,92,231,0.25) !important; }

/* ── Metric kort ── */
[data-testid="stMetric"] {
    background: var(--bg-card);
    backdrop-filter: blur(12px);
    -webkit-backdrop-filter: blur(12px);
    border: 1px solid rgba(108,92,231,0.12);
    border-radius: var(--radius);
    padding: 20px 24px;
    box-shadow: var(--shadow);
    transition: transform 0.2s ease, box-shadow 0.2s ease;
}
[data-testid="stMetric"]:hover {
    transform: translateY(-2px);
    box-shadow: 0 12px 40px rgba(108,92,231,0.12);
}
[data-testid="stMetric"] label { font-size: 13px !important; font-weight: 600 !important;
    text-transform: uppercase; letter-spacing: 0.5px; opacity: 0.65; }
[data-testid="stMetric"] [data-testid="stMetricValue"] {
    font-size: 32px !important; font-weight: 800 !important;
    background: var(--gradient-main); -webkit-background-clip: text;
    -webkit-text-fill-color: transparent; background-clip: text;
}

/* ── Kalender-grid ── */
.cal-grid {
    display: grid;
    grid-template-columns: repeat(7, 1fr);
    gap: 6px;
    margin: 8px 0;
}
.cal-header {
    text-align: center; font-weight: 700; font-size: 12px;
    text-transform: uppercase; letter-spacing: 1px;
    color: #636e72; padding: 10px 0;
}
.cal-cell {
    aspect-ratio: 1.1;
    display: flex; flex-direction: column; align-items: center; justify-content: center;
    border-radius: var(--radius-sm); font-weight: 600; font-size: 15px;
    transition: all 0.2s ease; cursor: default; position: relative;
}
.cal-cell:hover { transform: scale(1.08); }
.cal-work {
    background: linear-gradient(135deg, #dfe6e9, #f0f3f5);
    color: #2d3436;
    border: 1px solid rgba(0,0,0,0.04);
}
.cal-weekend {
    background: linear-gradient(135deg, #ffeaa7, #fdcb6e);
    color: #6c5300;
    border: 1px solid rgba(253,203,110,0.3);
}
.cal-holiday {
    background: linear-gradient(135deg, #fd79a8, #e84393);
    color: #fff;
    border: 1px solid rgba(232,67,147,0.3);
    box-shadow: 0 4px 15px rgba(232,67,147,0.2);
}
.cal-holiday-name {
    font-size: 8px; font-weight: 500; opacity: 0.85;
    margin-top: 2px; max-width: 100%; overflow: hidden;
    text-overflow: ellipsis; white-space: nowrap; padding: 0 4px;
}
.cal-today {
    box-shadow: 0 0 0 3px var(--accent), 0 4px 15px rgba(108,92,231,0.25) !important;
}
.cal-empty { opacity: 0; }

/* ── Page header ── */
.page-header {
    padding: 12px 0 8px 0;
    margin-bottom: 8px;
}
.page-header h1 {
    font-size: 36px; font-weight: 800; margin: 0; line-height: 1.1;
    background: var(--gradient-main); -webkit-background-clip: text;
    -webkit-text-fill-color: transparent; background-clip: text;
}
.page-header p {
    font-size: 15px; color: #636e72; margin: 4px 0 0 0; font-weight: 400;
}

/* ── Glassmorphism kort ── */
.glass-card {
    background: var(--bg-card);
    backdrop-filter: blur(12px);
    -webkit-backdrop-filter: blur(12px);
    border: 1px solid rgba(108,92,231,0.1);
    border-radius: var(--radius);
    padding: 24px;
    box-shadow: var(--shadow);
    margin-bottom: 16px;
}

/* ── Kompetenstaggar ── */
.skill-tag {
    display: inline-flex; align-items: center; gap: 4px;
    padding: 4px 14px; border-radius: 20px;
    font-size: 12px; font-weight: 600;
    background: linear-gradient(135deg, #dfe6e9, #f0f3f5);
    color: #2d3436; border: 1px solid rgba(0,0,0,0.06);
    margin: 3px; transition: all 0.2s ease;
}
.skill-tag:hover { transform: translateY(-1px); box-shadow: 0 3px 10px rgba(0,0,0,0.08); }

/* ── Varningsboxar ── */
.alert-warn {
    background: linear-gradient(135deg, rgba(253,203,110,0.15), rgba(253,203,110,0.05));
    border-left: 4px solid #fdcb6e; border-radius: 0 var(--radius-sm) var(--radius-sm) 0;
    padding: 14px 20px; margin: 8px 0; font-size: 14px;
}
.alert-danger {
    background: linear-gradient(135deg, rgba(232,67,147,0.1), rgba(232,67,147,0.03));
    border-left: 4px solid #e84393; border-radius: 0 var(--radius-sm) var(--radius-sm) 0;
    padding: 14px 20px; margin: 8px 0; font-size: 14px;
}
.alert-success {
    background: linear-gradient(135deg, rgba(0,184,148,0.1), rgba(0,184,148,0.03));
    border-left: 4px solid #00b894; border-radius: 0 var(--radius-sm) var(--radius-sm) 0;
    padding: 14px 20px; margin: 8px 0; font-size: 14px;
}

/* ── Kalender legend ── */
.legend { display: flex; gap: 16px; align-items: center; flex-wrap: wrap; padding: 12px 0; }
.legend-item { display: flex; align-items: center; gap: 6px; font-size: 13px; font-weight: 500; }
.legend-dot { width: 14px; height: 14px; border-radius: 4px; }

/* ── Helgdagslista ── */
.holiday-row {
    display: flex; justify-content: space-between; align-items: center;
    padding: 10px 16px; border-radius: var(--radius-sm);
    margin: 4px 0; transition: background 0.15s ease;
}
.holiday-row:hover { background: rgba(108,92,231,0.04); }
.holiday-date { font-weight: 600; font-size: 14px; min-width: 120px; }
.holiday-day { font-size: 13px; color: #636e72; min-width: 50px; }
.holiday-name { font-size: 14px; color: #e84393; font-weight: 500; }

/* ── Formulärkort ── */
.stExpander { border-radius: var(--radius) !important; border: 1px solid rgba(108,92,231,0.1) !important;
    box-shadow: var(--shadow) !important; overflow: hidden; }
.stExpander header { font-weight: 600 !important; }

/* ── Projekt-färgindikator ── */
.proj-dot {
    display: inline-block; width: 12px; height: 12px;
    border-radius: 50%; vertical-align: middle; margin-right: 8px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.15);
}

/* ── Knappar ── */
.stDownloadButton > button, .stFormSubmitButton > button {
    border-radius: var(--radius-sm) !important;
    font-weight: 600 !important; letter-spacing: 0.3px;
    transition: all 0.2s ease !important;
}
.stDownloadButton > button:hover, .stFormSubmitButton > button:hover {
    transform: translateY(-1px) !important;
    box-shadow: 0 6px 20px rgba(108,92,231,0.2) !important;
}

/* ── Divider ── */
hr { border-color: rgba(108,92,231,0.08) !important; margin: 24px 0 !important; }

/* ── Export-kort ── */
.export-card {
    background: var(--bg-card); backdrop-filter: blur(12px);
    border: 1px solid rgba(108,92,231,0.1); border-radius: var(--radius);
    padding: 28px; box-shadow: var(--shadow); text-align: center;
}
.export-card h4 { margin-top: 8px; }

/* ── Sidebar branding ── */
.sidebar-brand {
    padding: 8px 0 16px 0; text-align: center;
}
.sidebar-brand h2 {
    font-size: 22px; font-weight: 800; margin: 0;
    background: linear-gradient(135deg, #a29bfe, #00b894);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
}
.sidebar-brand p { font-size: 11px; letter-spacing: 2px; text-transform: uppercase;
    opacity: 0.5; margin: 2px 0 0 0; }
.sidebar-stat { text-align: center; padding: 8px 0; }
.sidebar-stat .num { font-size: 28px; font-weight: 800;
    background: linear-gradient(135deg, #a29bfe, #00b894);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
.sidebar-stat .label { font-size: 11px; text-transform: uppercase; letter-spacing: 1px; opacity: 0.5; }
</style>
""", unsafe_allow_html=True)


# ============================================================
# SIDEBAR - NAVIGATION
# ============================================================

st.sidebar.markdown("""
<div class="sidebar-brand">
    <h2>Teammanager</h2>
    <p>Resource Planning</p>
</div>
""", unsafe_allow_html=True)

st.sidebar.markdown("---")

NAV_ICONS = {
    "Kalender": "&#128197;",
    "Resurser": "&#128101;",
    "Projekt": "&#128188;",
    "Allokering": "&#128203;",
    "Dashboard": "&#128202;",
    "Export": "&#128229;"
}

sida = st.sidebar.radio(
    "Navigering",
    list(NAV_ICONS.keys()),
    index=0
)

st.sidebar.markdown("---")

personal_count = len(hamta_all_personal())
projekt_count = len(hamta_alla_projekt())

st.sidebar.markdown(f"""
<div style="display:flex;gap:12px;">
    <div class="sidebar-stat" style="flex:1;">
        <div class="num">{personal_count}</div>
        <div class="label">Resurser</div>
    </div>
    <div class="sidebar-stat" style="flex:1;">
        <div class="num">{projekt_count}</div>
        <div class="label">Projekt</div>
    </div>
</div>
""", unsafe_allow_html=True)

st.sidebar.markdown("---")
st.sidebar.caption("v2.0 &middot; 2026")


# ============================================================
# HJÄLPFUNKTIONER
# ============================================================

def page_header(title, subtitle):
    """Rendera en snygg sidrubrik."""
    st.markdown(f"""
    <div class="page-header">
        <h1>{NAV_ICONS.get(title, '')} {title}</h1>
        <p>{subtitle}</p>
    </div>
    """, unsafe_allow_html=True)


# ============================================================
# SIDA: KALENDER
# ============================================================

if sida == "Kalender":
    page_header("Kalender", "Svensk arbetskalender med helgdagar")

    col1, col2 = st.columns(2)
    with col1:
        valt_ar = st.selectbox("År", range(date.today().year, date.today().year + 5), index=0)
    with col2:
        vald_manad = st.selectbox("Månad", range(1, 13), index=date.today().month - 1,
                                  format_func=lambda x: MANAD_NAMN[x])

    arbetsdagar_manad = antal_arbetsdagar_i_manad(valt_ar, vald_manad)
    helgdagar = hamta_svenska_helgdagar(valt_ar, valt_ar)

    roda_dagar_manad = sum(
        1 for d, namn in helgdagar.items()
        if d.month == vald_manad and d.year == valt_ar and d.weekday() < 5
    )

    col1, col2, col3 = st.columns(3)
    col1.metric("Arbetsdagar", arbetsdagar_manad)
    col2.metric("Röda dagar", roda_dagar_manad)
    col3.metric("Teamkapacitet", f"{arbetsdagar_manad * 8 * personal_count}h")

    st.markdown("---")

    # Bygg kalender som HTML-grid
    dagar = skapa_manadskalender(valt_ar, vald_manad)
    idag = date.today()

    cal_html = '<div class="cal-grid">'
    for namn in VECKODAG_NAMN:
        cal_html += f'<div class="cal-header">{namn}</div>'

    forsta_veckodag = dagar[0]["veckodag"]
    for _ in range(forsta_veckodag):
        cal_html += '<div class="cal-cell cal-empty">&nbsp;</div>'

    for d in dagar:
        today_class = " cal-today" if d["datum"] == idag else ""

        if d["typ"] == "rod_dag":
            cal_html += f'''<div class="cal-cell cal-holiday{today_class}">
                {d["dag"]}
                <span class="cal-holiday-name">{d["helgdagsnamn"]}</span>
            </div>'''
        elif d["typ"] == "helg":
            cal_html += f'<div class="cal-cell cal-weekend{today_class}">{d["dag"]}</div>'
        else:
            cal_html += f'<div class="cal-cell cal-work{today_class}">{d["dag"]}</div>'

    cal_html += '</div>'
    st.markdown(cal_html, unsafe_allow_html=True)

    # Legend
    st.markdown("""
    <div class="legend">
        <div class="legend-item"><div class="legend-dot" style="background:linear-gradient(135deg,#dfe6e9,#f0f3f5);border:1px solid rgba(0,0,0,0.08);"></div> Arbetsdag</div>
        <div class="legend-item"><div class="legend-dot" style="background:linear-gradient(135deg,#ffeaa7,#fdcb6e);"></div> Helg</div>
        <div class="legend-item"><div class="legend-dot" style="background:linear-gradient(135deg,#fd79a8,#e84393);"></div> Röd dag</div>
        <div class="legend-item"><div class="legend-dot" style="background:#fff;box-shadow:0 0 0 3px var(--accent);"></div> Idag</div>
    </div>
    """, unsafe_allow_html=True)

    # Röda dagar expander
    with st.expander(f"Alla röda dagar {valt_ar}"):
        for d in sorted(helgdagar.keys()):
            veckodag = VECKODAG_NAMN[d.weekday()]
            st.markdown(
                f'<div class="holiday-row">'
                f'<span class="holiday-date">{d}</span>'
                f'<span class="holiday-day">{veckodag}</span>'
                f'<span class="holiday-name">{helgdagar[d]}</span>'
                f'</div>',
                unsafe_allow_html=True
            )


# ============================================================
# SIDA: RESURSER
# ============================================================

elif sida == "Resurser":
    page_header("Resurser", "Hantera teamets medarbetare och kompetenser")

    with st.expander("Lägg till ny medarbetare", expanded=False):
        with st.form("ny_personal_form"):
            col1, col2, col3 = st.columns(3)
            with col1:
                nytt_namn = st.text_input("Namn *")
            with col2:
                ny_roll = st.text_input("Roll / Titel")
            with col3:
                ny_kap = st.number_input("Kapacitet (h/dag)", value=8.0, min_value=1.0,
                                         max_value=12.0, step=0.5)
            ny_kompetens_text = st.text_input(
                "Kompetenser (kommaseparerade)",
                placeholder="Python, JavaScript, Projektledning..."
            )
            if st.form_submit_button("Lägg till", type="primary"):
                if nytt_namn.strip():
                    person_id = lagg_till_personal(nytt_namn, ny_roll, ny_kap)
                    if person_id:
                        if ny_kompetens_text.strip():
                            taggar = [t.strip() for t in ny_kompetens_text.split(",")]
                            satt_kompetenser(person_id, taggar)
                        st.success(f"'{nytt_namn}' tillagd!")
                        st.rerun()
                    else:
                        st.error(f"Kunde inte lägga till - namnet kanske redan finns?")
                else:
                    st.warning("Namn är obligatoriskt.")

    st.markdown("---")

    visa_inaktiva = st.checkbox("Visa även inaktiva", value=False)
    personal = hamta_all_personal(bara_aktiva=not visa_inaktiva)

    if not personal:
        st.markdown("""
        <div class="glass-card" style="text-align:center;padding:48px;">
            <div style="font-size:48px;margin-bottom:12px;">&#128101;</div>
            <h3 style="margin:0 0 8px 0;">Inga medarbetare ännu</h3>
            <p style="opacity:0.6;">Lägg till din första medarbetare med formuläret ovan.</p>
        </div>
        """, unsafe_allow_html=True)
    else:
        for person in personal:
            kompetenser = hamta_kompetenser(person["id"])
            status_icon = "&#9989;" if person["aktiv"] else "&#9898;"
            label = f'{person["namn"]} — {person["roll"]}' if person["roll"] else person["namn"]

            with st.expander(f'{label}'):
                with st.form(f"edit_personal_{person['id']}"):
                    col1, col2, col3, col4 = st.columns([3, 2, 2, 1])
                    with col1:
                        edit_namn = st.text_input("Namn", value=person["namn"],
                                                  key=f"pn_{person['id']}")
                    with col2:
                        edit_roll = st.text_input("Roll", value=person["roll"],
                                                  key=f"pr_{person['id']}")
                    with col3:
                        edit_kap = st.number_input("Kapacitet (h/dag)",
                                                   value=float(person["kapacitet_h"]),
                                                   min_value=1.0, max_value=12.0, step=0.5,
                                                   key=f"pk_{person['id']}")
                    with col4:
                        edit_aktiv = st.checkbox("Aktiv", value=bool(person["aktiv"]),
                                                 key=f"pa_{person['id']}")

                    edit_komp = st.text_input(
                        "Kompetenser",
                        value=", ".join(kompetenser),
                        key=f"pkomp_{person['id']}"
                    )

                    if kompetenser:
                        tagg_html = " ".join(
                            f'<span class="skill-tag">{t}</span>' for t in kompetenser
                        )
                        st.markdown(tagg_html, unsafe_allow_html=True)

                    col_save, col_delete = st.columns([4, 1])
                    with col_save:
                        if st.form_submit_button("Spara", type="primary"):
                            uppdatera_personal(person["id"], edit_namn, edit_roll,
                                             edit_kap, 1 if edit_aktiv else 0)
                            taggar = [t.strip() for t in edit_komp.split(",")]
                            satt_kompetenser(person["id"], taggar)
                            st.success("Uppdaterad!")
                            st.rerun()
                    with col_delete:
                        if st.form_submit_button("Ta bort"):
                            ta_bort_personal(person["id"])
                            st.rerun()


# ============================================================
# SIDA: PROJEKT
# ============================================================

elif sida == "Projekt":
    page_header("Projekt", "Hantera pågående och kommande projekt")

    with st.expander("Skapa nytt projekt", expanded=False):
        with st.form("nytt_projekt_form"):
            col1, col2 = st.columns(2)
            with col1:
                proj_namn = st.text_input("Projektnamn *")
                proj_farg = st.color_picker("Färg", value="#6C5CE7")
            with col2:
                proj_start = st.date_input("Startdatum", value=date.today())
                proj_slut = st.date_input("Slutdatum",
                                          value=date.today() + timedelta(days=90))
            if st.form_submit_button("Skapa projekt", type="primary"):
                if proj_namn.strip():
                    pid = lagg_till_projekt(proj_namn, proj_farg,
                                           str(proj_start), str(proj_slut))
                    if pid:
                        st.success(f"Projekt '{proj_namn}' skapat!")
                        st.rerun()
                    else:
                        st.error("Kunde inte skapa projektet. Namnet kanske redan finns?")
                else:
                    st.warning("Projektnamn är obligatoriskt.")

    st.markdown("---")

    visa_avslutade = st.checkbox("Visa även avslutade projekt", value=False)
    projekt = hamta_alla_projekt(bara_aktiva=not visa_avslutade)

    if not projekt:
        st.markdown("""
        <div class="glass-card" style="text-align:center;padding:48px;">
            <div style="font-size:48px;margin-bottom:12px;">&#128188;</div>
            <h3 style="margin:0 0 8px 0;">Inga projekt ännu</h3>
            <p style="opacity:0.6;">Skapa ditt första projekt med formuläret ovan.</p>
        </div>
        """, unsafe_allow_html=True)
    else:
        for proj in projekt:
            status_text = "" if proj["aktiv"] else " (Avslutat)"
            with st.expander(f'{proj["namn"]}{status_text}'):
                st.markdown(
                    f'<span class="proj-dot" style="background:{proj["farg"]};"></span>'
                    f' **{proj["namn"]}**',
                    unsafe_allow_html=True
                )
                with st.form(f"edit_proj_{proj['id']}"):
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        ep_namn = st.text_input("Namn", value=proj["namn"],
                                                key=f"epn_{proj['id']}")
                        ep_farg = st.color_picker("Färg", value=proj["farg"],
                                                  key=f"epf_{proj['id']}")
                    with col2:
                        ep_start = st.date_input(
                            "Start",
                            value=datetime.strptime(proj["startdatum"], "%Y-%m-%d").date()
                                  if proj["startdatum"] else date.today(),
                            key=f"eps_{proj['id']}"
                        )
                    with col3:
                        ep_slut = st.date_input(
                            "Slut",
                            value=datetime.strptime(proj["slutdatum"], "%Y-%m-%d").date()
                                  if proj["slutdatum"] else date.today() + timedelta(days=90),
                            key=f"epe_{proj['id']}"
                        )
                    ep_aktiv = st.checkbox("Aktivt", value=bool(proj["aktiv"]),
                                          key=f"epa_{proj['id']}")
                    col_save, col_delete = st.columns([4, 1])
                    with col_save:
                        if st.form_submit_button("Spara", type="primary"):
                            uppdatera_projekt(proj["id"], ep_namn, ep_farg,
                                            str(ep_start), str(ep_slut),
                                            1 if ep_aktiv else 0)
                            st.success("Projekt uppdaterat!")
                            st.rerun()
                    with col_delete:
                        if st.form_submit_button("Ta bort"):
                            ta_bort_projekt(proj["id"])
                            st.rerun()


# ============================================================
# SIDA: ALLOKERING
# ============================================================

elif sida == "Allokering":
    page_header("Allokering", "Tilldela personal till projekt per dag")

    personal = hamta_all_personal()
    projekt = hamta_alla_projekt()

    if not personal:
        st.markdown('<div class="alert-warn">&#128161; Lägg till personal först under <b>Resurser</b>.</div>',
                    unsafe_allow_html=True)
    elif not projekt:
        st.markdown('<div class="alert-warn">&#128161; Skapa projekt först under <b>Projekt</b>.</div>',
                    unsafe_allow_html=True)
    else:
        col1, col2 = st.columns(2)
        with col1:
            allok_start = st.date_input("Från", value=date.today(), key="allok_fran")
        with col2:
            allok_slut = st.date_input("Till",
                                       value=date.today() + timedelta(days=13),
                                       key="allok_till")

        if allok_start > allok_slut:
            st.error("Startdatum måste vara före slutdatum.")
        else:
            arbetsdagar = hamta_arbetsdagar(allok_start, allok_slut)
            if not arbetsdagar:
                st.info("Inga arbetsdagar i vald period.")
            else:
                st.markdown("---")
                person_val = st.selectbox(
                    "Välj medarbetare",
                    personal,
                    format_func=lambda p: f"{p['namn']} ({p['roll']})"
                )

                if person_val:
                    # Visa kapacitetsvarningar
                    for dag in arbetsdagar:
                        belastning = hamta_dagsbelastning(person_val["id"], dag)
                        if belastning > person_val["kapacitet_h"]:
                            overtid = belastning - person_val["kapacitet_h"]
                            st.markdown(
                                f'<div class="alert-danger">&#9888;&#65039; <strong>{dag}</strong>: '
                                f'Överbelagd med {overtid:.1f}h '
                                f'({belastning:.1f}h / {person_val["kapacitet_h"]:.1f}h)</div>',
                                unsafe_allow_html=True
                            )

                    st.markdown("---")
                    st.caption("Fyll i timmar per projekt och dag (0 = ingen allokering)")

                    for proj in projekt:
                        st.markdown(
                            f'<span class="proj-dot" style="background:{proj["farg"]};"></span>'
                            f' **{proj["namn"]}**',
                            unsafe_allow_html=True
                        )

                        for rad_start in range(0, len(arbetsdagar), 7):
                            rad_dagar = arbetsdagar[rad_start:rad_start + 7]
                            cols = st.columns(len(rad_dagar))
                            for i, dag in enumerate(rad_dagar):
                                veckodag = VECKODAG_NAMN[dag.weekday()]
                                befintliga = hamta_allokeringar(
                                    personal_id=person_val["id"],
                                    projekt_id=proj["id"],
                                    fran_datum=dag, till_datum=dag
                                )
                                nuvarande = befintliga[0]["timmar"] if befintliga else 0.0
                                with cols[i]:
                                    nya_timmar = st.number_input(
                                        f"{veckodag} {dag.day}/{dag.month}",
                                        value=float(nuvarande),
                                        min_value=0.0, max_value=12.0, step=0.5,
                                        key=f"allok_{person_val['id']}_{proj['id']}_{dag}"
                                    )
                                    if nya_timmar != nuvarande:
                                        satt_allokering(person_val["id"], proj["id"], dag, nya_timmar)
                        st.markdown("---")

                    # Sammanfattning
                    total_allokerat = 0
                    per_projekt = {}
                    for proj in projekt:
                        allok = hamta_allokeringar(
                            personal_id=person_val["id"], projekt_id=proj["id"],
                            fran_datum=allok_start, till_datum=allok_slut
                        )
                        proj_timmar = sum(a["timmar"] for a in allok)
                        if proj_timmar > 0:
                            per_projekt[proj["namn"]] = proj_timmar
                        total_allokerat += proj_timmar

                    total_kapacitet = len(arbetsdagar) * person_val["kapacitet_h"]
                    belaggning = (total_allokerat / total_kapacitet * 100) if total_kapacitet > 0 else 0

                    col1, col2, col3 = st.columns(3)
                    col1.metric("Allokerade timmar", f"{total_allokerat:.1f}h")
                    col2.metric("Tillgänglig kapacitet", f"{total_kapacitet:.0f}h")
                    col3.metric("Beläggning", f"{belaggning:.1f}%")

                    if per_projekt:
                        st.markdown("**Fördelning per projekt:**")
                        for proj_namn, timmar in per_projekt.items():
                            st.write(f"- {proj_namn}: {timmar:.1f}h")


# ============================================================
# SIDA: DASHBOARD
# ============================================================

elif sida == "Dashboard":
    page_header("Dashboard", "Beläggningsanalys och teamöversikt")

    col1, col2 = st.columns(2)
    with col1:
        dash_start = st.date_input("Från", value=date.today(), key="dash_fran")
    with col2:
        dash_slut = st.date_input("Till",
                                  value=date.today() + timedelta(days=60),
                                  key="dash_till")

    if dash_start >= dash_slut:
        st.error("Startdatum måste vara före slutdatum.")
    else:
        personal = hamta_all_personal()
        if not personal:
            st.info("Lägg till personal först för att se dashboard.")
        else:
            st.markdown("---")
            st.markdown("### Beläggning per person och vecka")
            heatmap = skapa_belaggnings_heatmap(dash_start, dash_slut)
            if heatmap:
                heatmap.update_layout(
                    paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                    font=dict(family="Inter", size=12),
                    title=None, margin=dict(l=120, t=20)
                )
                st.plotly_chart(heatmap, use_container_width=True)
            else:
                st.info("Ingen data att visa.")

            st.markdown("---")
            st.markdown("### Team-allokering per vecka")
            stapel = skapa_team_belaggning_stapel(dash_start, dash_slut)
            if stapel:
                stapel.update_layout(
                    paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                    font=dict(family="Inter", size=12),
                    title=None, margin=dict(t=20)
                )
                st.plotly_chart(stapel, use_container_width=True)
            else:
                st.info("Inga allokeringar i perioden.")

            st.markdown("---")
            st.markdown("### Individuell analys")
            vald_person = st.selectbox(
                "Välj medarbetare", personal,
                format_func=lambda p: f"{p['namn']} ({p['roll']})",
                key="dash_person"
            )
            if vald_person:
                pie = skapa_person_belaggning_pie(vald_person["id"], dash_start, dash_slut)
                if pie:
                    pie.update_layout(
                        paper_bgcolor='rgba(0,0,0,0)',
                        font=dict(family="Inter", size=12),
                        title=None
                    )
                    st.plotly_chart(pie, use_container_width=True)
                else:
                    st.info(f"Inga allokeringar för {vald_person['namn']} i perioden.")

            st.markdown("---")
            st.markdown("### Kapacitetsvarningar")
            varningar = skapa_kapacitetsvarningar(dash_start, dash_slut)
            if varningar.empty:
                st.markdown(
                    '<div class="alert-success">&#9989; Inga kapacitetsvarningar i perioden!</div>',
                    unsafe_allow_html=True
                )
            else:
                st.markdown(
                    f'<div class="alert-warn">&#9888;&#65039; <strong>{len(varningar)}</strong> '
                    f'överbelastade dagar hittade</div>',
                    unsafe_allow_html=True
                )
                for _, v in varningar.iterrows():
                    st.markdown(
                        f'<div class="alert-danger">&#9888;&#65039; <strong>{v["personal_namn"]}</strong> '
                        f'{v["datum"]}: {v["total_timmar"]:.1f}h allokerat '
                        f'(kapacitet: {v["kapacitet_h"]:.1f}h, '
                        f'övertid: +{v["overtid"]:.1f}h)</div>',
                        unsafe_allow_html=True
                    )


# ============================================================
# SIDA: EXPORT
# ============================================================

elif sida == "Export":
    page_header("Export", "Exportera data till CSV och PDF")

    col1, col2 = st.columns(2)
    with col1:
        exp_start = st.date_input("Från", value=date.today().replace(day=1), key="exp_fran")
    with col2:
        exp_slut = st.date_input("Till",
                                 value=date.today() + timedelta(days=30),
                                 key="exp_till")

    st.markdown("---")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### CSV-exporter")

        csv_allok = exportera_allokeringar_csv(exp_start, exp_slut)
        st.download_button(
            label="&#128196;  Allokeringar (CSV)",
            data=csv_allok,
            file_name=f"allokeringar_{exp_start}_{exp_slut}.csv",
            mime="text/csv",
            use_container_width=True
        )

        csv_personal = exportera_personal_csv()
        st.download_button(
            label="&#128101;  Personalregister (CSV)",
            data=csv_personal,
            file_name="personalregister.csv",
            mime="text/csv",
            use_container_width=True
        )

        csv_belagg = exportera_belaggningsrapport_csv(exp_start, exp_slut)
        st.download_button(
            label="&#128202;  Beläggningsrapport (CSV)",
            data=csv_belagg,
            file_name=f"belaggning_{exp_start}_{exp_slut}.csv",
            mime="text/csv",
            use_container_width=True
        )

    with col2:
        st.markdown("### PDF-rapport")
        st.write("Generera en komplett beläggningsrapport som PDF.")

        try:
            pdf_data = generera_pdf_rapport(exp_start, exp_slut)
            st.download_button(
                label="&#128209;  Ladda ner PDF-rapport",
                data=pdf_data,
                file_name=f"belaggningsrapport_{exp_start}_{exp_slut}.pdf",
                mime="application/pdf",
                use_container_width=True
            )
        except ImportError:
            st.warning("PDF-export kräver `fpdf2`. Installera med: `pip install fpdf2`")
        except Exception as e:
            st.error(f"Kunde inte generera PDF: {e}")
