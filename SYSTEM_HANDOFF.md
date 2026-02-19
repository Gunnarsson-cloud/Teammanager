# System State & Handoff Document
## Teammanager - Resursplaneringsapplikation v3.0

> **Syfte:** Detta dokument innehåller ALLT en framtida utvecklare eller LLM behöver
> för att underhålla, felsöka och vidareutveckla applikationen utan att gissa.
> Varje fil, funktion, tabell, CSS-klass och algoritm är dokumenterad.

---

## 1. Projektöversikt

| Egenskap | Värde |
|----------|-------|
| **Namn** | Teammanager |
| **Version** | 3.0 |
| **Språk** | Python 3.10+ |
| **Ramverk** | Streamlit (wide layout, single-page app med sidebar-navigation) |
| **Databas** | SQLite (fil: `teammanager.db`, skapas automatiskt vid start) |
| **Hosting** | Streamlit Community Cloud (auto-deploy vid push) |
| **Live URL** | `teammanager-stfn9tuicvkch4mulxcdpa.streamlit.app` |
| **Repo** | `github.com/Gunnarsson-cloud/Teammanager` |
| **Branch** | `master` |
| **Entry point** | `app.py` |
| **Målgrupp** | Team Leader med 15+ resurser, ersätter Excel-planering |
| **Ägare** | Andreas Gunnarsson (`a.e.gunnarsson@gmail.com`) |

---

## 2. Arkitektur

### 2.1 Systemdiagram

```
Webbläsare (Streamlit UI)
        |
        v
+-------------------+
|      app.py       |  <-- Streamlit entry point, routing, UI, ~230 rader CSS
|   (~860 rader)    |
+--------+----------+
         |
    importerar
         |
  +------+------+----------+-----------+
  |      |      |          |           |
  v      v      v          v           v
database.py  calendar_utils.py  charts.py  export_utils.py
(599 rad)    (105 rad)          (262 rad)  (194 rad)
SQLite CRUD  Helgdagar/Dagar    Plotly     CSV/PDF
  |
  v
teammanager.db (SQLite, 6 tabeller)
```

### 2.2 Dataflöde

```
1. Användare -> Streamlit widgets (formulär, selectbox, date_input, number_input, tabs)
2. Streamlit -> Python-funktion i database.py (SQLite read/write via sqlite3)
3. database.py -> returnerar list[dict] (via sqlite3.Row -> dict)
4. app.py -> Skickar data till charts.py (Plotly) eller export_utils.py (CSV/PDF)
5. Plotly/Pandas -> Renderas i Streamlit via st.plotly_chart() / st.download_button()
6. All Plotly: paper_bgcolor='rgba(0,0,0,0)' för transparent bakgrund
```

### 2.3 Sidnavigation (st.sidebar.radio)

Applikationen har **9 sidor** (v3.0), navigerade via `st.sidebar.radio("Navigering", NAV_ITEMS)`:

| # | Sida | Ikon | Beskrivning | Ny i v3? |
|---|------|------|-------------|----------|
| 1 | **Hem** | &#127968; | Smart startsida: KPI-kort, överbelagda, frånvarande, lediga resurser | **JA** |
| 2 | Kalender | &#128197; | Svensk månadskalender med röda dagar (CSS Grid) | Nej |
| 3 | Resurser | &#128101; | CRUD för personal med roll, kapacitet, kompetenstaggar | Nej |
| 4 | Projekt | &#128188; | CRUD för projekt med färgval, start/slutdatum | Nej |
| 5 | **Allokering** | &#128203; | 4 flikar: Snabballokering, Dag-för-dag, Kopiera vecka, Kommentarer | **UTÖKAD** |
| 6 | **Frånvaro** | &#127796; | Registrera/ta bort frånvaro, 30-dagarsvy, frånvarodiagram | **JA** |
| 7 | **Teamöversikt** | &#128200; | Gantt-tidslinje, detaljvy per person, lediga resurser per dag | **JA** |
| 8 | Dashboard | &#128202; | Plotly heatmap, stapeldiagram, cirkeldiagram, varningar | Nej |
| 9 | Export | &#128229; | Ladda ner CSV (3 typer) och PDF-rapport | Nej |

---

## 3. Filstruktur & Ansvar

```
Teammanager/
├── app.py                  # ~860 rader - Streamlit UI, routing, 9 sidor, ~230 rader CSS
├── database.py             #  599 rader - SQLite CRUD, 6 tabeller, ~30 funktioner
├── calendar_utils.py       #  105 rader - Svenska helgdagar, arbetsdagsberäkningar
├── charts.py               #  262 rader - 6 Plotly-diagram (heatmap, stapel, pie, gantt, frånvaro)
├── export_utils.py         #  194 rader - CSV-export (3 typer) + PDF-rapport
├── requirements.txt        #    5 rader - Python-beroenden (5 paket)
├── .gitignore              #   10 rader - Ignorerar __pycache__, .db, .env, venv
├── README.md               #   41 rader - Setup och deploy-guide
├── SYSTEM_HANDOFF.md       # Detta dokument (komplett teknisk handoff)
└── teammanager.db          # Skapas vid körning (gitignored, ej i repo)
```

---

## 4. Databas-schema (SQLite: `teammanager.db`)

Databasen initieras av `database.init_db()` vid varje appstart med `CREATE TABLE IF NOT EXISTS`.
Foreign keys är aktiverade via `PRAGMA foreign_keys = ON` i `get_connection()`.
Alla borttagningar kaskaderar (ON DELETE CASCADE).
Alla datum lagras som ISO-strängar (`YYYY-MM-DD`).

### 4.1 ER-Diagram (6 tabeller)

```
personal 1──* allokering *──1 projekt
personal 1──* kompetenser
personal 1──* franvaro          (NY i v3.0)
personal 1──* kommentarer       (NY i v3.0)
```

### 4.2 Tabell: `personal`

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
| kapacitet_h | REAL | DEFAULT 8.0 | Max arbetstimmar per dag (1.0-12.0, steg 0.5) |
| aktiv | INTEGER | DEFAULT 1 | 1=aktiv, 0=inaktiv (soft delete) |
| skapad_datum | TEXT | DEFAULT date('now') | ISO-datum (YYYY-MM-DD) |

### 4.3 Tabell: `projekt`

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

### 4.4 Tabell: `allokering`

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
| | | UNIQUE(personal_id, projekt_id, datum) | En post per person+projekt+dag |

**Upsert-logik:** `satt_allokering()` / `bulk_allokera()` använder `ON CONFLICT ... DO UPDATE SET timmar = excluded.timmar`. Om timmar <= 0 raderas posten istället (DELETE).

### 4.5 Tabell: `kompetenser`

```sql
CREATE TABLE kompetenser (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    personal_id   INTEGER NOT NULL,
    tagg          TEXT NOT NULL,
    FOREIGN KEY (personal_id) REFERENCES personal(id) ON DELETE CASCADE,
    UNIQUE(personal_id, tagg)
);
```

**Ersättningslogik:** `satt_kompetenser()` raderar alla befintliga taggar för personen och infogar de nya (full replace).

### 4.6 Tabell: `franvaro` (NY i v3.0)

```sql
CREATE TABLE franvaro (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    personal_id   INTEGER NOT NULL,
    datum         TEXT NOT NULL,
    typ           TEXT NOT NULL DEFAULT 'semester',
    notering      TEXT DEFAULT '',
    FOREIGN KEY (personal_id) REFERENCES personal(id) ON DELETE CASCADE,
    UNIQUE(personal_id, datum)
);
```

| Kolumn | Typ | Constraint | Beskrivning |
|--------|-----|-----------|-------------|
| id | INTEGER | PK, AUTOINCREMENT | Unikt ID |
| personal_id | INTEGER | FK -> personal.id, CASCADE | Koppling till medarbetare |
| datum | TEXT | NOT NULL | ISO-datum (YYYY-MM-DD) |
| typ | TEXT | NOT NULL, DEFAULT 'semester' | En av: semester, sjuk, vab, tjanstledig, utbildning, ovrigt |
| notering | TEXT | DEFAULT '' | Fritext (t.ex. "Fjällsemester") |
| | | UNIQUE(personal_id, datum) | Max en frånvaro per person och dag |

**Frånvarotyper (definierade i `database.FRANVARO_TYPER`):**

| Nyckel | Namn | Ikon | Färg |
|--------|------|------|------|
| `semester` | Semester | :palm_tree: | `#00b894` (grön) |
| `sjuk` | Sjuk | :face_with_thermometer: | `#e17055` (röd-orange) |
| `vab` | VAB | :baby: | `#fdcb6e` (gul) |
| `tjanstledig` | Tjänstledig | :clipboard: | `#74b9ff` (blå) |
| `utbildning` | Utbildning | :books: | `#a29bfe` (lila) |
| `ovrigt` | Övrigt | :pushpin: | `#636e72` (grå) |

### 4.7 Tabell: `kommentarer` (NY i v3.0)

```sql
CREATE TABLE kommentarer (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    personal_id   INTEGER NOT NULL,
    datum         TEXT NOT NULL,
    text          TEXT NOT NULL DEFAULT '',
    skapad        TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (personal_id) REFERENCES personal(id) ON DELETE CASCADE,
    UNIQUE(personal_id, datum)
);
```

| Kolumn | Typ | Constraint | Beskrivning |
|--------|-----|-----------|-------------|
| id | INTEGER | PK, AUTOINCREMENT | Unikt ID |
| personal_id | INTEGER | FK -> personal.id, CASCADE | Koppling till medarbetare |
| datum | TEXT | NOT NULL | ISO-datum |
| text | TEXT | NOT NULL, DEFAULT '' | Kommentartext (fritext) |
| skapad | TEXT | DEFAULT datetime('now') | Tidsstämpel för senaste ändring |
| | | UNIQUE(personal_id, datum) | Max en kommentar per person och dag |

**Upsert-logik:** `satt_kommentar()` använder `ON CONFLICT ... DO UPDATE SET text, skapad`. Tom text raderar posten.

---

## 5. Modul-för-modul-dokumentation

### 5.1 `database.py` - Databaslager (599 rader)

**Anslutningshantering:**
- `DB_PATH` beräknas som `os.path.join(os.path.dirname(os.path.abspath(__file__)), "teammanager.db")`
- `get_connection()` returnerar `sqlite3.Connection` med:
  - `PRAGMA foreign_keys = ON`
  - `conn.row_factory = sqlite3.Row` (resultat kan accessas som dict)
- Varje funktion öppnar och stänger sin egen connection (ej persistent/pooled)

#### Personal-funktioner

| Funktion | Signatur | Returnerar | Beskrivning |
|----------|----------|-----------|-------------|
| `init_db()` | `()` | `None` | Skapar alla 6 tabeller med `CREATE TABLE IF NOT EXISTS` |
| `hamta_all_personal()` | `(bara_aktiva=True)` | `list[dict]` | Alla medarbetare, sorterat på namn |
| `lagg_till_personal()` | `(namn, roll="", kapacitet_h=8.0)` | `int | None` | Nytt ID eller None vid duplikat |
| `uppdatera_personal()` | `(id, namn, roll, kapacitet_h, aktiv)` | `bool` | True vid OK, False vid duplikatnamn |
| `ta_bort_personal()` | `(person_id)` | `None` | Kaskaderar bort allokeringar, kompetenser, frånvaro, kommentarer |

#### Projekt-funktioner

| Funktion | Signatur | Returnerar | Beskrivning |
|----------|----------|-----------|-------------|
| `hamta_alla_projekt()` | `(bara_aktiva=True)` | `list[dict]` | Alla projekt, sorterat på namn |
| `lagg_till_projekt()` | `(namn, farg, startdatum, slutdatum)` | `int | None` | Nytt ID eller None vid duplikat |
| `uppdatera_projekt()` | `(id, namn, farg, startdatum, slutdatum, aktiv)` | `bool` | True/False |
| `ta_bort_projekt()` | `(projekt_id)` | `None` | Kaskaderar bort allokeringar |

#### Allokering-funktioner

| Funktion | Signatur | Returnerar | Beskrivning |
|----------|----------|-----------|-------------|
| `hamta_allokeringar()` | `(personal_id=None, projekt_id=None, fran_datum=None, till_datum=None)` | `list[dict]` | Joinad data med namn och färger (alla filter valfria) |
| `satt_allokering()` | `(personal_id, projekt_id, datum, timmar)` | `None` | Upsert; timmar<=0 raderar |
| `bulk_allokera()` | `(personal_id, projekt_id, datum_lista, timmar_per_dag)` | `None` | **NY v3.0** Allokera samma timmar för en lista datum |
| `kopiera_vecka()` | `(personal_id, fran_vecka_start, till_vecka_start)` | `int` | **NY v3.0** Kopierar mån-fre allokeringar, returnerar antal kopierade |
| `hamta_dagsbelastning()` | `(personal_id, datum)` | `float` | SUM(timmar) för en person på ett datum |

**`hamta_allokeringar()` returnerar dict med nycklarna:**
```python
{
    "id", "personal_id", "projekt_id", "datum", "timmar",
    "personal_namn", "projekt_namn", "projekt_farg", "kapacitet_h"
}
```

**`kopiera_vecka()` algoritm:**
```python
1. Hämta alla allokeringar för personen under fran_vecka_start till fran_vecka_start+4 (mån-fre)
2. Beräkna dag_diff = (till_vecka_start - fran_vecka_start).days
3. För varje allokering: nytt_datum = gammalt_datum + dag_diff
4. Upsert varje allokering till nytt datum
```

#### Kompetens-funktioner

| Funktion | Signatur | Returnerar | Beskrivning |
|----------|----------|-----------|-------------|
| `hamta_kompetenser()` | `(personal_id)` | `list[str]` | Alla taggar för en person |
| `hamta_alla_kompetenser()` | `()` | `list[str]` | Alla unika taggar i systemet |
| `satt_kompetenser()` | `(personal_id, taggar)` | `None` | Full replace av personens taggar |

#### Frånvaro-funktioner (ALLA NYA i v3.0)

| Funktion | Signatur | Returnerar | Beskrivning |
|----------|----------|-----------|-------------|
| `hamta_franvaro()` | `(personal_id=None, fran_datum=None, till_datum=None)` | `list[dict]` | Frånvaro med personal_namn, alla filter valfria |
| `satt_franvaro()` | `(personal_id, datum, typ, notering="")` | `None` | Upsert; tom typ raderar |
| `bulk_franvaro()` | `(personal_id, datum_lista, typ, notering="")` | `None` | Registrera frånvaro för flera datum |
| `ta_bort_franvaro()` | `(personal_id, fran_datum, till_datum)` | `None` | Radera all frånvaro för person i intervall |
| `ar_franvarande()` | `(personal_id, datum)` | `dict | None` | Returnerar `{"typ": "..."}` eller None |

**`hamta_franvaro()` returnerar dict med:**
```python
{"id", "personal_id", "datum", "typ", "notering", "personal_namn"}
```

#### Kommentar-funktioner (ALLA NYA i v3.0)

| Funktion | Signatur | Returnerar | Beskrivning |
|----------|----------|-----------|-------------|
| `hamta_kommentar()` | `(personal_id, datum)` | `str` | Kommentartext eller "" |
| `satt_kommentar()` | `(personal_id, datum, text)` | `None` | Upsert; tom text raderar |
| `hamta_kommentarer_period()` | `(personal_id, fran_datum, till_datum)` | `dict{datum_str: text}` | Alla kommentarer i period som dict |

#### Sammanställningsfunktioner (ALLA NYA i v3.0)

| Funktion | Signatur | Returnerar | Beskrivning |
|----------|----------|-----------|-------------|
| `hamta_overbelagda()` | `(fran_datum, till_datum)` | `list[dict]` | Alla person+datum med SUM(timmar) > kapacitet |
| `hamta_oallokerade()` | `(fran_datum, till_datum, arbetsdagar)` | `list[dict]` | Aktiva personer utan allokering (exkl. frånvarande) |
| `hamta_lediga_resurser()` | `(datum)` | `list[dict]` | Personer med ledig kapacitet, sorterat störst ledig tid först |
| `hamta_teamoversikt()` | `(fran_datum, till_datum, arbetsdagar)` | `dict` | Komplett teamöversikt med allokeringar+frånvaro per person per dag |

**`hamta_overbelagda()` returnerar:**
```python
{"personal_id", "personal_namn", "datum", "total_timmar", "kapacitet_h"}
```

**`hamta_oallokerade()` returnerar:**
```python
{"personal_id", "personal_namn", "datum", "roll"}
```
Logik: Hoppar över personer som har frånvaro registrerad det datumet.

**`hamta_lediga_resurser()` returnerar:**
```python
{"personal_id", "namn", "roll", "kapacitet_h", "allokerat", "ledigt"}
```
Sorterat med mest ledig tid först. Exkluderar frånvarande.

**`hamta_teamoversikt()` returnerar nested dict:**
```python
{
    personal_id: {
        "namn": str,
        "roll": str,
        "kapacitet_h": float,
        "dagar": {
            "2026-02-19": {
                "allokeringar": [{"projekt": str, "farg": str, "timmar": float}, ...],
                "franvaro": "semester" | None
            },
            ...
        }
    },
    ...
}
```

---

### 5.2 `calendar_utils.py` - Kalenderberäkningar (105 rader)

**Cachning:** `hamta_svenska_helgdagar()` är dekorerad med `@lru_cache(maxsize=10)`.

| Funktion | Signatur | Returnerar | Beskrivning |
|----------|----------|-----------|-------------|
| `hamta_svenska_helgdagar()` | `(ar_start, ar_slut)` | `dict{date: str}` | Alla röda dagar via `holidays.Sweden()`, cachad |
| `ar_arbetsdag()` | `(datum, helgdagar=None)` | `bool` | True om mån-fre och inte helgdag |
| `hamta_arbetsdagar()` | `(fran, till)` | `list[date]` | Alla arbetsdagar i intervallet |
| `antal_arbetsdagar_i_manad()` | `(ar, manad)` | `int` | Antal arbetsdagar i en specifik månad |
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
- `MANAD_NAMN = ["", "Januari", "Februari", ..., "December"]` (index 0 är tom sträng, index 1-12 = månader)

---

### 5.3 `charts.py` - Plotly-visualiseringar (262 rader)

**6 funktioner** som returnerar `go.Figure | None` (eller `pd.DataFrame` för varningar):

| Funktion | Signatur | Returnerar | Beskrivning |
|----------|----------|-----------|-------------|
| `skapa_belaggnings_heatmap()` | `(fran, till)` | `go.Figure | None` | Heatmap: personal x veckor, färg=beläggning% |
| `skapa_team_belaggning_stapel()` | `(fran, till)` | `go.Figure | None` | Stacked bar: vecka x timmar, per projekt |
| `skapa_person_belaggning_pie()` | `(personal_id, fran, till)` | `go.Figure | None` | Pie chart: tidsfördelning per projekt |
| `skapa_kapacitetsvarningar()` | `(fran, till)` | `pd.DataFrame` | Alla överbelagda person+datum |
| `skapa_gantt_oversikt()` | `(fran, till, arbetsdagar)` | `go.Figure | None` | **NY v3.0** Gantt-tidslinje per person |
| `skapa_franvaro_oversikt()` | `(fran, till)` | `go.Figure | None` | **NY v3.0** Stacked bar: frånvaro per typ och person |

**Heatmap-färgskala:**
```
0%   = #f0f0f0 (ljusgrå)      - Ingen beläggning
25%  = #a8d5e2 (ljusblå)      - Låg beläggning
50%  = #2ecc71 (grön)          - Normal beläggning
75%  = #f39c12 (orange)        - Hög beläggning
100% = #e74c3c (röd)           - Full beläggning
zmax = 120 (tillåter visning av 120% överbeläggning)
```

**Beläggningsformel (heatmap):**
```python
for varje person:
    for varje vecka i perioden:
        arbetsdagar_i_vecka = antal vardagar (mån-fre) som inte är helgdagar
        allokerade_timmar = SUM(allokering.timmar) för personens dagar i veckan
        max_timmar = arbetsdagar_i_vecka * person.kapacitet_h
        beläggning% = (allokerade_timmar / max_timmar) * 100 if max_timmar > 0 else 0
```

**Kapacitetsvarningar returnerar DataFrame med kolumner:**
```
personal_id, personal_namn, datum, kapacitet_h, total_timmar, overtid
```

**Gantt-översikt (NY v3.0):**
- Horisontella stapeldiagram med en rad per person
- Varje dag = ett segment, färgat efter projekt eller frånvarotyp
- Frånvarodagar visas med frånvarotypens färg
- Allokeringsdagar visas med projektfärg, bredd proportionell mot timmar/kapacitet
- Y-axel: personnamn, X-axel: datum (dag/månad-format)

**Frånvaroöversikt (NY v3.0):**
- Stacked bar chart: x=personal, y=antal dagar, uppdelat per frånvarotyp
- Använder FRANVARO_TYPER dict för färger, ikoner och namn

---

### 5.4 `export_utils.py` - Export (194 rader)

| Funktion | Signatur | Returnerar | Beskrivning |
|----------|----------|-----------|-------------|
| `exportera_allokeringar_csv()` | `(fran, till)` | `bytes` | CSV: Personal, Projekt, Datum, Timmar |
| `exportera_personal_csv()` | `()` | `bytes` | CSV: Namn, Roll, Kapacitet, Aktiv, Kompetenser, Skapad |
| `exportera_belaggningsrapport_csv()` | `(fran, till)` | `bytes` | CSV: Per person med beläggnings% |
| `generera_pdf_rapport()` | `(fran, till)` | `bytes` | PDF med tabell + sammanfattning |

**CSV-format:**
- Encoding: `utf-8-sig` (BOM för Excel-kompatibilitet med svenska tecken)
- Separator: `;` (semikolon, standard för svenska Excel-installationer)
- Alla funktioner returnerar `bytes` via `io.BytesIO`

**PDF-struktur (generera_pdf_rapport):**
1. Titel: "Teammanager - Belaggningsrapport" (Helvetica Bold 18pt)
2. Period och antal arbetsdagar (centrerat)
3. Tabell med blå header (#3498db): Personal | Roll | Tillg.(h) | Allok.(h) | Belaggn.%
4. Varannan rad ljusgrå bakgrund (#f5f5f5)
5. Överbelagda markeras med "(!)" suffix
6. Sammanfattning: antal resurser, total tid, snittbeläggning
7. Footer med genereringsdatum (italic)

**Känd PDF-begränsning:** fpdf2 med Helvetica-font stöder ej å/ä/ö. Lösning: Byt till Unicode-font (DejaVu).

---

### 5.5 `app.py` - Huvudapplikation (~860 rader)

**Övergripande struktur (uppifrån och ner):**

| Radintervall (ungefär) | Innehåll |
|------------------------|----------|
| 1-37 | Imports och konfiguration (`st.set_page_config`, `init_db()`) |
| 38-189 | CSS-styling (~150 rader modern 2026 design) |
| 190-228 | Sidebar: branding, navigation (9 sidor), stats |
| 225-228 | Hjälpfunktion `page_header(title, subtitle)` |
| 230-312 | **Sida: Hem** - KPI-kort, överbelagda, frånvarande, oallokerade, lediga |
| 314-369 | **Sida: Kalender** - CSS Grid-kalender, legender, röda dagar |
| 371-423 | **Sida: Resurser** - Personal CRUD med kompetenstaggar |
| 425-475 | **Sida: Projekt** - Projekt CRUD med färgval |
| 477-630 | **Sida: Allokering** - 4 tabs (snabb, dag-för-dag, kopiera, kommentarer) |
| 632-701 | **Sida: Frånvaro** - Registrera/ta bort, 30-dagarsvy, diagram |
| 703-771 | **Sida: Teamöversikt** - Gantt, detaljvy, lediga resurser |
| 773-830 | **Sida: Dashboard** - Plotly-diagram och kapacitetsvarningar |
| 832-861 | **Sida: Export** - CSV/PDF-nedladdningsknappar |

#### Sida: Hem (HELT NY i v3.0)

Smart startsida som visar vad som kräver uppmärksamhet:

1. **KPI-kort** (4 kolumner):
   - Överbelagda denna vecka (antal person+datum)
   - Utan allokering denna vecka
   - Frånvarande denna vecka
   - Överbelagda nästa vecka (varning framåt)

2. **Varningslistor:**
   - Överbelagda denna vecka (röda `alert-danger` boxar)
   - Överbelagda nästa vecka (gula `alert-warn` boxar)
   - Frånvarande denna vecka (blå `alert-info` boxar med ikon per typ)
   - Utan allokering (expanderbar tabell)

3. **Lediga resurser idag** (gröna `alert-success` boxar med namn, roll, lediga timmar, %)

4. **Allt-ser-bra-ut** meddelande om inga problem finns

**Datumberäkning:**
```python
idag = date.today()
vecka_slut = idag + timedelta(days=(4 - idag.weekday()))  # Fredag denna vecka
nasta_vecka_start = idag + timedelta(days=(7 - idag.weekday()))  # Måndag nästa vecka
nasta_vecka_slut = nasta_vecka_start + timedelta(days=4)  # Fredag nästa vecka
```

#### Sida: Allokering (UTÖKAD i v3.0)

**4 flikar (st.tabs):**

1. **Snabballokering** - Välj projekt, ange timmar/dag, allokera hela perioden med ett klick
   - Snabbknappar: 100% (8h), 75% (6h), 50% (4h), 25% (2h)
   - Visar antal arbetsdagar och totaltimmar

2. **Dag-för-dag** - number_input per projekt per dag (7 dagar per rad)
   - Visar frånvarodagar som info-boxar (ej redigerbara)
   - Visar överbelagda dagar som danger-boxar
   - Varje ändring sparas direkt via `satt_allokering()`

3. **Kopiera vecka** - Välj käll-måndag och mål-måndag, kopierar alla allokeringar
   - Använder `kopiera_vecka()` som kopierar mån-fre

4. **Kommentarer** - Fritextfält per dag (max 10 dagar visas)
   - Sparas direkt vid ändring via `satt_kommentar()`
   - Platshållartext: "Anteckning..."

**Sammanfattning** (under alla flikar):
- 3 metric-kort: Allokerat, Kapacitet, Beläggning%
- Lista per projekt med timmar

#### Sida: Frånvaro (HELT NY i v3.0)

1. **Registrera frånvaro** (expanderbar form):
   - Välj medarbetare, frånvarotyp (6 st med ikoner), datum från-till, notering
   - Använder `bulk_franvaro()` med `hamta_arbetsdagar()` (hoppar över helger/helgdagar)

2. **Ta bort frånvaro** (expanderbar form):
   - Välj medarbetare, datum från-till
   - Använder `ta_bort_franvaro()`

3. **Kommande frånvaro (30 dagar)** - Lista med info-boxar
4. **Frånvaroöversikt (3 månader)** - Plotly stacked bar chart

#### Sida: Teamöversikt (HELT NY i v3.0)

1. **Gantt-tidslinje** - Plotly horisontella staplat stapeldiagram
2. **Detaljerad översikt** - Expander per person med DataFrame-tabell:
   - Kolumner: Datum, Veckodag, Status (projekt+timmar eller frånvarotyp), Timmar
3. **Lediga resurser per dag** - Välj datum, se vem som har ledig kapacitet

---

## 6. UI/CSS-design (v2.0+, ~230 rader CSS)

### 6.1 Designsystem

| Element | Teknik |
|---------|--------|
| Font | Inter (Google Fonts), vikter 300-800 |
| Accentfärg 1 | `#6C5CE7` (lila) |
| Accentfärg 2 | `#00B894` (grön) |
| Huvudgradient | `135deg: #6C5CE7 -> #a29bfe -> #00B894` |
| Kort | Glassmorphism: `backdrop-filter: blur(12px)`, `rgba(255,255,255,0.65)` |
| Border-radius | 16px (kort), 10px (knappar), 20px (taggar), 4px (legend-dots) |
| Skuggor | `0 8px 32px rgba(0,0,0,0.08)` (standard), starkare vid hover |
| Hover | `transform: translateY(-2px)` med 0.2s ease transition |

### 6.2 CSS-variabler (definierade i `:root`)

```css
--accent: #6C5CE7;
--accent2: #00B894;
--bg-card: rgba(255,255,255,0.65);
--shadow: 0 8px 32px rgba(0,0,0,0.08);
--radius: 16px;
--radius-sm: 10px;
--gradient-main: linear-gradient(135deg, #6C5CE7 0%, #a29bfe 50%, #00B894 100%);
```

### 6.3 Sidebar

- Bakgrund: Mörk gradient (`#1e1e2e -> #2d2b55`)
- Textfärg: `#cdd6f4` (mjuk ljusgrå)
- Branding: `.sidebar-brand` med gradient-text "Teammanager" + "RESOURCE PLANNING"
- Stats: `.sidebar-stat` med gradient-siffror (antal resurser + projekt)
- Versionsetikett: `v3.0 · 2026`

### 6.4 Kalender (CSS Grid)

| CSS-klass | Bakgrund | Används för |
|-----------|----------|-------------|
| `.cal-grid` | - | 7-kolumns grid med 6px gap |
| `.cal-header` | - | Veckodagsrubriker (Mån-Sön) |
| `.cal-work` | `linear-gradient(135deg, #dfe6e9, #f0f3f5)` | Arbetsdagar |
| `.cal-weekend` | `linear-gradient(135deg, #ffeaa7, #fdcb6e)` | Helger (lör-sön) |
| `.cal-holiday` | `linear-gradient(135deg, #fd79a8, #e84393)` | Röda dagar, vit text |
| `.cal-today` | - | Lila box-shadow ring (`0 0 0 3px var(--accent)`) |
| `.cal-empty` | - | Tomma celler (opacity: 0) |
| `.cal-holiday-name` | - | Helgdagsnamn (8px, max-width, ellipsis) |

### 6.5 Metric-kort

- `[data-testid="stMetric"]` selektorn (Streamlit internals)
- Glassmorphism-bakgrund med blur
- Label: uppercase, 13px, font-weight 600, opacity 0.65
- Värde: 32px, font-weight 800, gradient-text (clip)
- Hover: lift 2px + starkare skugga

### 6.6 Alert-boxar

| CSS-klass | Vänsterkant | Bakgrund | Användning |
|-----------|-------------|----------|-----------|
| `.alert-success` | `#00b894` (grön) | Grön gradient | Allt OK, lediga resurser |
| `.alert-warn` | `#fdcb6e` (gul) | Gul gradient | Informationsvarningar |
| `.alert-danger` | `#e84393` (rosa) | Rosa gradient | Överbeläggning |
| `.alert-info` | `#74b9ff` (blå) | Blå gradient | Frånvaroinformation |

### 6.7 Övriga CSS-klasser

| Klass | Beskrivning |
|-------|-------------|
| `.page-header` | Sidtitel med gradient-text (36px, 800 weight) + undertitel |
| `.glass-card` | Glassmorphism-kort med blur, border, padding 24px |
| `.skill-tag` | Pill-formade kompetenstaggar med hover-lift |
| `.legend` | Flexbox-rad med `.legend-item` och `.legend-dot` |
| `.holiday-row` | Rad i helgdagslistan med hover-highlight |
| `.proj-dot` | 12px cirkel med box-shadow för projektfärg |
| `.action-card` | Kort med gradient-nummer (används på Hem-sidan) |

---

## 7. Algoritmer & Affärslogik

### 7.1 Arbetsdag-definition

```python
def ar_arbetsdag(datum):
    if datum.weekday() >= 5:         # Lördag (5) eller Söndag (6)
        return False
    if datum in svenska_helgdagar:    # holidays.Sweden() med @lru_cache
        return False
    return True
```

### 7.2 Allokering upsert-mönster

Används av `satt_allokering()`, `bulk_allokera()`, `kopiera_vecka()`:

```python
if timmar <= 0:
    DELETE FROM allokering WHERE personal_id AND projekt_id AND datum
else:
    INSERT INTO allokering (personal_id, projekt_id, datum, timmar)
    VALUES (?, ?, ?, ?)
    ON CONFLICT(personal_id, projekt_id, datum)
    DO UPDATE SET timmar = excluded.timmar
```

### 7.3 Frånvaro upsert-mönster

Samma princip: `UNIQUE(personal_id, datum)` med `ON CONFLICT ... DO UPDATE`.
En person kan bara ha EN typ av frånvaro per dag. Ny registrering ersätter gammal.

### 7.4 Kommentar upsert-mönster

```python
if text.strip() == "":
    DELETE FROM kommentarer WHERE personal_id AND datum
else:
    INSERT ... ON CONFLICT(personal_id, datum)
    DO UPDATE SET text = excluded.text, skapad = datetime('now')
```

### 7.5 Beläggningsberäkning (heatmap)

```python
for varje person:
    for varje vecka i perioden:
        arbetsdagar = [dag for dag in veckan if ar_arbetsdag(dag)]
        max_h = len(arbetsdagar) * person.kapacitet_h
        allokerat_h = SUM(alla allokeringar för personen under dessa dagar)
        belaggning_pct = (allokerat_h / max_h) * 100 if max_h > 0 else 0
```

### 7.6 Överbelagd-detektion

```sql
SELECT personal_id, datum, SUM(timmar) as total
FROM allokering
GROUP BY personal_id, datum
HAVING total > personal.kapacitet_h
```

### 7.7 Oallokerad-detektion

```python
for varje arbetsdag:
    for varje aktiv person:
        if personen har frånvaro denna dag:
            hoppa över (frånvaro är inte samma som "oallokerad")
        if SUM(allokeringar) == 0:
            markera som oallokerad
```

### 7.8 Lediga resurser

```python
for varje aktiv person:
    if personen har frånvaro detta datum:
        hoppa över
    allokerat = SUM(allokeringar för personen detta datum)
    ledigt = kapacitet_h - allokerat
    if ledigt > 0:
        lägg till i listan
sortera med mest ledig tid först
```

### 7.9 Kopiera vecka

```python
def kopiera_vecka(personal_id, fran_mandag, till_mandag):
    # Hämta mån-fre (5 dagar) från källveckan
    fran_slut = fran_mandag + 4 dagar
    allokeringar = SELECT * WHERE personal_id AND datum BETWEEN fran_mandag AND fran_slut

    # Beräkna offset
    dag_diff = (till_mandag - fran_mandag).days  # Alltid multipel av 7

    # Upsert varje allokering med nytt datum
    for allok in allokeringar:
        nytt_datum = gammalt_datum + dag_diff
        UPSERT allokering(personal_id, projekt_id, nytt_datum, timmar)
```

---

## 8. Tekniska beroenden

### 8.1 Python-paket (requirements.txt)

| Paket | Version | Syfte | Importeras i |
|-------|---------|-------|-------------|
| streamlit | >=1.28.0 | Web UI-ramverk, widgets, session state | app.py |
| pandas | >=2.0.0 | DataFrames, gruppering, export | charts.py, export_utils.py, app.py |
| plotly | >=5.15.0 | Interaktiva diagram (heatmap, bar, pie, gantt) | charts.py |
| holidays | >=0.34 | Svenska helgdagar (röda dagar) | calendar_utils.py |
| fpdf2 | >=2.7.0 | PDF-generering | export_utils.py |

### 8.2 Python standardbibliotek

| Paket | Används i | Syfte |
|-------|-----------|-------|
| sqlite3 | database.py | Databasanslutning |
| os | database.py | Filsökvägar (DB_PATH) |
| datetime | alla filer | date, timedelta, datetime |
| functools | calendar_utils.py | lru_cache (helgdagscachning) |
| io | export_utils.py | BytesIO (export-buffertar) |

---

## 9. Deploy & Drift

### 9.1 Streamlit Community Cloud

- **Live URL:** `teammanager-stfn9tuicvkch4mulxcdpa.streamlit.app`
- **Repo:** `Gunnarsson-cloud/Teammanager`
- **Branch:** `master`
- **Main file:** `app.py` (VIKTIGT: inte streamlit_app.py som är default)
- **Auto-deploy:** Ja, vid push till master
- **Python-version:** Väljs automatiskt av Streamlit Cloud

### 9.2 Köra lokalt

```bash
cd Teammanager
pip install -r requirements.txt
streamlit run app.py
# Öppna http://localhost:8501
```

### 9.3 Git-konfiguration

```bash
# Repo
git remote -v
# origin  https://github.com/Gunnarsson-cloud/Teammanager.git

# Branch
git branch
# * master

# Användare
git config user.name   # Andreas Gunnarsson
git config user.email  # a.e.gunnarsson@gmail.com
```

### 9.4 Viktigt att veta

| Punkt | Detalj |
|-------|--------|
| DB auto-skapas | `init_db()` körs vid varje appstart, skapar tabeller om de inte finns |
| Ephemeral disk | Streamlit Cloud raderar `teammanager.db` vid omstart/redeploy |
| .gitignore | `.db`-filer, `__pycache__/`, `.env`, `venv/` exkluderas |
| git add | Använd ALDRIG `git add -A` på Windows (fångar `nul` device-fil). Använd `git add filnamn1 filnamn2` |
| Python ej installerat lokalt | Maskinen har ej Python. Appen körs enbart på Streamlit Cloud |
| Plotly transparent | Alla diagram: `paper_bgcolor='rgba(0,0,0,0)'`, `plot_bgcolor='rgba(0,0,0,0)'` |

---

## 10. Fullständig import-karta

### app.py importerar:

```python
# Från database.py:
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

# Från calendar_utils.py:
skapa_manadskalender, ar_arbetsdag, hamta_arbetsdagar,
hamta_svenska_helgdagar, antal_arbetsdagar_i_manad,
VECKODAG_NAMN, MANAD_NAMN

# Från charts.py:
skapa_belaggnings_heatmap, skapa_team_belaggning_stapel,
skapa_person_belaggning_pie, skapa_kapacitetsvarningar,
skapa_gantt_oversikt, skapa_franvaro_oversikt

# Från export_utils.py:
exportera_allokeringar_csv, exportera_personal_csv,
exportera_belaggningsrapport_csv, generera_pdf_rapport
```

### charts.py importerar:

```python
from calendar_utils import hamta_arbetsdagar, hamta_svenska_helgdagar, MANAD_NAMN
from database import (
    hamta_allokeringar, hamta_all_personal, hamta_franvaro,
    hamta_teamoversikt, FRANVARO_TYPER
)
```

### export_utils.py importerar:

```python
from database import hamta_allokeringar, hamta_all_personal, hamta_alla_projekt, hamta_kompetenser
from calendar_utils import hamta_arbetsdagar
```

---

## 11. Ändringslogg

### v1.0 (2026-02-19) - Initial release
- [x] Svensk kalender med holidays-biblioteket (5 år framåt)
- [x] CRUD för personal (namn, roll, kapacitet, aktiv-flagga)
- [x] CRUD för projekt (namn, färg, start/slutdatum)
- [x] Kompetenstaggar per medarbetare
- [x] Allokering: timmar per person/projekt/dag med upsert-logik
- [x] Dashboard: Plotly heatmap, stacked bar, pie chart
- [x] Kapacitetsvarningar (>kapacitet per dag)
- [x] Export: 3 CSV-typer + PDF-rapport
- [x] Publicerad till GitHub och Streamlit Cloud

### v2.0 (2026-02-19) - Modern UI redesign
- [x] Komplett CSS-redesign: glassmorphism, gradient-accenter
- [x] Mörk sidebar med gradient-branding (#1e1e2e -> #2d2b55)
- [x] CSS Grid-kalender (ersätter st.columns) med hover-animationer
- [x] Idag-indikator (lila ring) i kalendern
- [x] Inter-font från Google Fonts (vikter 300-800)
- [x] Gradient page headers (36px, 800 weight)
- [x] Glassmorphism metric-kort med gradient-text
- [x] Pill-formade kompetenstaggar med hover
- [x] 4 alert-box-typer (success/warn/danger/info)
- [x] Transparenta Plotly-diagram
- [x] Hover lift-effekt på knappar och kort

### v3.0 (2026-02-19) - Komplett funktionalitet
- [x] **Ny sida: Hem** - Smart startsida med KPI-kort, varningar, lediga resurser
- [x] **Ny sida: Frånvaro** - 6 frånvarotyper (semester, sjuk, VAB, tjänstledig, utbildning, övrigt)
- [x] **Ny sida: Teamöversikt** - Gantt-tidslinje + detaljvy per person + lediga resurser
- [x] **Ny DB-tabell: franvaro** - UNIQUE(personal_id, datum), 6 typer med ikoner/färger
- [x] **Ny DB-tabell: kommentarer** - UNIQUE(personal_id, datum), fritext med tidsstämpel
- [x] **Bulk-allokering** - Allokera hela perioder med ett klick + snabbknappar (100/75/50/25%)
- [x] **Kopiera vecka** - Duplicera allokeringar mån-fre mellan veckor
- [x] **Dag-för-dag med frånvarovisning** - Frånvarodagar visas som info-boxar, ej redigerbara
- [x] **Kommentarer per dag** - Anteckningar som "Jobbar hemifrån" eller "Väntar på beslut"
- [x] **Överbelagda-detektion** - SQL-baserad GROUP BY + HAVING, visas på Hem-sidan
- [x] **Oallokerade-detektion** - Hittar personer utan allokeringar, exkluderar frånvarande
- [x] **Lediga resurser** - Per dag, sorterat på mest ledig tid, exkluderar frånvarande
- [x] **Gantt-diagram** - Plotly horisontella staplat stapeldiagram per person
- [x] **Frånvarodiagram** - Plotly stacked bar per typ och person

---

## 12. Kända begränsningar

| # | Begränsning | Orsak | Föreslagen lösning |
|---|------------|-------|-------------------|
| 1 | Data försvinner vid redeploy | Streamlit Cloud ephemeral disk | Migrera till PostgreSQL/Supabase |
| 2 | Ingen autentisering | Ej implementerat | Lägg till `streamlit-authenticator` |
| 3 | Långsam heatmap vid stor data | O(n*m) Python-loop per person per vecka per dag | Precompute med SQL-aggregering |
| 4 | PDF utan å/ä/ö | fpdf2 Helvetica har ej stöd | Byt till Unicode-font (DejaVu) |
| 5 | Single-user | SQLite + Streamlit session | Multi-user kräver databas + auth |
| 6 | Dag-för-dag UI långsam vid många dagar | Varje cell gör separat DB-anrop | Batch-hämta alla allokeringar |
| 7 | Ingen drag-and-drop | Streamlit har ej stöd | Överväg custom component |
| 8 | `git add -A` kraschar på Windows | `nul` device-fil | Använd alltid specifika filnamn |
| 9 | Frånvaro ingår ej i PDF-rapport | export_utils.py ej uppdaterad i v3.0 | Lägg till frånvarodata i rapport |
| 10 | Kommentarer ej exporterbara | Ej implementerat | Lägg till i CSV-export |

---

## 13. Naturliga nästa steg (ej implementerat)

- [ ] Persistent databas (PostgreSQL/Supabase) för Streamlit Cloud
- [ ] Användarautentisering (multi-user, lösenord)
- [ ] Drag-and-drop allokering i kalendervy
- [ ] API-integration mot projektverktyg (Jira, Azure DevOps)
- [ ] Notifikationer vid överbeläggning (e-post/Teams)
- [ ] Budgetuppföljning per projekt (timmar vs. plan)
- [ ] Import från Excel för initial datamigration
- [ ] Dark mode toggle
- [ ] Frånvaro i PDF-rapport
- [ ] Kommentarer i CSV-export
- [ ] Unicode-font i PDF (DejaVu för å/ä/ö-stöd)
- [ ] Precomputed heatmap med SQL-aggregering för prestanda

---

*Dokumentet uppdaterat: 2026-02-19 | Version: 3.0*
*Total kodbas: ~2020 rader Python + ~230 rader CSS*
*Antal databastabeller: 6 | Antal sidor: 9 | Antal Plotly-diagram: 6*
