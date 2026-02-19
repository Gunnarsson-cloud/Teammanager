# Teammanager

Resursplaneringsapp for teamledare (15+ resurser). Ersatter Excel med en modern webbaserad losning.

## Funktioner

- **Svensk kalender** - 5-arskalender med roda dagar (holidays-lib)
- **Personalhantering** - CRUD med roller, kapacitet och kompetenstaggar
- **Projekthantering** - Fargkodade projekt med start/slutdatum
- **Allokering** - Tilldela timmar per person/projekt/dag
- **Dashboard** - Plotly heatmaps, stapeldiagram och kapacitetsvarningar
- **Export** - CSV och PDF-rapporter

## Teknikstack

| Bibliotek | Syfte |
|-----------|-------|
| Streamlit | UI-ramverk |
| Pandas | Datatransformation |
| Plotly | Interaktiva diagram |
| holidays | Svenska helgdagar |
| SQLite | Persistent lagring |
| fpdf2 | PDF-generering |

## Kor lokalt

```bash
pip install -r requirements.txt
streamlit run app.py
```

Oppna http://localhost:8501 i webblasaren.

## Deploya till Streamlit Cloud

1. Ga till [share.streamlit.io](https://share.streamlit.io)
2. Logga in med ditt GitHub-konto
3. Valj detta repo, branch `master`, fil `app.py`
4. Klicka **Deploy**

Appen ar live inom 1-2 minuter.
