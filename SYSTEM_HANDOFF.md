# System State & Handoff Document
## Teammanager - Resursplaneringsapplikation v2.0

> **Syfte:** Detta dokument innehåller allt en framtida utvecklare eller LLM behöver
> för att underhålla, felsöka och vidareutveckla applikationen utan att gissa.

---

## 1. Projektöversikt

| Egenskap | Värde |
|----------|-------|
| **Namn** | Teammanager |
| **Version** | 2.0 |
| **Språk** | Python 3.10+ |
| **Ramverk** | Streamlit (wide layout, single-page app) |
| **Databas** | SQLite (fil: `teammanager.db`, skapas automatiskt) |
| **Hosting** | Streamlit Community Cloud |
| **Repo** | github.com/Gunnarsson-cloud/Teammanager |
| **Branch** | master |
| **Entry point** | `app.py` |
| **Målgrupp** | Team Leader med 15 resurser, ersätter Excel |

---

## 2. Arkitektur

### 2.1 Systemdiagram

```
Webbläsare (Streamlit UI)
        |
        v
+------------------+
|     app.py       |  <-- Streamlit entry point, routing, UI, CSS
|  (882 rader)     |
+--------+---------+
         |
    importerar
         |
  +------+------+------+------+
  |      |      |      |      |
  v      v      v      v      v
database.py  calendar_utils.py  charts.py  export_utils.py
(SQLite CRUD) (Helgdagar/Dagar) (Plotly)   (CSV/PDF)
  |
  v
teammanager.db (SQLite)
```

### 2.2 Dataflöde

```
1. Användare -> Streamlit widgets (formulär, selectbox, date_input, number_input)
2. Streamlit -> Python-funktion i database.py (SQLite read/write via sqlite3)
3. database.py -> returnerar list[dict] (via sqlite3.Row -> dict)
4. app.py -> Skickar data till charts.py (Plotly) eller export_utils.py (CSV/PDF)
5. Plotly/Pandas -> Renderas i Streamlit via st.plotly_chart() / st.download_button()
```

### 2.3 Sidnavigation (st.sidebar.radio)

| Sida | Ikon | Beskrivning |
|------|------|-------------|
| Kalender | &#128197; | Svensk månadskalender med röda dagar, helger, arbetsdagar |
| Resurser | &#128101; | CRUD för personal med roll, kapacitet, kompetenstaggar |
| Projekt | &#128188; | CRUD för projekt med färg, start/slutdatum |
| Allokering | &#128203; | Tilldela timmar per person/projekt/dag med kapacitetsvarningar |
| Dashboard | &#128202; | Plotly heatmap, stapeldiagram, cirkeldiagram, varningslista |
| Export | &#128229; | Ladda ner CSV (3 typer) och PDF-rapport |

---

## 3. Filstruktur & Ansvar

```
Teammanager/
├── app.py                  # 882 rader - Streamlit UI, routing, CSS-styling
├── database.py             # 296 rader - Alla SQLite CRUD-operationer
├── calendar_utils.py       # 105 rader - Svenska helgdagar, arbetsdagsberäkningar
├── charts.py               # 209 rader - Plotly heatmap, stapel, pie, varningar
├── export_utils.py         # 194 rader - CSV-export (3 typer) + PDF-rapport
├── requirements.txt        #   5 rader - Python-beroenden
├── .gitignore              #  10 rader - Ignorerar __pycache__, .db, .env
├── README.md               #  41 rader - Setup och deploy-guide
├── SYSTEM_HANDOFF.md       # Detta dokument
└── teammanager.db          # Skapas vid körning (gitignored)
```

---

## 4. Databas-schema (SQLite: `teammanager.db`)

Databasen initieras av `database.init_db()` vid varje appstart med `CREATE TABLE IF NOT EXISTS`.
Foreign keys är aktiverade via `PRAGMA foreign_keys = ON`.
Alla borttagningar kaskaderar (ON DELETE CASCADE).

### 4.1 Tabell: `personal`

```sql
CREATE TABLE personal (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    namn          TEXT NOT NULL UNIQUE,
    roll          TEXT DEFAULT '',
    kapacitet_h   REAL DEFAULT 8.0,
    aktiv         INTEGER DEFAULT 1,
    skapad_datum  TEXT DEFAULT (date('now'))
);
```

| Kolumn | Typ | Constraint | Beskrivning |
|--------|-----|-----------|-------------|
| id | INTEGER | PK, AUTOINCREMENT | Unikt ID |
| namn | TEXT | NOT NULL, UNIQUE | Medarbetarens fullständiga namn |
| roll | TEXT | DEFAULT '' | Arbetsroll/titel (t.ex. "Utvecklare") |
| kapacitet_h | REAL | DEFAULT 8.0 | Max arbetstimmar per dag |
| aktiv | INTEGER | DEFAULT 1 | 1=aktiv, 0=inaktiv (soft delete) |
| skapad_datum | TEXT | DEFAULT date('now') | ISO-datum (YYYY-MM-DD) |

### 4.2 Tabell: `projekt`

```sql
CREATE TABLE projekt (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    namn          TEXT NOT NULL UNIQUE,
    farg          TEXT DEFAULT '#3498db',
    startdatum    TEXT,
    slutdatum     TEXT,
    aktiv         INTEGER DEFAULT 1
);
```

| Kolumn | Typ | Constraint | Beskrivning |
|--------|-----|-----------|-------------|
| id | INTEGER | PK, AUTOINCREMENT | Unikt ID |
| namn | TEXT | NOT NULL, UNIQUE | Projektnamn |
| farg | TEXT | DEFAULT '#3498db' | HEX-färgkod (används i diagram och UI) |
| startdatum | TEXT | nullable | ISO-datum |
| slutdatum | TEXT | nullable | ISO-datum |
| aktiv | INTEGER | DEFAULT 1 | 1=aktivt, 0=avslutat |

### 4.3 Tabell: `allokering`

```sql
CREATE TABLE allokering (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    personal_id   INTEGER NOT NULL,
    projekt_id    INTEGER NOT NULL,
    datum         TEXT NOT NULL,
    timmar        REAL NOT NULL DEFAULT 0,
    FOREIGN KEY (personal_id) REFERENCES personal(id) ON DELETE CASCADE,
    FOREIGN KEY (projekt_id) REFERENCES projekt(id) ON DELETE CASCADE,
    UNIQUE(personal_id, projekt_id, datum)
);
```

| Kolumn | Typ | Constraint | Beskrivning |
|--------|-----|-----------|-------------|
| id | INTEGER | PK, AUTOINCREMENT | Unikt ID |
| personal_id | INTEGER | FK -> personal.id, CASCADE | Koppling till medarbetare |
| projekt_id | INTEGER | FK -> projekt.id, CASCADE | Koppling till projekt |
| datum | TEXT | NOT NULL | ISO-datum (YYYY-MM-DD) |
| timmar | REAL | NOT NULL, DEFAULT 0 | Allokerade timmar (0.5-steg) |
| | | UNIQUE(personal_id, projekt_id, datum) | En person kan bara ha en allokering per projekt per dag |

**Upsert-logik:** `satt_allokering()` använder `ON CONFLICT ... DO UPDATE`. Om timmar=0 raderas posten istället.

### 4.4 Tabell: `kompetenser`

```sql
CREATE TABLE kompetenser (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    personal_id   INTEGER NOT NULL,
    tagg          TEXT NOT NULL,
    FOREIGN KEY (personal_id) REFERENCES personal(id) ON DELETE CASCADE,
    UNIQUE(personal_id, tagg)
);
```

| Kolumn | Typ | Constraint | Beskrivning |
|--------|-----|-----------|-------------|
| id | INTEGER | PK, AUTOINCREMENT | Unikt ID |
| personal_id | INTEGER | FK -> personal.id, CASCADE | Koppling till medarbetare |
| tagg | TEXT | NOT NULL | Kompetenstagg (t.ex. "Python", "Projektledning") |
| | | UNIQUE(personal_id, tagg) | En person kan inte ha dubbletter |

**Ersättningslogik:** `satt_kompetenser()` raderar alla befintliga taggar och lägger in de nya (full replace).

### 4.5 ER-Diagram (relationer)

```
personal 1──* allokering *──1 projekt
personal 1──* kompetenser
```

---

## 5. Modul-för-modul-dokumentation

### 5.1 `database.py` - Databaslager

**Anslutningshantering:**
- `DB_PATH` = `teammanager.db` i samma mapp som scriptet
- `get_connection()` returnerar `sqlite3.Connection` med `row_factory = sqlite3.Row`
- Varje funktion öppnar och stänger sin egen connection (ej persistent)

**Funktioner:**

| Funktion | Signatur | Returnerar | Beskrivning |
|----------|----------|-----------|-------------|
| `init_db()` | `()` | `None` | Skapar alla 4 tabeller om de inte finns |
| `hamta_all_personal()` | `(bara_aktiva=True)` | `list[dict]` | Alla medarbetare, sorterat på namn |
| `lagg_till_personal()` | `(namn, roll, kapacitet_h)` | `int \| None` | Nytt ID eller None vid duplikat |
| `uppdatera_personal()` | `(id, namn, roll, kap, aktiv)` | `bool` | True vid OK, False vid duplikat |
| `ta_bort_personal()` | `(person_id)` | `None` | Kaskaderar bort allokeringar + kompetenser |
| `hamta_alla_projekt()` | `(bara_aktiva=True)` | `list[dict]` | Alla projekt, sorterat på namn |
| `lagg_till_projekt()` | `(namn, farg, start, slut)` | `int \| None` | Nytt ID eller None vid duplikat |
| `uppdatera_projekt()` | `(id, namn, farg, start, slut, aktiv)` | `bool` | True/False |
| `ta_bort_projekt()` | `(projekt_id)` | `None` | Kaskaderar bort allokeringar |
| `hamta_allokeringar()` | `(personal_id, projekt_id, fran, till)` | `list[dict]` | Joinad data med namn och färger |
| `satt_allokering()` | `(personal_id, projekt_id, datum, timmar)` | `None` | Upsert; timmar=0 raderar |
| `hamta_dagsbelastning()` | `(personal_id, datum)` | `float` | SUM(timmar) för person+datum |
| `hamta_kompetenser()` | `(personal_id)` | `list[str]` | Alla taggar för en person |
| `hamta_alla_kompetenser()` | `()` | `list[str]` | Alla unika taggar i systemet |
| `satt_kompetenser()` | `(personal_id, taggar)` | `None` | Full replace av personens taggar |

**`hamta_allokeringar()` returnerar dict med nycklarna:**
```python
{
    "id", "personal_id", "projekt_id", "datum", "timmar",
    "personal_namn", "projekt_namn", "projekt_farg", "kapacitet_h"
}
```

### 5.2 `calendar_utils.py` - Kalenderberäkningar

**Cachning:** `hamta_svenska_helgdagar()` är dekorerad med `@lru_cache(maxsize=10)`.

| Funktion | Signatur | Returnerar | Beskrivning |
|----------|----------|-----------|-------------|
| `hamta_svenska_helgdagar()` | `(ar_start, ar_slut)` | `dict{date: str}` | Alla röda dagar via `holidays.Sweden()` |
| `ar_arbetsdag()` | `(datum, helgdagar=None)` | `bool` | True om mån-fre och inte helgdag |
| `hamta_arbetsdagar()` | `(fran, till)` | `list[date]` | Alla arbetsdagar i intervallet |
| `antal_arbetsdagar_i_manad()` | `(ar, manad)` | `int` | Antal arbetsdagar i en månad |
| `skapa_manadskalender()` | `(ar, manad)` | `list[dict]` | Daginfo med typ, veckodag, helgnamn |

**`skapa_manadskalender()` returnerar dagar med:**
```python
{
    "datum": date,        # Python date-objekt
    "dag": int,           # Dagnummer (1-31)
    "veckodag": int,      # 0=Måndag, 6=Söndag
    "typ": str,           # "arbetsdag" | "helg" | "rod_dag"
    "helgdagsnamn": str,  # "" eller "Nyårsdagen" etc.
    "vecka": int           # ISO-veckonummer
}
```

**Konstanter:**
- `VECKODAG_NAMN = ["Mån", "Tis", "Ons", "Tor", "Fre", "Lör", "Sön"]`
- `MANAD_NAMN = ["", "Januari", ..., "December"]` (index 0 är tom)

### 5.3 `charts.py` - Plotly-visualiseringar

| Funktion | Signatur | Returnerar | Beskrivning |
|----------|----------|-----------|-------------|
| `skapa_belaggnings_heatmap()` | `(fran, till)` | `go.Figure \| None` | Heatmap: personal x veckor, färg=beläggning% |
| `skapa_team_belaggning_stapel()` | `(fran, till)` | `go.Figure \| None` | Stacked bar: vecka x timmar, uppdelat per projekt |
| `skapa_person_belaggning_pie()` | `(personal_id, fran, till)` | `go.Figure \| None` | Pie chart: tidsfördelning per projekt |
| `skapa_kapacitetsvarningar()` | `(fran, till)` | `pd.DataFrame` | Alla dagar med överbeläggning |

**Heatmap-färgskala:**
```
0%   = #f0f0f0 (ljusgrå)
25%  = #a8d5e2 (ljusblå)
50%  = #2ecc71 (grön)
75%  = #f39c12 (orange)
100% = #e74c3c (röd)
zmax = 120 (tillåter visning av överbeläggning)
```

**Beläggningsformel (heatmap):**
```python
for varje person och vecka:
    arbetsdagar_i_vecka = antal vardagar som inte är helgdagar
    allokerade_timmar = SUM(allokering.timmar) för den personens dagar i veckan
    max_timmar = arbetsdagar_i_vecka * person.kapacitet_h
    beläggning% = (allokerade_timmar / max_timmar) * 100
```

**Kapacitetsvarningar returnerar DataFrame med kolumner:**
```
personal_id, personal_namn, datum, kapacitet_h, total_timmar, overtid
```

### 5.4 `export_utils.py` - Export

| Funktion | Signatur | Returnerar | Beskrivning |
|----------|----------|-----------|-------------|
| `exportera_allokeringar_csv()` | `(fran, till)` | `bytes` | CSV: Personal, Projekt, Datum, Timmar |
| `exportera_personal_csv()` | `()` | `bytes` | CSV: Namn, Roll, Kapacitet, Aktiv, Kompetenser, Skapad |
| `exportera_belaggningsrapport_csv()` | `(fran, till)` | `bytes` | CSV: Per person med beläggnings% |
| `generera_pdf_rapport()` | `(fran, till)` | `bytes` | PDF med tabell + sammanfattning |

**CSV-format:**
- Encoding: `utf-8-sig` (BOM för Excel-kompatibilitet)
- Separator: `;` (semikolon, för svenska Excel)

**PDF-struktur (generera_pdf_rapport):**
1. Titel: "Teammanager - Belaggningsrapport"
2. Period och antal arbetsdagar
3. Tabell: Personal | Roll | Tillg.(h) | Allok.(h) | Belaggn.%
4. Varannan rad ljusgrå bakgrund
5. Sammanfattning: antal resurser, total tid, snittbeläggning
6. Footer med genereringsdatum

### 5.5 `app.py` - Huvudapplikation

**Struktur (uppifrån och ner):**

| Radintervall | Innehåll |
|-------------|----------|
| 1-30 | Imports och konfiguration |
| 31-42 | `st.set_page_config()` och `init_db()` |
| 44-278 | CSS-styling (Modern 2026 design) |
| 282-329 | Sidebar: branding, navigation, stats |
| 332-343 | Hjälpfunktion `page_header()` |
| 346-424 | **Sida: Kalender** - CSS Grid-kalender med helgdagar |
| 427-523 | **Sida: Resurser** - Personal CRUD med kompetenstaggar |
| 526-611 | **Sida: Projekt** - Projekt CRUD med färgval |
| 614-722 | **Sida: Allokering** - Timmar per dag/person/projekt |
| 725-813 | **Sida: Dashboard** - Plotly-diagram och varningar |
| 816-882 | **Sida: Export** - CSV/PDF-nedladdningsknappar |

---

## 6. UI/CSS-design (v2.0)

### 6.1 Designsystem

| Element | Teknik |
|---------|--------|
| Font | Inter (Google Fonts), vikter 300-800 |
| Accentfärg 1 | `#6C5CE7` (lila) |
| Accentfärg 2 | `#00B894` (grön) |
| Gradient | `135deg: #6C5CE7 -> #a29bfe -> #00B894` |
| Kort | Glassmorphism: `backdrop-filter: blur(12px)`, halvtransparent bakgrund |
| Radier | 16px (kort), 10px (knappar), 20px (taggar) |
| Skuggor | `0 8px 32px rgba(0,0,0,0.08)` |
| Hover | `transform: translateY(-2px)` med mjuk transition |

### 6.2 Sidebar

- Bakgrund: Mörk gradient (`#1e1e2e -> #2d2b55`)
- Branding: Gradient-text "Teammanager" + "RESOURCE PLANNING"
- Stats: Antal resurser och projekt med gradient-siffror
- Navigation: Radio-knappar med hover-effekt

### 6.3 Kalender-celler (CSS Grid)

| Typ | CSS-klass | Bakgrund |
|-----|-----------|----------|
| Arbetsdag | `.cal-work` | Gradient grå (`#dfe6e9 -> #f0f3f5`) |
| Helg | `.cal-weekend` | Gradient gul (`#ffeaa7 -> #fdcb6e`) |
| Röd dag | `.cal-holiday` | Gradient rosa (`#fd79a8 -> #e84393`), vit text |
| Idag | `.cal-today` | Extra lila box-shadow ring |
| Tom | `.cal-empty` | opacity: 0 |

### 6.4 Metric-kort

- Glassmorphism-bakgrund med blur
- Label: uppercase, 13px, 0.65 opacity
- Värde: 32px, font-weight 800, gradient-text
- Hover: lift 2px + starkare skugga

### 6.5 Alert-boxar

| Klass | Färg vänsterkant | Användning |
|-------|------------------|-----------|
| `.alert-success` | `#00b894` (grön) | Inga varningar |
| `.alert-warn` | `#fdcb6e` (gul) | Informationsmeddelanden |
| `.alert-danger` | `#e84393` (rosa) | Överbeläggning |

---

## 7. Algoritmer & Affärslogik

### 7.1 Arbetsdag-definition

```python
def ar_arbetsdag(datum):
    if datum.weekday() >= 5:     # Lördag (5) eller Söndag (6)
        return False
    if datum in svenska_helgdagar:  # holidays.Sweden()
        return False
    return True
```

### 7.2 Capacity Warning-algoritm

```python
# Körs i charts.skapa_kapacitetsvarningar():
for varje (personal_id, datum) kombination:
    total = SUM(allokering.timmar WHERE personal_id AND datum)
    kapacitet = personal.kapacitet_h   # Default 8.0h

    if total > kapacitet:
        varning(personal_namn, datum, total, kapacitet, overtid=total-kapacitet)
```

### 7.3 Allokering upsert

```python
def satt_allokering(personal_id, projekt_id, datum, timmar):
    if timmar <= 0:
        DELETE FROM allokering WHERE personal_id AND projekt_id AND datum
    else:
        INSERT ... ON CONFLICT(personal_id, projekt_id, datum)
        DO UPDATE SET timmar = excluded.timmar
```

### 7.4 Heatmap-beläggning per vecka

```python
for varje person:
    for varje vecka i perioden:
        arbetsdagar = [dag for dag in veckan if ar_arbetsdag(dag)]
        max_h = len(arbetsdagar) * person.kapacitet_h
        allokerat_h = SUM(alla allokeringar för personen under dessa dagar)
        belaggning_pct = (allokerat_h / max_h) * 100 if max_h > 0 else 0
```

---

## 8. Tekniska beroenden

### 8.1 Python-paket (requirements.txt)

| Paket | Version | Syfte | Importeras i |
|-------|---------|-------|-------------|
| streamlit | >=1.28.0 | Web UI-ramverk | app.py |
| pandas | >=2.0.0 | DataFrames, gruppering, export | charts.py, export_utils.py |
| plotly | >=5.15.0 | Interaktiva diagram (heatmap, bar, pie) | charts.py |
| holidays | >=0.34 | Svenska helgdagar (röda dagar) | calendar_utils.py |
| fpdf2 | >=2.7.0 | PDF-generering | export_utils.py |

### 8.2 Python standardbibliotek

| Paket | Används för |
|-------|-------------|
| sqlite3 | Databasanslutning |
| os | Filsökvägar (DB_PATH) |
| datetime | date, timedelta, datetime |
| functools | lru_cache (helgdagscachning) |
| io | BytesIO (export-buffertar) |

---

## 9. Deploy & Drift

### 9.1 Streamlit Community Cloud

- **URL:** `teammanager-stfn9tuicvkch4mulxcdpa.streamlit.app`
- **Repo:** `Gunnarsson-cloud/Teammanager`
- **Branch:** `master`
- **Main file:** `app.py`
- **Auto-deploy:** Ja, vid push till master

### 9.2 Köra lokalt

```bash
cd Teammanager
pip install -r requirements.txt
streamlit run app.py
# Öppna http://localhost:8501
```

### 9.3 Viktigt att veta

- SQLite-databasen (`teammanager.db`) skapas automatiskt vid första körning
- Streamlit Cloud har **ephemeral disk** - data sparas INTE permanent mellan deploys
- För produktionsbruk bör SQLite bytas mot PostgreSQL/MySQL
- `.gitignore` exkluderar `.db`-filer, `__pycache__/`, `.env`

---

## 10. Ändringslogg

### v1.0 (2026-02-19) - Initial release
- [x] Svensk kalender med holidays-biblioteket (5 år framåt)
- [x] CRUD för personal och projekt
- [x] Allokeringsvy per person/projekt/dag
- [x] Dashboard med Plotly heatmaps, stapeldiagram, pie charts
- [x] Kompetenstaggar per medarbetare
- [x] Kapacitetsvarningar (>kapacitet per dag)
- [x] Export: 3 CSV-typer + PDF-rapport
- [x] Publicerad till GitHub och Streamlit Cloud

### v2.0 (2026-02-19) - Modern UI redesign
- [x] Komplett CSS-redesign med glassmorphism och gradient-accenter
- [x] Mörk sidebar med gradient-branding
- [x] CSS Grid-kalender (ersätter st.columns) med hover-animationer
- [x] Idag-indikator (lila ring) i kalendern
- [x] Inter-font från Google Fonts
- [x] Gradient page headers
- [x] Glassmorphism metric-kort med gradient-text
- [x] Pill-formade kompetenstaggar med hover
- [x] Gradient alert-boxar (success/warn/danger)
- [x] Transparenta Plotly-diagram (smälter in i layouten)
- [x] Hover lift-effekt på knappar och kort

### Naturliga nästa steg (ej implementerat)
- [ ] Semester- och frånvarohantering (sjuk, VAB, tjänstledigt)
- [ ] Drag-and-drop allokering i kalendervy
- [ ] Användarautentisering (multi-user, lösenord)
- [ ] API-integration mot projektverktyg (Jira, Azure DevOps)
- [ ] Notifikationer vid överbeläggning (e-post/Teams)
- [ ] Budgetuppföljning per projekt (timmar vs. plan)
- [ ] Import från Excel för initial datamigration
- [ ] Persistent databas (PostgreSQL) för Streamlit Cloud
- [ ] Dark mode toggle (CSS-variabler finns förberedda)

---

## 11. Kända begränsningar

| Begränsning | Orsak | Lösning |
|------------|-------|---------|
| Data försvinner vid redeploy | Streamlit Cloud ephemeral disk | Migrera till PostgreSQL |
| Ingen autentisering | Ej implementerat | Lägg till `streamlit-authenticator` |
| Långsam heatmap vid stor data | O(n*m) loop i charts.py | Precompute med SQL-aggregering |
| PDF utan svenska tecken | fpdf2 Helvetica stöder ej å/ä/ö | Byt till Unicode-font (DejaVu) |
| Single-user | SQLite + Streamlit session | Multi-user kräver databas + auth |

---

*Dokumentet uppdaterat: 2026-02-19 | Version: 2.0*
*Total kodbas: ~1700 rader Python + 230 rader CSS*
