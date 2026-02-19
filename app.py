"""
Teammanager - Resursplaneringsapplikation v3.0
================================================
Komplett resursplanering med frånvaro, bulk-allokering, Gantt-vy,
lediga resurser, kopiera vecka, kommentarer och smart startsida.
Kör med: streamlit run app.py
"""

import streamlit as st
import pandas as pd
from datetime import date, timedelta, datetime
from database import (
    init_db, hamta_all_personal, lagg_till_personal, uppdatera_personal,
    ta_bort_personal, hamta_alla_projekt, lagg_till_projekt, uppdatera_projekt,
    ta_bort_projekt, hamta_allokeringar, satt_allokering, hamta_dagsbelastning,
    hamta_kompetenser, hamta_alla_kompetenser, satt_kompetenser,
    bulk_allokera, kopiera_vecka,
    hamta_franvaro, satt_franvaro, bulk_franvaro, ta_bort_franvaro,
    ar_franvarande, FRANVARO_TYPER,
    hamta_kommentar, satt_kommentar, hamta_kommentarer_period,
    hamta_overbelagda, hamta_oallokerade, hamta_lediga_resurser,
    hamta_teamoversikt
)
from calendar_utils import (
    skapa_manadskalender, ar_arbetsdag, hamta_arbetsdagar,
    hamta_svenska_helgdagar, antal_arbetsdagar_i_manad,
    VECKODAG_NAMN, MANAD_NAMN
)
from charts import (
    skapa_belaggnings_heatmap, skapa_team_belaggning_stapel,
    skapa_person_belaggning_pie, skapa_kapacitetsvarningar,
    skapa_gantt_oversikt, skapa_franvaro_oversikt
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
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
:root {
    --accent: #6C5CE7; --accent2: #00B894;
    --bg-card: rgba(255,255,255,0.65);
    --shadow: 0 8px 32px rgba(0,0,0,0.08);
    --radius: 16px; --radius-sm: 10px;
    --gradient-main: linear-gradient(135deg, #6C5CE7 0%, #a29bfe 50%, #00B894 100%);
}
html, body, [class*="css"] { font-family: 'Inter', -apple-system, sans-serif !important; }

section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #1e1e2e 0%, #2d2b55 100%) !important;
    border-right: 1px solid rgba(108,92,231,0.2);
}
section[data-testid="stSidebar"] * { color: #cdd6f4 !important; }
section[data-testid="stSidebar"] .stRadio label {
    font-size: 15px !important; font-weight: 500 !important;
    padding: 6px 0 !important; transition: all 0.2s ease;
}
section[data-testid="stSidebar"] .stRadio label:hover {
    color: #ffffff !important; padding-left: 4px !important;
}
section[data-testid="stSidebar"] hr { border-color: rgba(108,92,231,0.25) !important; }

[data-testid="stMetric"] {
    background: var(--bg-card); backdrop-filter: blur(12px);
    border: 1px solid rgba(108,92,231,0.12); border-radius: var(--radius);
    padding: 20px 24px; box-shadow: var(--shadow);
    transition: transform 0.2s ease, box-shadow 0.2s ease;
}
[data-testid="stMetric"]:hover { transform: translateY(-2px);
    box-shadow: 0 12px 40px rgba(108,92,231,0.12); }
[data-testid="stMetric"] label { font-size: 13px !important; font-weight: 600 !important;
    text-transform: uppercase; letter-spacing: 0.5px; opacity: 0.65; }
[data-testid="stMetric"] [data-testid="stMetricValue"] {
    font-size: 32px !important; font-weight: 800 !important;
    background: var(--gradient-main); -webkit-background-clip: text;
    -webkit-text-fill-color: transparent; background-clip: text;
}

.cal-grid { display: grid; grid-template-columns: repeat(7, 1fr); gap: 6px; margin: 8px 0; }
.cal-header { text-align: center; font-weight: 700; font-size: 12px;
    text-transform: uppercase; letter-spacing: 1px; color: #636e72; padding: 10px 0; }
.cal-cell { aspect-ratio: 1.1; display: flex; flex-direction: column;
    align-items: center; justify-content: center; border-radius: var(--radius-sm);
    font-weight: 600; font-size: 15px; transition: all 0.2s ease; cursor: default; }
.cal-cell:hover { transform: scale(1.08); }
.cal-work { background: linear-gradient(135deg, #dfe6e9, #f0f3f5); color: #2d3436;
    border: 1px solid rgba(0,0,0,0.04); }
.cal-weekend { background: linear-gradient(135deg, #ffeaa7, #fdcb6e); color: #6c5300;
    border: 1px solid rgba(253,203,110,0.3); }
.cal-holiday { background: linear-gradient(135deg, #fd79a8, #e84393); color: #fff;
    border: 1px solid rgba(232,67,147,0.3); box-shadow: 0 4px 15px rgba(232,67,147,0.2); }
.cal-holiday-name { font-size: 8px; font-weight: 500; opacity: 0.85;
    margin-top: 2px; max-width: 100%; overflow: hidden;
    text-overflow: ellipsis; white-space: nowrap; padding: 0 4px; }
.cal-today { box-shadow: 0 0 0 3px var(--accent), 0 4px 15px rgba(108,92,231,0.25) !important; }
.cal-empty { opacity: 0; }

.page-header { padding: 12px 0 8px 0; margin-bottom: 8px; }
.page-header h1 { font-size: 36px; font-weight: 800; margin: 0; line-height: 1.1;
    background: var(--gradient-main); -webkit-background-clip: text;
    -webkit-text-fill-color: transparent; background-clip: text; }
.page-header p { font-size: 15px; color: #636e72; margin: 4px 0 0 0; font-weight: 400; }

.glass-card { background: var(--bg-card); backdrop-filter: blur(12px);
    border: 1px solid rgba(108,92,231,0.1); border-radius: var(--radius);
    padding: 24px; box-shadow: var(--shadow); margin-bottom: 16px; }

.skill-tag { display: inline-flex; align-items: center; gap: 4px;
    padding: 4px 14px; border-radius: 20px; font-size: 12px; font-weight: 600;
    background: linear-gradient(135deg, #dfe6e9, #f0f3f5); color: #2d3436;
    border: 1px solid rgba(0,0,0,0.06); margin: 3px; transition: all 0.2s ease; }
.skill-tag:hover { transform: translateY(-1px); box-shadow: 0 3px 10px rgba(0,0,0,0.08); }

.alert-warn { background: linear-gradient(135deg, rgba(253,203,110,0.15), rgba(253,203,110,0.05));
    border-left: 4px solid #fdcb6e; border-radius: 0 var(--radius-sm) var(--radius-sm) 0;
    padding: 14px 20px; margin: 8px 0; font-size: 14px; }
.alert-danger { background: linear-gradient(135deg, rgba(232,67,147,0.1), rgba(232,67,147,0.03));
    border-left: 4px solid #e84393; border-radius: 0 var(--radius-sm) var(--radius-sm) 0;
    padding: 14px 20px; margin: 8px 0; font-size: 14px; }
.alert-success { background: linear-gradient(135deg, rgba(0,184,148,0.1), rgba(0,184,148,0.03));
    border-left: 4px solid #00b894; border-radius: 0 var(--radius-sm) var(--radius-sm) 0;
    padding: 14px 20px; margin: 8px 0; font-size: 14px; }
.alert-info { background: linear-gradient(135deg, rgba(116,185,255,0.1), rgba(116,185,255,0.03));
    border-left: 4px solid #74b9ff; border-radius: 0 var(--radius-sm) var(--radius-sm) 0;
    padding: 14px 20px; margin: 8px 0; font-size: 14px; }

.legend { display: flex; gap: 16px; align-items: center; flex-wrap: wrap; padding: 12px 0; }
.legend-item { display: flex; align-items: center; gap: 6px; font-size: 13px; font-weight: 500; }
.legend-dot { width: 14px; height: 14px; border-radius: 4px; }

.holiday-row { display: flex; justify-content: space-between; align-items: center;
    padding: 10px 16px; border-radius: var(--radius-sm); margin: 4px 0; transition: background 0.15s ease; }
.holiday-row:hover { background: rgba(108,92,231,0.04); }
.holiday-date { font-weight: 600; font-size: 14px; min-width: 120px; }
.holiday-day { font-size: 13px; color: #636e72; min-width: 50px; }
.holiday-name { font-size: 14px; color: #e84393; font-weight: 500; }

.stExpander { border-radius: var(--radius) !important; border: 1px solid rgba(108,92,231,0.1) !important;
    box-shadow: var(--shadow) !important; overflow: hidden; }
.proj-dot { display: inline-block; width: 12px; height: 12px; border-radius: 50%;
    vertical-align: middle; margin-right: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.15); }
.stDownloadButton > button, .stFormSubmitButton > button {
    border-radius: var(--radius-sm) !important; font-weight: 600 !important;
    transition: all 0.2s ease !important; }
.stDownloadButton > button:hover, .stFormSubmitButton > button:hover {
    transform: translateY(-1px) !important; box-shadow: 0 6px 20px rgba(108,92,231,0.2) !important; }
hr { border-color: rgba(108,92,231,0.08) !important; margin: 24px 0 !important; }

.sidebar-brand { padding: 8px 0 16px 0; text-align: center; }
.sidebar-brand h2 { font-size: 22px; font-weight: 800; margin: 0;
    background: linear-gradient(135deg, #a29bfe, #00b894);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
.sidebar-brand p { font-size: 11px; letter-spacing: 2px; text-transform: uppercase;
    opacity: 0.5; margin: 2px 0 0 0; }
.sidebar-stat { text-align: center; padding: 8px 0; }
.sidebar-stat .num { font-size: 28px; font-weight: 800;
    background: linear-gradient(135deg, #a29bfe, #00b894);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
.sidebar-stat .label { font-size: 11px; text-transform: uppercase; letter-spacing: 1px; opacity: 0.5; }

.action-card { background: var(--bg-card); backdrop-filter: blur(12px);
    border: 1px solid rgba(108,92,231,0.1); border-radius: var(--radius);
    padding: 20px; box-shadow: var(--shadow); margin-bottom: 12px;
    transition: transform 0.2s ease; }
.action-card:hover { transform: translateY(-2px); }
.action-card .number { font-size: 28px; font-weight: 800;
    background: var(--gradient-main); -webkit-background-clip: text;
    -webkit-text-fill-color: transparent; }
</style>
""", unsafe_allow_html=True)


# ============================================================
# SIDEBAR
# ============================================================

st.sidebar.markdown('<div class="sidebar-brand"><h2>Teammanager</h2><p>Resource Planning</p></div>',
                    unsafe_allow_html=True)
st.sidebar.markdown("---")

NAV_ITEMS = [
    "Hem", "Kalender", "Resurser", "Projekt",
    "Allokering", "Frånvaro", "Teamöversikt", "Dashboard", "Export"
]
NAV_ICONS = {
    "Hem": "&#127968;", "Kalender": "&#128197;", "Resurser": "&#128101;",
    "Projekt": "&#128188;", "Allokering": "&#128203;", "Frånvaro": "&#127796;",
    "Teamöversikt": "&#128200;", "Dashboard": "&#128202;", "Export": "&#128229;"
}

sida = st.sidebar.radio("Navigering", NAV_ITEMS, index=0)
st.sidebar.markdown("---")

personal_count = len(hamta_all_personal())
projekt_count = len(hamta_alla_projekt())

st.sidebar.markdown(f"""
<div style="display:flex;gap:12px;">
    <div class="sidebar-stat" style="flex:1;"><div class="num">{personal_count}</div><div class="label">Resurser</div></div>
    <div class="sidebar-stat" style="flex:1;"><div class="num">{projekt_count}</div><div class="label">Projekt</div></div>
</div>""", unsafe_allow_html=True)
st.sidebar.markdown("---")
st.sidebar.caption("v3.0 &middot; 2026")


def page_header(title, subtitle):
    st.markdown(f'<div class="page-header"><h1>{NAV_ICONS.get(title, "")} {title}</h1><p>{subtitle}</p></div>',
                unsafe_allow_html=True)


# ============================================================
# SIDA: HEM (startsida med röda flaggor)
# ============================================================

if sida == "Hem":
    page_header("Hem", "Snabböversikt och åtgärder som kräver uppmärksamhet")

    idag = date.today()
    vecka_slut = idag + timedelta(days=(4 - idag.weekday()) if idag.weekday() < 5 else 0)
    arbetsdagar_veckan = hamta_arbetsdagar(idag, vecka_slut)
    nasta_vecka_start = idag + timedelta(days=(7 - idag.weekday()))
    nasta_vecka_slut = nasta_vecka_start + timedelta(days=4)
    arbetsdagar_nasta = hamta_arbetsdagar(nasta_vecka_start, nasta_vecka_slut)

    # Hämta problem
    overbelagda_nu = hamta_overbelagda(idag, vecka_slut)
    overbelagda_nasta = hamta_overbelagda(nasta_vecka_start, nasta_vecka_slut)
    oallokerade_nu = hamta_oallokerade(idag, vecka_slut, arbetsdagar_veckan)
    franvaro_nu = hamta_franvaro(fran_datum=idag, till_datum=vecka_slut)

    # KPI-kort
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Överbelagda idag-fre", len(overbelagda_nu))
    col2.metric("Utan allokering", len(oallokerade_nu))
    col3.metric("Frånvarande denna vecka", len(franvaro_nu))
    col4.metric("Överbelagda nästa v.", len(overbelagda_nasta))

    st.markdown("---")

    # Överbelagda
    if overbelagda_nu:
        st.markdown("### Överbelagda denna vecka")
        for o in overbelagda_nu:
            overtid = o["total_timmar"] - o["kapacitet_h"]
            st.markdown(
                f'<div class="alert-danger">&#9888;&#65039; <b>{o["personal_namn"]}</b> '
                f'{o["datum"]}: {o["total_timmar"]:.1f}h / {o["kapacitet_h"]:.1f}h '
                f'(+{overtid:.1f}h)</div>', unsafe_allow_html=True)

    if overbelagda_nasta:
        st.markdown("### Överbelagda nästa vecka")
        for o in overbelagda_nasta:
            overtid = o["total_timmar"] - o["kapacitet_h"]
            st.markdown(
                f'<div class="alert-warn">&#9888;&#65039; <b>{o["personal_namn"]}</b> '
                f'{o["datum"]}: {o["total_timmar"]:.1f}h / {o["kapacitet_h"]:.1f}h '
                f'(+{overtid:.1f}h)</div>', unsafe_allow_html=True)

    # Frånvarande
    if franvaro_nu:
        st.markdown("### Frånvarande denna vecka")
        for f in franvaro_nu:
            info = FRANVARO_TYPER.get(f["typ"], FRANVARO_TYPER["ovrigt"])
            st.markdown(
                f'<div class="alert-info">{info["ikon"]} <b>{f["personal_namn"]}</b> '
                f'{f["datum"]} - {info["namn"]}'
                f'{" (" + f["notering"] + ")" if f["notering"] else ""}</div>',
                unsafe_allow_html=True)

    # Oallokerade
    if oallokerade_nu:
        with st.expander(f"Utan allokering denna vecka ({len(oallokerade_nu)} poster)", expanded=False):
            df_oa = pd.DataFrame(oallokerade_nu)
            st.dataframe(df_oa[["personal_namn", "datum", "roll"]], use_container_width=True, hide_index=True)

    # Lediga resurser idag
    st.markdown("---")
    st.markdown("### Lediga resurser idag")
    lediga = hamta_lediga_resurser(idag)
    if lediga:
        for l in lediga:
            pct = (l["ledigt"] / l["kapacitet_h"]) * 100
            st.markdown(
                f'<div class="alert-success">&#9989; <b>{l["namn"]}</b> ({l["roll"]}) '
                f'— {l["ledigt"]:.1f}h ledigt ({pct:.0f}%)</div>',
                unsafe_allow_html=True)
    else:
        st.info("Alla resurser är fullbelagda eller frånvarande idag.")

    if not overbelagda_nu and not overbelagda_nasta and not oallokerade_nu:
        st.markdown('<div class="alert-success">&#9989; <b>Allt ser bra ut!</b> Inga åtgärder krävs.</div>',
                    unsafe_allow_html=True)


# ============================================================
# SIDA: KALENDER
# ============================================================

elif sida == "Kalender":
    page_header("Kalender", "Svensk arbetskalender med helgdagar")

    col1, col2 = st.columns(2)
    with col1:
        valt_ar = st.selectbox("År", range(date.today().year, date.today().year + 5), index=0)
    with col2:
        vald_manad = st.selectbox("Månad", range(1, 13), index=date.today().month - 1,
                                  format_func=lambda x: MANAD_NAMN[x])

    arbetsdagar_manad = antal_arbetsdagar_i_manad(valt_ar, vald_manad)
    helgdagar = hamta_svenska_helgdagar(valt_ar, valt_ar)
    roda_dagar_manad = sum(1 for d in helgdagar if d.month == vald_manad and d.year == valt_ar and d.weekday() < 5)

    col1, col2, col3 = st.columns(3)
    col1.metric("Arbetsdagar", arbetsdagar_manad)
    col2.metric("Röda dagar", roda_dagar_manad)
    col3.metric("Teamkapacitet", f"{arbetsdagar_manad * 8 * personal_count}h")

    st.markdown("---")

    dagar = skapa_manadskalender(valt_ar, vald_manad)
    idag = date.today()
    cal_html = '<div class="cal-grid">'
    for namn in VECKODAG_NAMN:
        cal_html += f'<div class="cal-header">{namn}</div>'
    for _ in range(dagar[0]["veckodag"]):
        cal_html += '<div class="cal-cell cal-empty">&nbsp;</div>'
    for d in dagar:
        tc = " cal-today" if d["datum"] == idag else ""
        if d["typ"] == "rod_dag":
            cal_html += f'<div class="cal-cell cal-holiday{tc}">{d["dag"]}<span class="cal-holiday-name">{d["helgdagsnamn"]}</span></div>'
        elif d["typ"] == "helg":
            cal_html += f'<div class="cal-cell cal-weekend{tc}">{d["dag"]}</div>'
        else:
            cal_html += f'<div class="cal-cell cal-work{tc}">{d["dag"]}</div>'
    cal_html += '</div>'
    st.markdown(cal_html, unsafe_allow_html=True)

    st.markdown("""<div class="legend">
        <div class="legend-item"><div class="legend-dot" style="background:linear-gradient(135deg,#dfe6e9,#f0f3f5);border:1px solid rgba(0,0,0,0.08);"></div> Arbetsdag</div>
        <div class="legend-item"><div class="legend-dot" style="background:linear-gradient(135deg,#ffeaa7,#fdcb6e);"></div> Helg</div>
        <div class="legend-item"><div class="legend-dot" style="background:linear-gradient(135deg,#fd79a8,#e84393);"></div> Röd dag</div>
        <div class="legend-item"><div class="legend-dot" style="background:#fff;box-shadow:0 0 0 3px var(--accent);"></div> Idag</div>
    </div>""", unsafe_allow_html=True)

    with st.expander(f"Alla röda dagar {valt_ar}"):
        for d in sorted(helgdagar.keys()):
            st.markdown(f'<div class="holiday-row"><span class="holiday-date">{d}</span>'
                       f'<span class="holiday-day">{VECKODAG_NAMN[d.weekday()]}</span>'
                       f'<span class="holiday-name">{helgdagar[d]}</span></div>', unsafe_allow_html=True)


# ============================================================
# SIDA: RESURSER
# ============================================================

elif sida == "Resurser":
    page_header("Resurser", "Hantera teamets medarbetare och kompetenser")

    with st.expander("Lägg till ny medarbetare", expanded=False):
        with st.form("ny_personal_form"):
            col1, col2, col3 = st.columns(3)
            with col1: nytt_namn = st.text_input("Namn *")
            with col2: ny_roll = st.text_input("Roll / Titel")
            with col3: ny_kap = st.number_input("Kapacitet (h/dag)", value=8.0, min_value=1.0, max_value=12.0, step=0.5)
            ny_komp = st.text_input("Kompetenser (kommaseparerade)", placeholder="Python, JavaScript...")
            if st.form_submit_button("Lägg till", type="primary"):
                if nytt_namn.strip():
                    pid = lagg_till_personal(nytt_namn, ny_roll, ny_kap)
                    if pid:
                        if ny_komp.strip():
                            satt_kompetenser(pid, [t.strip() for t in ny_komp.split(",")])
                        st.success(f"'{nytt_namn}' tillagd!"); st.rerun()
                    else: st.error("Namnet finns redan.")
                else: st.warning("Namn krävs.")

    st.markdown("---")
    visa_inaktiva = st.checkbox("Visa inaktiva", value=False)
    personal = hamta_all_personal(bara_aktiva=not visa_inaktiva)

    if not personal:
        st.markdown('<div class="glass-card" style="text-align:center;padding:48px;"><div style="font-size:48px;">&#128101;</div><h3>Inga medarbetare ännu</h3><p style="opacity:0.6;">Lägg till personal ovan.</p></div>', unsafe_allow_html=True)
    else:
        for person in personal:
            kompetenser = hamta_kompetenser(person["id"])
            label = f'{person["namn"]} — {person["roll"]}' if person["roll"] else person["namn"]
            with st.expander(label):
                with st.form(f"edit_{person['id']}"):
                    c1, c2, c3, c4 = st.columns([3, 2, 2, 1])
                    with c1: en = st.text_input("Namn", value=person["namn"], key=f"pn_{person['id']}")
                    with c2: er = st.text_input("Roll", value=person["roll"], key=f"pr_{person['id']}")
                    with c3: ek = st.number_input("Kap.", value=float(person["kapacitet_h"]), min_value=1.0, max_value=12.0, step=0.5, key=f"pk_{person['id']}")
                    with c4: ea = st.checkbox("Aktiv", value=bool(person["aktiv"]), key=f"pa_{person['id']}")
                    ekomp = st.text_input("Kompetenser", value=", ".join(kompetenser), key=f"pkomp_{person['id']}")
                    if kompetenser:
                        st.markdown(" ".join(f'<span class="skill-tag">{t}</span>' for t in kompetenser), unsafe_allow_html=True)
                    c_save, c_del = st.columns([4, 1])
                    with c_save:
                        if st.form_submit_button("Spara", type="primary"):
                            uppdatera_personal(person["id"], en, er, ek, 1 if ea else 0)
                            satt_kompetenser(person["id"], [t.strip() for t in ekomp.split(",")]); st.rerun()
                    with c_del:
                        if st.form_submit_button("Ta bort"):
                            ta_bort_personal(person["id"]); st.rerun()


# ============================================================
# SIDA: PROJEKT
# ============================================================

elif sida == "Projekt":
    page_header("Projekt", "Hantera pågående och kommande projekt")

    with st.expander("Skapa nytt projekt", expanded=False):
        with st.form("nytt_projekt_form"):
            c1, c2 = st.columns(2)
            with c1:
                pn = st.text_input("Projektnamn *")
                pf = st.color_picker("Färg", value="#6C5CE7")
            with c2:
                ps = st.date_input("Start", value=date.today())
                pe = st.date_input("Slut", value=date.today() + timedelta(days=90))
            if st.form_submit_button("Skapa projekt", type="primary"):
                if pn.strip():
                    pid = lagg_till_projekt(pn, pf, str(ps), str(pe))
                    if pid: st.success(f"'{pn}' skapat!"); st.rerun()
                    else: st.error("Projektet finns redan.")
                else: st.warning("Namn krävs.")

    st.markdown("---")
    visa_avslutade = st.checkbox("Visa avslutade", value=False)
    projekt = hamta_alla_projekt(bara_aktiva=not visa_avslutade)

    if not projekt:
        st.markdown('<div class="glass-card" style="text-align:center;padding:48px;"><div style="font-size:48px;">&#128188;</div><h3>Inga projekt ännu</h3></div>', unsafe_allow_html=True)
    else:
        for proj in projekt:
            with st.expander(f'{proj["namn"]}{" (Avslutat)" if not proj["aktiv"] else ""}'):
                st.markdown(f'<span class="proj-dot" style="background:{proj["farg"]};"></span> **{proj["namn"]}**', unsafe_allow_html=True)
                with st.form(f"ep_{proj['id']}"):
                    c1, c2, c3 = st.columns(3)
                    with c1:
                        epn = st.text_input("Namn", value=proj["namn"], key=f"epn_{proj['id']}")
                        epf = st.color_picker("Färg", value=proj["farg"], key=f"epf_{proj['id']}")
                    with c2:
                        eps = st.date_input("Start", value=datetime.strptime(proj["startdatum"], "%Y-%m-%d").date() if proj["startdatum"] else date.today(), key=f"eps_{proj['id']}")
                    with c3:
                        epe = st.date_input("Slut", value=datetime.strptime(proj["slutdatum"], "%Y-%m-%d").date() if proj["slutdatum"] else date.today()+timedelta(days=90), key=f"epe_{proj['id']}")
                    epa = st.checkbox("Aktivt", value=bool(proj["aktiv"]), key=f"epa_{proj['id']}")
                    cs, cd = st.columns([4, 1])
                    with cs:
                        if st.form_submit_button("Spara", type="primary"):
                            uppdatera_projekt(proj["id"], epn, epf, str(eps), str(epe), 1 if epa else 0); st.rerun()
                    with cd:
                        if st.form_submit_button("Ta bort"):
                            ta_bort_projekt(proj["id"]); st.rerun()


# ============================================================
# SIDA: ALLOKERING (med bulk, kopiera vecka, kommentarer)
# ============================================================

elif sida == "Allokering":
    page_header("Allokering", "Tilldela personal till projekt — med snabbverktyg")

    personal = hamta_all_personal()
    projekt = hamta_alla_projekt()

    if not personal:
        st.markdown('<div class="alert-warn">&#128161; Lägg till personal först under <b>Resurser</b>.</div>', unsafe_allow_html=True)
    elif not projekt:
        st.markdown('<div class="alert-warn">&#128161; Skapa projekt först under <b>Projekt</b>.</div>', unsafe_allow_html=True)
    else:
        c1, c2 = st.columns(2)
        with c1: allok_start = st.date_input("Från", value=date.today(), key="af")
        with c2: allok_slut = st.date_input("Till", value=date.today() + timedelta(days=13), key="at")

        if allok_start > allok_slut:
            st.error("Startdatum måste vara före slutdatum.")
        else:
            arbetsdagar = hamta_arbetsdagar(allok_start, allok_slut)
            if not arbetsdagar:
                st.info("Inga arbetsdagar i perioden.")
            else:
                person_val = st.selectbox("Välj medarbetare", personal,
                    format_func=lambda p: f"{p['namn']} ({p['roll']})")

                if person_val:
                    tab_snabb, tab_dag, tab_kopiera, tab_kommentar = st.tabs(
                        ["Snabballokering", "Dag-för-dag", "Kopiera vecka", "Kommentarer"]
                    )

                    # TAB: SNABBALLOKERING (bulk)
                    with tab_snabb:
                        st.markdown("#### Snabballokering")
                        st.caption("Allokera samma antal timmar för hela perioden med ett klick.")

                        with st.form("bulk_form"):
                            bulk_proj = st.selectbox("Projekt", projekt,
                                format_func=lambda p: p["namn"], key="bulk_proj")
                            c1, c2 = st.columns(2)
                            with c1:
                                bulk_timmar = st.number_input("Timmar per dag", value=8.0,
                                    min_value=0.0, max_value=12.0, step=0.5, key="bulk_h")
                            with c2:
                                st.write(f"**{len(arbetsdagar)} arbetsdagar**")
                                st.write(f"Totalt: **{len(arbetsdagar) * bulk_timmar:.0f}h**")

                            if st.form_submit_button("Allokera hela perioden", type="primary"):
                                bulk_allokera(person_val["id"], bulk_proj["id"], arbetsdagar, bulk_timmar)
                                st.success(f"{person_val['namn']} allokerad {bulk_timmar}h/dag till {bulk_proj['namn']} ({len(arbetsdagar)} dagar)")
                                st.rerun()

                        # Snabbknappar
                        st.markdown("**Snabbknappar:**")
                        c1, c2, c3, c4 = st.columns(4)
                        for col, (label, timmar) in zip([c1, c2, c3, c4],
                            [("100%", 8.0), ("75%", 6.0), ("50%", 4.0), ("25%", 2.0)]):
                            with col:
                                if st.button(f"{label} ({timmar}h/dag)", use_container_width=True, key=f"snabb_{label}"):
                                    if projekt:
                                        bulk_allokera(person_val["id"], projekt[0]["id"], arbetsdagar, timmar)
                                        st.success(f"Allokerat {label} till {projekt[0]['namn']}")
                                        st.rerun()

                    # TAB: DAG FÖR DAG
                    with tab_dag:
                        st.markdown("#### Dag-för-dag-allokering")

                        for dag in arbetsdagar:
                            belastning = hamta_dagsbelastning(person_val["id"], dag)
                            franv = ar_franvarande(person_val["id"], dag)
                            if franv:
                                info = FRANVARO_TYPER.get(franv["typ"], FRANVARO_TYPER["ovrigt"])
                                st.markdown(f'<div class="alert-info">{info["ikon"]} {dag} ({VECKODAG_NAMN[dag.weekday()]}) — {info["namn"]}</div>', unsafe_allow_html=True)
                                continue
                            if belastning > person_val["kapacitet_h"]:
                                st.markdown(f'<div class="alert-danger">&#9888;&#65039; {dag}: {belastning:.1f}h / {person_val["kapacitet_h"]:.1f}h</div>', unsafe_allow_html=True)

                        for proj in projekt:
                            st.markdown(f'<span class="proj-dot" style="background:{proj["farg"]};"></span> **{proj["namn"]}**', unsafe_allow_html=True)
                            for rs in range(0, len(arbetsdagar), 7):
                                rd = arbetsdagar[rs:rs + 7]
                                cols = st.columns(len(rd))
                                for i, dag in enumerate(rd):
                                    bef = hamta_allokeringar(personal_id=person_val["id"], projekt_id=proj["id"], fran_datum=dag, till_datum=dag)
                                    nuv = bef[0]["timmar"] if bef else 0.0
                                    with cols[i]:
                                        ny = st.number_input(f"{VECKODAG_NAMN[dag.weekday()]} {dag.day}/{dag.month}",
                                            value=float(nuv), min_value=0.0, max_value=12.0, step=0.5,
                                            key=f"a_{person_val['id']}_{proj['id']}_{dag}")
                                        if ny != nuv:
                                            satt_allokering(person_val["id"], proj["id"], dag, ny)
                            st.markdown("---")

                    # TAB: KOPIERA VECKA
                    with tab_kopiera:
                        st.markdown("#### Kopiera vecka")
                        st.caption("Kopiera alla allokeringar från en vecka till en annan.")

                        with st.form("kopiera_form"):
                            c1, c2 = st.columns(2)
                            with c1:
                                fran_mandag = st.date_input("Från vecka (måndag)",
                                    value=allok_start - timedelta(days=allok_start.weekday()), key="kop_fran")
                            with c2:
                                till_mandag = st.date_input("Till vecka (måndag)",
                                    value=allok_start - timedelta(days=allok_start.weekday()) + timedelta(days=7), key="kop_till")

                            if st.form_submit_button("Kopiera vecka", type="primary"):
                                antal = kopiera_vecka(person_val["id"], fran_mandag, till_mandag)
                                st.success(f"Kopierade {antal} allokeringar!")
                                st.rerun()

                    # TAB: KOMMENTARER
                    with tab_kommentar:
                        st.markdown("#### Kommentarer per dag")
                        st.caption("Lägg till anteckningar som 'Jobbar hemifrån' eller 'Väntar på beslut'.")

                        for dag in arbetsdagar[:10]:  # Begränsa till 10 dagar
                            befintlig = hamta_kommentar(person_val["id"], dag)
                            ny_kommentar = st.text_input(
                                f"{VECKODAG_NAMN[dag.weekday()]} {dag}",
                                value=befintlig,
                                key=f"kom_{person_val['id']}_{dag}",
                                placeholder="Anteckning..."
                            )
                            if ny_kommentar != befintlig:
                                satt_kommentar(person_val["id"], dag, ny_kommentar)

                    # Sammanfattning
                    st.markdown("---")
                    st.markdown("### Sammanfattning")
                    total_allokerat = 0
                    per_projekt = {}
                    for proj in projekt:
                        allok = hamta_allokeringar(personal_id=person_val["id"], projekt_id=proj["id"],
                                                    fran_datum=allok_start, till_datum=allok_slut)
                        pt = sum(a["timmar"] for a in allok)
                        if pt > 0: per_projekt[proj["namn"]] = pt
                        total_allokerat += pt
                    total_kap = len(arbetsdagar) * person_val["kapacitet_h"]
                    bel = (total_allokerat / total_kap * 100) if total_kap > 0 else 0

                    c1, c2, c3 = st.columns(3)
                    c1.metric("Allokerat", f"{total_allokerat:.1f}h")
                    c2.metric("Kapacitet", f"{total_kap:.0f}h")
                    c3.metric("Beläggning", f"{bel:.1f}%")
                    if per_projekt:
                        for pn, t in per_projekt.items():
                            st.write(f"- {pn}: {t:.1f}h")


# ============================================================
# SIDA: FRÅNVARO
# ============================================================

elif sida == "Frånvaro":
    page_header("Frånvaro", "Registrera semester, sjukdom, VAB och annan frånvaro")

    personal = hamta_all_personal()
    if not personal:
        st.warning("Lägg till personal först.")
    else:
        # Registrera frånvaro
        with st.expander("Registrera frånvaro", expanded=True):
            with st.form("franvaro_form"):
                c1, c2 = st.columns(2)
                with c1:
                    fv_person = st.selectbox("Medarbetare", personal,
                        format_func=lambda p: f"{p['namn']} ({p['roll']})", key="fv_person")
                    fv_typ = st.selectbox("Typ", list(FRANVARO_TYPER.keys()),
                        format_func=lambda t: f"{FRANVARO_TYPER[t]['ikon']} {FRANVARO_TYPER[t]['namn']}")
                with c2:
                    fv_fran = st.date_input("Från datum", value=date.today(), key="fv_fran")
                    fv_till = st.date_input("Till datum", value=date.today(), key="fv_till")
                fv_not = st.text_input("Notering (valfritt)", placeholder="T.ex. 'Fjällsemester'")

                if st.form_submit_button("Registrera frånvaro", type="primary"):
                    dagar = hamta_arbetsdagar(fv_fran, fv_till)
                    if dagar:
                        bulk_franvaro(fv_person["id"], dagar, fv_typ, fv_not)
                        st.success(f"{FRANVARO_TYPER[fv_typ]['ikon']} {fv_person['namn']} frånvarande {len(dagar)} arbetsdagar ({fv_typ})")
                        st.rerun()
                    else:
                        st.warning("Inga arbetsdagar i valt intervall.")

        # Ta bort frånvaro
        with st.expander("Ta bort frånvaro", expanded=False):
            with st.form("ta_bort_franvaro_form"):
                c1, c2, c3 = st.columns(3)
                with c1: tb_person = st.selectbox("Medarbetare", personal, format_func=lambda p: p["namn"], key="tb_p")
                with c2: tb_fran = st.date_input("Från", value=date.today(), key="tb_fran")
                with c3: tb_till = st.date_input("Till", value=date.today(), key="tb_till")
                if st.form_submit_button("Ta bort frånvaro"):
                    ta_bort_franvaro(tb_person["id"], tb_fran, tb_till)
                    st.success("Frånvaro borttagen."); st.rerun()

        st.markdown("---")

        # Visa frånvaro
        st.markdown("### Kommande frånvaro (30 dagar)")
        kommande = hamta_franvaro(fran_datum=date.today(), till_datum=date.today() + timedelta(days=30))
        if kommande:
            for f in kommande:
                info = FRANVARO_TYPER.get(f["typ"], FRANVARO_TYPER["ovrigt"])
                st.markdown(
                    f'<div class="alert-info">{info["ikon"]} <b>{f["personal_namn"]}</b> '
                    f'{f["datum"]} — {info["namn"]}'
                    f'{" (" + f["notering"] + ")" if f["notering"] else ""}</div>',
                    unsafe_allow_html=True)
        else:
            st.info("Ingen frånvaro registrerad de närmaste 30 dagarna.")

        # Frånvarodiagram
        st.markdown("---")
        st.markdown("### Frånvaroöversikt (3 månader)")
        fv_chart = skapa_franvaro_oversikt(date.today(), date.today() + timedelta(days=90))
        if fv_chart:
            fv_chart.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                                   font=dict(family="Inter", size=12), title=None)
            st.plotly_chart(fv_chart, use_container_width=True)


# ============================================================
# SIDA: TEAMÖVERSIKT (Gantt-liknande + lediga resurser)
# ============================================================

elif sida == "Teamöversikt":
    page_header("Teamöversikt", "Se hela teamet på en tidslinje — vem gör vad?")

    c1, c2 = st.columns(2)
    with c1: to_start = st.date_input("Från", value=date.today(), key="to_fran")
    with c2: to_slut = st.date_input("Till", value=date.today() + timedelta(days=13), key="to_till")

    arbetsdagar = hamta_arbetsdagar(to_start, to_slut)
    personal = hamta_all_personal()

    if not personal:
        st.info("Lägg till personal först.")
    elif not arbetsdagar:
        st.info("Inga arbetsdagar i perioden.")
    else:
        # Gantt-diagram
        st.markdown("### Tidslinje")
        gantt = skapa_gantt_oversikt(to_start, to_slut, arbetsdagar)
        if gantt:
            gantt.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                               font=dict(family="Inter", size=12))
            st.plotly_chart(gantt, use_container_width=True)

        st.markdown("---")

        # Tabell: vem gör vad
        st.markdown("### Detaljerad översikt")
        oversikt = hamta_teamoversikt(to_start, to_slut, arbetsdagar)

        for pid, pdata in oversikt.items():
            with st.expander(f"{pdata['namn']} — {pdata['roll']}"):
                rows = []
                for dag in arbetsdagar:
                    dag_str = str(dag)
                    if dag_str in pdata["dagar"]:
                        dd = pdata["dagar"][dag_str]
                        if dd["franvaro"]:
                            info = FRANVARO_TYPER.get(dd["franvaro"], FRANVARO_TYPER["ovrigt"])
                            rows.append({"Datum": dag_str, "Veckodag": VECKODAG_NAMN[dag.weekday()],
                                        "Status": f"{info['ikon']} {info['namn']}", "Timmar": "-"})
                        elif dd["allokeringar"]:
                            proj_str = ", ".join(f"{a['projekt']} ({a['timmar']}h)" for a in dd["allokeringar"])
                            total = sum(a["timmar"] for a in dd["allokeringar"])
                            rows.append({"Datum": dag_str, "Veckodag": VECKODAG_NAMN[dag.weekday()],
                                        "Status": proj_str, "Timmar": f"{total:.1f}h"})
                        else:
                            rows.append({"Datum": dag_str, "Veckodag": VECKODAG_NAMN[dag.weekday()],
                                        "Status": "Ledig", "Timmar": "0h"})
                if rows:
                    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

        st.markdown("---")

        # Lediga resurser per dag
        st.markdown("### Lediga resurser")
        vald_dag = st.date_input("Välj dag", value=date.today(), key="ledig_dag")
        lediga = hamta_lediga_resurser(vald_dag)
        if lediga:
            for l in lediga:
                pct = (l["ledigt"] / l["kapacitet_h"]) * 100
                st.markdown(f'<div class="alert-success">&#9989; <b>{l["namn"]}</b> ({l["roll"]}) '
                           f'— {l["ledigt"]:.1f}h ledigt ({pct:.0f}%)</div>', unsafe_allow_html=True)
        else:
            st.info(f"Alla är fullbelagda eller frånvarande {vald_dag}.")


# ============================================================
# SIDA: DASHBOARD
# ============================================================

elif sida == "Dashboard":
    page_header("Dashboard", "Beläggningsanalys och teamöversikt")

    c1, c2 = st.columns(2)
    with c1: ds = st.date_input("Från", value=date.today(), key="df")
    with c2: de = st.date_input("Till", value=date.today() + timedelta(days=60), key="dt")

    if ds >= de:
        st.error("Startdatum måste vara före slutdatum.")
    else:
        personal = hamta_all_personal()
        if not personal:
            st.info("Lägg till personal först.")
        else:
            st.markdown("---")
            st.markdown("### Beläggning per person och vecka")
            hm = skapa_belaggnings_heatmap(ds, de)
            if hm:
                hm.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                    font=dict(family="Inter", size=12), title=None, margin=dict(l=120, t=20))
                st.plotly_chart(hm, use_container_width=True)
            else: st.info("Ingen data.")

            st.markdown("---")
            st.markdown("### Team-allokering per vecka")
            sb = skapa_team_belaggning_stapel(ds, de)
            if sb:
                sb.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                    font=dict(family="Inter", size=12), title=None, margin=dict(t=20))
                st.plotly_chart(sb, use_container_width=True)
            else: st.info("Inga allokeringar.")

            st.markdown("---")
            st.markdown("### Individuell analys")
            vp = st.selectbox("Välj medarbetare", personal,
                format_func=lambda p: f"{p['namn']} ({p['roll']})", key="dp")
            if vp:
                pie = skapa_person_belaggning_pie(vp["id"], ds, de)
                if pie:
                    pie.update_layout(paper_bgcolor='rgba(0,0,0,0)', font=dict(family="Inter", size=12), title=None)
                    st.plotly_chart(pie, use_container_width=True)
                else: st.info(f"Inga allokeringar för {vp['namn']}.")

            st.markdown("---")
            st.markdown("### Kapacitetsvarningar")
            varn = skapa_kapacitetsvarningar(ds, de)
            if varn.empty:
                st.markdown('<div class="alert-success">&#9989; Inga varningar!</div>', unsafe_allow_html=True)
            else:
                for _, v in varn.iterrows():
                    st.markdown(f'<div class="alert-danger">&#9888;&#65039; <b>{v["personal_namn"]}</b> '
                        f'{v["datum"]}: {v["total_timmar"]:.1f}h (kap: {v["kapacitet_h"]:.1f}h, '
                        f'+{v["overtid"]:.1f}h)</div>', unsafe_allow_html=True)


# ============================================================
# SIDA: EXPORT
# ============================================================

elif sida == "Export":
    page_header("Export", "Exportera data till CSV och PDF")

    c1, c2 = st.columns(2)
    with c1: es = st.date_input("Från", value=date.today().replace(day=1), key="ef")
    with c2: ee = st.date_input("Till", value=date.today() + timedelta(days=30), key="et")
    st.markdown("---")

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("### CSV-exporter")
        st.download_button("&#128196; Allokeringar", exportera_allokeringar_csv(es, ee),
            file_name=f"allokeringar_{es}_{ee}.csv", mime="text/csv", use_container_width=True)
        st.download_button("&#128101; Personal", exportera_personal_csv(),
            file_name="personalregister.csv", mime="text/csv", use_container_width=True)
        st.download_button("&#128202; Beläggning", exportera_belaggningsrapport_csv(es, ee),
            file_name=f"belaggning_{es}_{ee}.csv", mime="text/csv", use_container_width=True)
    with c2:
        st.markdown("### PDF-rapport")
        try:
            pdf = generera_pdf_rapport(es, ee)
            st.download_button("&#128209; Ladda ner PDF", pdf,
                file_name=f"rapport_{es}_{ee}.pdf", mime="application/pdf", use_container_width=True)
        except Exception as e:
            st.error(f"PDF-fel: {e}")
