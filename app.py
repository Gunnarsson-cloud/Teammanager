"""
Teammanager - Resursplaneringsapplikation
==========================================
Huvudapplikation (Streamlit entry point).
Ersätter Excel-baserad resursplanering för ett team på 15 resurser.

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
    page_icon="\U0001F4CA",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initiera databasen
init_db()

# ============================================================
# STYLING
# ============================================================

st.markdown("""
<style>
    /* Kompakt sidopanel */
    .stSidebar .stRadio > label { font-size: 14px; }

    /* Kalender-styling */
    .cal-arbetsdag { background-color: #d4edda; padding: 4px 8px; border-radius: 4px;
                     margin: 1px; display: inline-block; min-width: 32px; text-align: center; }
    .cal-helg { background-color: #f8d7da; padding: 4px 8px; border-radius: 4px;
                margin: 1px; display: inline-block; min-width: 32px; text-align: center; color: #721c24; }
    .cal-rod-dag { background-color: #f5c6cb; padding: 4px 8px; border-radius: 4px;
                   margin: 1px; display: inline-block; min-width: 32px; text-align: center;
                   color: #721c24; font-weight: bold; }

    /* Kapacitetsvarning */
    .warning-box { background-color: #fff3cd; border-left: 4px solid #ffc107;
                   padding: 10px 15px; margin: 5px 0; border-radius: 4px; }
    .danger-box { background-color: #f8d7da; border-left: 4px solid #dc3545;
                  padding: 10px 15px; margin: 5px 0; border-radius: 4px; }

    /* Status-taggar */
    .tag { display: inline-block; padding: 2px 10px; border-radius: 12px;
           font-size: 12px; margin: 2px; }
    .tag-blue { background-color: #d1ecf1; color: #0c5460; }
    .tag-green { background-color: #d4edda; color: #155724; }
    .tag-orange { background-color: #fff3cd; color: #856404; }
    .tag-red { background-color: #f8d7da; color: #721c24; }
</style>
""", unsafe_allow_html=True)


# ============================================================
# SIDEBAR - NAVIGATION
# ============================================================

st.sidebar.title("Teammanager")
st.sidebar.markdown("---")

sida = st.sidebar.radio(
    "Navigering",
    ["Kalender", "Resurser", "Projekt", "Allokering", "Dashboard", "Export"],
    index=0
)

st.sidebar.markdown("---")
st.sidebar.caption("v1.0 | Resursplanering")

# Info i sidopanelen
personal_count = len(hamta_all_personal())
projekt_count = len(hamta_alla_projekt())
st.sidebar.metric("Aktiva resurser", personal_count)
st.sidebar.metric("Aktiva projekt", projekt_count)


# ============================================================
# SIDA: KALENDER
# ============================================================

if sida == "Kalender":
    st.title("Arbetskalender")
    st.caption("Svensk kalender med helgdagar och arbetsdagar")

    # Välj år och månad
    col1, col2 = st.columns(2)
    with col1:
        valt_ar = st.selectbox("År", range(date.today().year, date.today().year + 5), index=0)
    with col2:
        vald_manad = st.selectbox("Månad", range(1, 13), index=date.today().month - 1,
                                  format_func=lambda x: MANAD_NAMN[x])

    # Statistik för månaden
    arbetsdagar_manad = antal_arbetsdagar_i_manad(valt_ar, vald_manad)
    helgdagar = hamta_svenska_helgdagar(valt_ar, valt_ar)

    col1, col2, col3 = st.columns(3)
    col1.metric("Arbetsdagar", arbetsdagar_manad)

    # Räkna röda dagar i månaden
    roda_dagar_manad = sum(
        1 for d, namn in helgdagar.items()
        if d.month == vald_manad and d.year == valt_ar and d.weekday() < 5
    )
    col2.metric("Röda dagar (vardagar)", roda_dagar_manad)
    col3.metric("Total arbetstid (team)", f"{arbetsdagar_manad * 8 * personal_count}h")

    st.markdown("---")

    # Visa kalender
    dagar = skapa_manadskalender(valt_ar, vald_manad)

    # Rubrikrad
    header_cols = st.columns(7)
    for i, namn in enumerate(VECKODAG_NAMN):
        header_cols[i].markdown(f"**{namn}**")

    # Fyll ut tomma dagar i början
    forsta_veckodag = dagar[0]["veckodag"]

    dag_index = 0
    current_row_dagar = [None] * forsta_veckodag  # Fyll med tomma platser

    for dag_info in dagar:
        current_row_dagar.append(dag_info)

        if len(current_row_dagar) == 7:
            # Skriv ut raden
            cols = st.columns(7)
            for i, d in enumerate(current_row_dagar):
                if d is None:
                    cols[i].write("")
                else:
                    if d["typ"] == "arbetsdag":
                        cols[i].markdown(
                            f'<div class="cal-arbetsdag">{d["dag"]}</div>',
                            unsafe_allow_html=True
                        )
                    elif d["typ"] == "helg":
                        cols[i].markdown(
                            f'<div class="cal-helg">{d["dag"]}</div>',
                            unsafe_allow_html=True
                        )
                    else:  # rod_dag
                        cols[i].markdown(
                            f'<div class="cal-rod-dag">{d["dag"]}</div>',
                            unsafe_allow_html=True
                        )
                        cols[i].caption(d["helgdagsnamn"])
            current_row_dagar = []

    # Skriv ut sista ofullständiga raden
    if current_row_dagar:
        while len(current_row_dagar) < 7:
            current_row_dagar.append(None)
        cols = st.columns(7)
        for i, d in enumerate(current_row_dagar):
            if d is None:
                cols[i].write("")
            else:
                if d["typ"] == "arbetsdag":
                    cols[i].markdown(
                        f'<div class="cal-arbetsdag">{d["dag"]}</div>',
                        unsafe_allow_html=True
                    )
                elif d["typ"] == "helg":
                    cols[i].markdown(
                        f'<div class="cal-helg">{d["dag"]}</div>',
                        unsafe_allow_html=True
                    )
                else:
                    cols[i].markdown(
                        f'<div class="cal-rod-dag">{d["dag"]}</div>',
                        unsafe_allow_html=True
                    )
                    cols[i].caption(d["helgdagsnamn"])

    # Förklaring
    st.markdown("---")
    st.markdown(
        '<span class="cal-arbetsdag">Arbetsdag</span> '
        '<span class="cal-helg">Helg</span> '
        '<span class="cal-rod-dag">Röd dag</span>',
        unsafe_allow_html=True
    )

    # Visa röda dagar för hela året
    with st.expander(f"Alla röda dagar {valt_ar}"):
        for d in sorted(helgdagar.keys()):
            veckodag = VECKODAG_NAMN[d.weekday()]
            st.write(f"**{d}** ({veckodag}) - {helgdagar[d]}")


# ============================================================
# SIDA: RESURSER
# ============================================================

elif sida == "Resurser":
    st.title("Personalhantering")
    st.caption("Hantera teamets medarbetare och kompetenser")

    # Formulär för att lägga till personal
    with st.expander("Lägg till ny medarbetare", expanded=False):
        with st.form("ny_personal_form"):
            col1, col2, col3 = st.columns(3)
            with col1:
                nytt_namn = st.text_input("Namn *")
            with col2:
                ny_roll = st.text_input("Roll/Titel")
            with col3:
                ny_kap = st.number_input("Kapacitet (h/dag)", value=8.0, min_value=1.0,
                                         max_value=12.0, step=0.5)

            ny_kompetens_text = st.text_input(
                "Kompetenser (kommaseparerade)",
                placeholder="Python, JavaScript, Projektledning..."
            )

            if st.form_submit_button("Lägg till"):
                if nytt_namn.strip():
                    person_id = lagg_till_personal(nytt_namn, ny_roll, ny_kap)
                    if person_id:
                        # Spara kompetenser
                        if ny_kompetens_text.strip():
                            taggar = [t.strip() for t in ny_kompetens_text.split(",")]
                            satt_kompetenser(person_id, taggar)
                        st.success(f"'{nytt_namn}' tillagd!")
                        st.rerun()
                    else:
                        st.error(f"Kunde inte lägga till '{nytt_namn}'. Namnet kanske redan finns?")
                else:
                    st.warning("Namn är obligatoriskt.")

    st.markdown("---")

    # Visa befintlig personal
    visa_inaktiva = st.checkbox("Visa även inaktiva", value=False)
    personal = hamta_all_personal(bara_aktiva=not visa_inaktiva)

    if not personal:
        st.info("Inga medarbetare registrerade. Lägg till din första medarbetare ovan.")
    else:
        for person in personal:
            kompetenser = hamta_kompetenser(person["id"])
            status_text = "" if person["aktiv"] else " (Inaktiv)"

            with st.expander(f"{person['namn']} - {person['roll']}{status_text}"):
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

                    # Visa kompetenstaggar
                    if kompetenser:
                        tagg_html = " ".join(
                            f'<span class="tag tag-blue">{t}</span>' for t in kompetenser
                        )
                        st.markdown(tagg_html, unsafe_allow_html=True)

                    col_save, col_delete = st.columns([4, 1])
                    with col_save:
                        if st.form_submit_button("Spara"):
                            uppdatera_personal(person["id"], edit_namn, edit_roll,
                                             edit_kap, 1 if edit_aktiv else 0)
                            taggar = [t.strip() for t in edit_komp.split(",")]
                            satt_kompetenser(person["id"], taggar)
                            st.success("Uppdaterad!")
                            st.rerun()
                    with col_delete:
                        if st.form_submit_button("Ta bort", type="secondary"):
                            ta_bort_personal(person["id"])
                            st.success(f"'{person['namn']}' borttagen.")
                            st.rerun()


# ============================================================
# SIDA: PROJEKT
# ============================================================

elif sida == "Projekt":
    st.title("Projekthantering")
    st.caption("Hantera pågående och kommande projekt")

    # Formulär för nytt projekt
    with st.expander("Skapa nytt projekt", expanded=False):
        with st.form("nytt_projekt_form"):
            col1, col2 = st.columns(2)
            with col1:
                proj_namn = st.text_input("Projektnamn *")
                proj_farg = st.color_picker("Färg", value="#3498db")
            with col2:
                proj_start = st.date_input("Startdatum", value=date.today())
                proj_slut = st.date_input("Slutdatum",
                                          value=date.today() + timedelta(days=90))

            if st.form_submit_button("Skapa projekt"):
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

    # Visa projekt
    visa_avslutade = st.checkbox("Visa även avslutade projekt", value=False)
    projekt = hamta_alla_projekt(bara_aktiva=not visa_avslutade)

    if not projekt:
        st.info("Inga projekt registrerade. Skapa ditt första projekt ovan.")
    else:
        for proj in projekt:
            status_text = "" if proj["aktiv"] else " (Avslutat)"
            farg_preview = f'<span style="display:inline-block;width:14px;height:14px;background:{proj["farg"]};border-radius:50%;vertical-align:middle;margin-right:5px;"></span>'

            with st.expander(f'{proj["namn"]}{status_text}'):
                st.markdown(f'{farg_preview} **{proj["namn"]}**', unsafe_allow_html=True)

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
                        if st.form_submit_button("Spara"):
                            uppdatera_projekt(proj["id"], ep_namn, ep_farg,
                                            str(ep_start), str(ep_slut),
                                            1 if ep_aktiv else 0)
                            st.success("Projekt uppdaterat!")
                            st.rerun()
                    with col_delete:
                        if st.form_submit_button("Ta bort", type="secondary"):
                            ta_bort_projekt(proj["id"])
                            st.success(f"Projekt '{proj['namn']}' borttaget.")
                            st.rerun()


# ============================================================
# SIDA: ALLOKERING
# ============================================================

elif sida == "Allokering":
    st.title("Resursallokering")
    st.caption("Tilldela personal till projekt per dag")

    personal = hamta_all_personal()
    projekt = hamta_alla_projekt()

    if not personal:
        st.warning("Lägg till personal först under 'Resurser'.")
    elif not projekt:
        st.warning("Skapa projekt först under 'Projekt'.")
    else:
        # Välj period
        st.subheader("Välj period")
        col1, col2 = st.columns(2)
        with col1:
            allok_start = st.date_input("Från", value=date.today(),
                                        key="allok_fran")
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

                # Välj person att allokera
                person_val = st.selectbox(
                    "Välj medarbetare",
                    personal,
                    format_func=lambda p: f"{p['namn']} ({p['roll']})"
                )

                if person_val:
                    st.subheader(f"Allokering: {person_val['namn']}")

                    # Visa kapacitetsvarningar
                    for dag in arbetsdagar:
                        belastning = hamta_dagsbelastning(person_val["id"], dag)
                        if belastning > person_val["kapacitet_h"]:
                            overtid = belastning - person_val["kapacitet_h"]
                            st.markdown(
                                f'<div class="danger-box">&#9888; <strong>{dag}</strong>: '
                                f'Överbelagd med {overtid:.1f}h '
                                f'({belastning:.1f}h / {person_val["kapacitet_h"]:.1f}h)</div>',
                                unsafe_allow_html=True
                            )

                    # Allokeringstabell
                    st.markdown("---")
                    st.caption("Fyll i timmar per projekt och dag (0 = ingen allokering)")

                    # Skapa formulär per projekt
                    for proj in projekt:
                        farg_dot = f'<span style="display:inline-block;width:10px;height:10px;background:{proj["farg"]};border-radius:50%;margin-right:5px;"></span>'
                        st.markdown(f"#### {farg_dot} {proj['namn']}", unsafe_allow_html=True)

                        # Visa dagar i rader om max 7 per rad
                        for rad_start in range(0, len(arbetsdagar), 7):
                            rad_dagar = arbetsdagar[rad_start:rad_start + 7]
                            cols = st.columns(len(rad_dagar))

                            for i, dag in enumerate(rad_dagar):
                                veckodag = VECKODAG_NAMN[dag.weekday()]

                                # Hämta befintlig allokering
                                befintliga = hamta_allokeringar(
                                    personal_id=person_val["id"],
                                    projekt_id=proj["id"],
                                    fran_datum=dag,
                                    till_datum=dag
                                )
                                nuvarande = befintliga[0]["timmar"] if befintliga else 0.0

                                with cols[i]:
                                    nya_timmar = st.number_input(
                                        f"{veckodag} {dag.day}/{dag.month}",
                                        value=float(nuvarande),
                                        min_value=0.0,
                                        max_value=12.0,
                                        step=0.5,
                                        key=f"allok_{person_val['id']}_{proj['id']}_{dag}"
                                    )

                                    # Spara direkt vid förändring
                                    if nya_timmar != nuvarande:
                                        satt_allokering(person_val["id"], proj["id"],
                                                       dag, nya_timmar)

                        st.markdown("---")

                    # Sammanfattning för vald person och period
                    st.subheader("Sammanfattning")
                    total_allokerat = 0
                    per_projekt = {}

                    for proj in projekt:
                        allok = hamta_allokeringar(
                            personal_id=person_val["id"],
                            projekt_id=proj["id"],
                            fran_datum=allok_start,
                            till_datum=allok_slut
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
                        st.write("**Fördelning per projekt:**")
                        for proj_namn, timmar in per_projekt.items():
                            st.write(f"- {proj_namn}: {timmar:.1f}h")


# ============================================================
# SIDA: DASHBOARD
# ============================================================

elif sida == "Dashboard":
    st.title("Dashboard")
    st.caption("Beläggningsanalys och översikt")

    # Välj period
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
            # Beläggnings-heatmap
            st.subheader("Beläggning per person och vecka")
            heatmap = skapa_belaggnings_heatmap(dash_start, dash_slut)
            if heatmap:
                st.plotly_chart(heatmap, use_container_width=True)
            else:
                st.info("Ingen data att visa.")

            st.markdown("---")

            # Teambeläggning stapeldiagram
            st.subheader("Team-allokering per vecka")
            stapel = skapa_team_belaggning_stapel(dash_start, dash_slut)
            if stapel:
                st.plotly_chart(stapel, use_container_width=True)
            else:
                st.info("Inga allokeringar i perioden.")

            st.markdown("---")

            # Personlig beläggning
            st.subheader("Individuell analys")
            vald_person = st.selectbox(
                "Välj medarbetare",
                personal,
                format_func=lambda p: f"{p['namn']} ({p['roll']})",
                key="dash_person"
            )

            if vald_person:
                pie = skapa_person_belaggning_pie(vald_person["id"], dash_start, dash_slut)
                if pie:
                    st.plotly_chart(pie, use_container_width=True)
                else:
                    st.info(f"Inga allokeringar för {vald_person['namn']} i perioden.")

            st.markdown("---")

            # Kapacitetsvarningar
            st.subheader("Kapacitetsvarningar")
            varningar = skapa_kapacitetsvarningar(dash_start, dash_slut)

            if varningar.empty:
                st.success("Inga kapacitetsvarningar i perioden!")
            else:
                st.warning(f"{len(varningar)} överbelastade dagar hittade:")
                for _, v in varningar.iterrows():
                    st.markdown(
                        f'<div class="danger-box">&#9888; <strong>{v["personal_namn"]}</strong> '
                        f'den {v["datum"]}: {v["total_timmar"]:.1f}h allokerat '
                        f'(kapacitet: {v["kapacitet_h"]:.1f}h, '
                        f'övertid: {v["overtid"]:.1f}h)</div>',
                        unsafe_allow_html=True
                    )


# ============================================================
# SIDA: EXPORT
# ============================================================

elif sida == "Export":
    st.title("Export")
    st.caption("Exportera data till CSV och PDF")

    # Välj period
    st.subheader("Exportperiod")
    col1, col2 = st.columns(2)
    with col1:
        exp_start = st.date_input("Från", value=date.today().replace(day=1), key="exp_fran")
    with col2:
        exp_slut = st.date_input("Till",
                                 value=date.today() + timedelta(days=30),
                                 key="exp_till")

    st.markdown("---")

    # Export-knappar
    st.subheader("Tillgängliga exporter")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("#### CSV-exporter")

        # Allokeringar CSV
        csv_allok = exportera_allokeringar_csv(exp_start, exp_slut)
        st.download_button(
            label="Ladda ner allokeringar (CSV)",
            data=csv_allok,
            file_name=f"allokeringar_{exp_start}_{exp_slut}.csv",
            mime="text/csv"
        )

        # Personalregister CSV
        csv_personal = exportera_personal_csv()
        st.download_button(
            label="Ladda ner personalregister (CSV)",
            data=csv_personal,
            file_name="personalregister.csv",
            mime="text/csv"
        )

        # Beläggningsrapport CSV
        csv_belagg = exportera_belaggningsrapport_csv(exp_start, exp_slut)
        st.download_button(
            label="Ladda ner beläggningsrapport (CSV)",
            data=csv_belagg,
            file_name=f"belaggning_{exp_start}_{exp_slut}.csv",
            mime="text/csv"
        )

    with col2:
        st.markdown("#### PDF-rapport")
        st.write("Generera en komplett beläggningsrapport som PDF.")

        try:
            pdf_data = generera_pdf_rapport(exp_start, exp_slut)
            st.download_button(
                label="Ladda ner PDF-rapport",
                data=pdf_data,
                file_name=f"belaggningsrapport_{exp_start}_{exp_slut}.pdf",
                mime="application/pdf"
            )
        except ImportError:
            st.warning("PDF-export kräver `fpdf2`. Installera med: `pip install fpdf2`")
        except Exception as e:
            st.error(f"Kunde inte generera PDF: {e}")
