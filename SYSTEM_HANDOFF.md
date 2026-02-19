# System State & Handoff Document
## Teammanager - Resursplaneringsapplikation v1.0

---

## 1. Arkitekturöversikt

### Systemdesign
Applikationen är en **single-page Streamlit-app** med SQLite som persistent lagring.

```
[Streamlit UI] <-> [Python Backend Logic] <-> [SQLite Database]
       |                    |
       v                    v
  [Plotly Charts]    [Pandas DataFrames]
       |                    |
       v                    v
  [holidays lib]     [CSV/PDF Export]
```

### Dataflöde
1. **Input:** Användaren interagerar via Streamlit-widgets (formulär, selectboxes, date_input)
2. **Processing:** Python-funktioner läser/skriver till SQLite via `sqlite3`, transformerar data med `pandas`
3. **Output:** Plotly-diagram renderas i Streamlit, tabeller visas med `st.dataframe()`

### Sidnavigation (via st.sidebar)
- **Kalender** - Visa arbetskalender med röda dagar
- **Resurser** - Hantera personal och kompetenser
- **Projekt** - Hantera projekt
- **Allokering** - Tilldela personal till projekt per dag
- **Dashboard** - Beläggningsanalys med heatmaps
- **Export** - CSV/PDF-export av data

---

## 2. Databas-schema (SQLite: `teammanager.db`)

### Tabell: `personal`
| Kolumn        | Typ     | Beskrivning                     |
|---------------|---------|----------------------------------|
| id            | INTEGER | PRIMARY KEY AUTOINCREMENT        |
| namn          | TEXT    | Fullständigt namn (UNIQUE)       |
| roll          | TEXT    | Arbetsroll/titel                 |
| kapacitet_h   | REAL    | Max timmar per dag (default 8.0) |
| aktiv         | INTEGER | 1=aktiv, 0=inaktiv              |
| skapad_datum  | TEXT    | ISO-datum när posten skapades    |

### Tabell: `projekt`
| Kolumn        | Typ     | Beskrivning                      |
|---------------|---------|-----------------------------------|
| id            | INTEGER | PRIMARY KEY AUTOINCREMENT         |
| namn          | TEXT    | Projektnamn (UNIQUE)              |
| farg          | TEXT    | HEX-färgkod för visualisering    |
| startdatum    | TEXT    | Projektets startdatum             |
| slutdatum     | TEXT    | Projektets slutdatum              |
| aktiv         | INTEGER | 1=aktiv, 0=avslutat              |

### Tabell: `allokering`
| Kolumn        | Typ     | Beskrivning                      |
|---------------|---------|-----------------------------------|
| id            | INTEGER | PRIMARY KEY AUTOINCREMENT         |
| personal_id   | INTEGER | FK -> personal.id                 |
| projekt_id    | INTEGER | FK -> projekt.id                  |
| datum         | TEXT    | ISO-datum för allokeringen        |
| timmar        | REAL    | Antal allokerade timmar           |
| UNIQUE        |         | (personal_id, projekt_id, datum)  |

### Tabell: `kompetenser`
| Kolumn        | Typ     | Beskrivning                      |
|---------------|---------|-----------------------------------|
| id            | INTEGER | PRIMARY KEY AUTOINCREMENT         |
| personal_id   | INTEGER | FK -> personal.id                 |
| tagg          | TEXT    | Kompetenstagg (t.ex. "Python")   |
| UNIQUE        |         | (personal_id, tagg)               |

---

## 3. Logik-beskrivning

### Svenska helgdagar
- Använder biblioteket `holidays` med `holidays.Sweden(years=range(start, slut))`
- Genererar alla svenska röda dagar inklusive rörliga (Påsk, Midsommar, etc.)
- Arbetsdagar = Alla dagar som INTE är lördag, söndag eller röd dag
- Kalendervy färgkodar: Röd=helg/röd dag, Grön=arbetsdag

### Capacity Warning-algoritm
```python
# För varje person och datum:
total_timmar = SUM(allokering.timmar) WHERE personal_id=X AND datum=Y
kapacitet = personal.kapacitet_h  # Default 8.0

if total_timmar > kapacitet:
    status = "ÖVERBELAGD"  # Röd varning
elif total_timmar == kapacitet:
    status = "FULLT"       # Gul
elif total_timmar > 0:
    status = "DELVIS"      # Blå
else:
    status = "LEDIG"       # Grå
```

### Beläggningsberäkning (Dashboard)
- **Per person:** `beläggning% = (allokerade_timmar / tillgängliga_arbetsdagar * kapacitet) * 100`
- **Per team:** Genomsnitt av alla personers beläggning
- Heatmap: X-axel=veckor, Y-axel=personal, färg=beläggningsgrad

---

## 4. Ändringslogg

### v1.0 (Initial release)
- [x] Våg 1: Svensk kalender med holidays-biblioteket (5 år)
- [x] Våg 2: CRUD för personal och projekt, allokeringsvy
- [x] Våg 3: Dashboard med Plotly heatmaps
- [x] Våg 4: Kompetenstaggar, kapacitetsvarningar, CSV/PDF-export

### Naturliga nästa steg
- [ ] Semester- och frånvarohantering (sjuk, VAB, tjänstledigt)
- [ ] Drag-and-drop allokering i kalendervy
- [ ] Användarautentisering (multi-user)
- [ ] API-integration mot projektverktyg (Jira, Azure DevOps)
- [ ] Notifikationer vid överbeläggning (e-post/Teams)
- [ ] Budgetuppföljning per projekt (timmar vs. plan)
- [ ] Import från Excel för initial migration

---

## 5. Filstruktur

```
Teammanager/
├── app.py                  # Huvudapplikation (Streamlit entry point)
├── database.py             # Databashantering (SQLite CRUD)
├── calendar_utils.py       # Kalenderberäkningar och helgdagar
├── charts.py               # Plotly-diagram och visualiseringar
├── export_utils.py         # Export till CSV och PDF
├── requirements.txt        # Python-beroenden
├── SYSTEM_HANDOFF.md       # Detta dokument
└── teammanager.db          # SQLite-databas (skapas vid första körning)
```

---

## 6. Tekniska beroenden

| Bibliotek    | Version  | Syfte                          |
|-------------|----------|--------------------------------|
| streamlit   | >=1.28   | Web-ramverk / UI               |
| pandas      | >=2.0    | Datatransformation             |
| plotly       | >=5.15   | Interaktiva diagram            |
| holidays    | >=0.34   | Svenska helgdagar              |
| fpdf2       | >=2.7    | PDF-generering                 |

---

*Dokumentet genererat: 2026-02-19 | Version: 1.0*
