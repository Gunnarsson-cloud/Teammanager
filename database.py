"""
database.py - Databashantering för Teammanager v3.1
Hanterar all CRUD-logik mot databasen.
Stödjer både SQLite (lokal utveckling) och PostgreSQL/Supabase (produktion).
Inkluderar: personal, projekt, allokering, kompetenser, frånvaro, kommentarer.
"""

import sqlite3
import os
from datetime import datetime, date, timedelta

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "teammanager.db")

# ============================================================
# DUAL-MODE: PostgreSQL (Supabase) eller SQLite (lokal fallback)
# ============================================================

_USE_POSTGRES = False
_SUPABASE_DB_URL = ""

try:
    import streamlit as st
    _SUPABASE_DB_URL = st.secrets.get("database", {}).get("SUPABASE_DB_URL", "")
except Exception:
    _SUPABASE_DB_URL = os.environ.get("SUPABASE_DB_URL", "")

if _SUPABASE_DB_URL:
    try:
        import psycopg2
        import psycopg2.extras
        _USE_POSTGRES = True
    except ImportError:
        _USE_POSTGRES = False

# Databasspecifika inställningar
if _USE_POSTGRES:
    _IntegrityError = psycopg2.IntegrityError
    _NOW_FUNC = "CURRENT_TIMESTAMP"
else:
    _IntegrityError = sqlite3.IntegrityError
    _NOW_FUNC = "datetime('now')"


def _q(query):
    """Konvertera SQLite ?-placeholders till PostgreSQL %s om det behövs."""
    if _USE_POSTGRES:
        return query.replace("?", "%s")
    return query


# ============================================================
# CONNECTION WRAPPER FÖR POSTGRESQL
# ============================================================

class _PgConnectionWrapper:
    """Wrappar psycopg2-connection att bete sig som sqlite3.Connection.
    Alla execute()-anrop använder DictCursor automatiskt så att
    row["kolumn"] och dict(row) fungerar likadant som sqlite3.Row.
    """

    def __init__(self, conn):
        self._conn = conn

    def execute(self, query, params=None):
        cursor = self._conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cursor.execute(query, params or ())
        return cursor

    def executescript(self, script):
        """Ej tillgänglig för PostgreSQL — använd execute() per statement."""
        raise NotImplementedError("Använd execute() per statement för PostgreSQL")

    def commit(self):
        self._conn.commit()

    def rollback(self):
        self._conn.rollback()

    def close(self):
        self._conn.close()

    def cursor(self):
        return self._conn.cursor(cursor_factory=psycopg2.extras.DictCursor)


# ============================================================
# ANSLUTNING
# ============================================================

def get_connection():
    """Skapa och returnera en databasanslutning.
    PostgreSQL om SUPABASE_DB_URL finns, annars SQLite.
    """
    if _USE_POSTGRES:
        raw = psycopg2.connect(_SUPABASE_DB_URL)
        raw.autocommit = False
        return _PgConnectionWrapper(raw)
    else:
        conn = sqlite3.connect(DB_PATH)
        conn.execute("PRAGMA foreign_keys = ON")
        conn.row_factory = sqlite3.Row
        return conn


# ============================================================
# TABELLINITIERING
# ============================================================

_CREATE_TABLES_PG = [
    """CREATE TABLE IF NOT EXISTS personal (
        id SERIAL PRIMARY KEY,
        namn TEXT NOT NULL UNIQUE,
        roll TEXT DEFAULT '',
        kapacitet_h REAL DEFAULT 8.0,
        aktiv INTEGER DEFAULT 1,
        skapad_datum TEXT DEFAULT CURRENT_DATE
    )""",
    """CREATE TABLE IF NOT EXISTS projekt (
        id SERIAL PRIMARY KEY,
        namn TEXT NOT NULL UNIQUE,
        farg TEXT DEFAULT '#3498db',
        startdatum TEXT,
        slutdatum TEXT,
        aktiv INTEGER DEFAULT 1
    )""",
    """CREATE TABLE IF NOT EXISTS allokering (
        id SERIAL PRIMARY KEY,
        personal_id INTEGER NOT NULL,
        projekt_id INTEGER NOT NULL,
        datum TEXT NOT NULL,
        timmar REAL NOT NULL DEFAULT 0,
        FOREIGN KEY (personal_id) REFERENCES personal(id) ON DELETE CASCADE,
        FOREIGN KEY (projekt_id) REFERENCES projekt(id) ON DELETE CASCADE,
        UNIQUE(personal_id, projekt_id, datum)
    )""",
    """CREATE TABLE IF NOT EXISTS kompetenser (
        id SERIAL PRIMARY KEY,
        personal_id INTEGER NOT NULL,
        tagg TEXT NOT NULL,
        FOREIGN KEY (personal_id) REFERENCES personal(id) ON DELETE CASCADE,
        UNIQUE(personal_id, tagg)
    )""",
    """CREATE TABLE IF NOT EXISTS franvaro (
        id SERIAL PRIMARY KEY,
        personal_id INTEGER NOT NULL,
        datum TEXT NOT NULL,
        typ TEXT NOT NULL DEFAULT 'semester',
        notering TEXT DEFAULT '',
        FOREIGN KEY (personal_id) REFERENCES personal(id) ON DELETE CASCADE,
        UNIQUE(personal_id, datum)
    )""",
    """CREATE TABLE IF NOT EXISTS kommentarer (
        id SERIAL PRIMARY KEY,
        personal_id INTEGER NOT NULL,
        datum TEXT NOT NULL,
        text TEXT NOT NULL DEFAULT '',
        skapad TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (personal_id) REFERENCES personal(id) ON DELETE CASCADE,
        UNIQUE(personal_id, datum)
    )""",
]

_CREATE_TABLES_SQLITE = """
    CREATE TABLE IF NOT EXISTS personal (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        namn TEXT NOT NULL UNIQUE,
        roll TEXT DEFAULT '',
        kapacitet_h REAL DEFAULT 8.0,
        aktiv INTEGER DEFAULT 1,
        skapad_datum TEXT DEFAULT (date('now'))
    );

    CREATE TABLE IF NOT EXISTS projekt (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        namn TEXT NOT NULL UNIQUE,
        farg TEXT DEFAULT '#3498db',
        startdatum TEXT,
        slutdatum TEXT,
        aktiv INTEGER DEFAULT 1
    );

    CREATE TABLE IF NOT EXISTS allokering (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        personal_id INTEGER NOT NULL,
        projekt_id INTEGER NOT NULL,
        datum TEXT NOT NULL,
        timmar REAL NOT NULL DEFAULT 0,
        FOREIGN KEY (personal_id) REFERENCES personal(id) ON DELETE CASCADE,
        FOREIGN KEY (projekt_id) REFERENCES projekt(id) ON DELETE CASCADE,
        UNIQUE(personal_id, projekt_id, datum)
    );

    CREATE TABLE IF NOT EXISTS kompetenser (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        personal_id INTEGER NOT NULL,
        tagg TEXT NOT NULL,
        FOREIGN KEY (personal_id) REFERENCES personal(id) ON DELETE CASCADE,
        UNIQUE(personal_id, tagg)
    );

    CREATE TABLE IF NOT EXISTS franvaro (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        personal_id INTEGER NOT NULL,
        datum TEXT NOT NULL,
        typ TEXT NOT NULL DEFAULT 'semester',
        notering TEXT DEFAULT '',
        FOREIGN KEY (personal_id) REFERENCES personal(id) ON DELETE CASCADE,
        UNIQUE(personal_id, datum)
    );

    CREATE TABLE IF NOT EXISTS kommentarer (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        personal_id INTEGER NOT NULL,
        datum TEXT NOT NULL,
        text TEXT NOT NULL DEFAULT '',
        skapad TEXT DEFAULT (datetime('now')),
        FOREIGN KEY (personal_id) REFERENCES personal(id) ON DELETE CASCADE,
        UNIQUE(personal_id, datum)
    );
"""


def init_db():
    """Skapa alla tabeller om de inte redan finns."""
    conn = get_connection()
    if _USE_POSTGRES:
        cursor = conn.cursor()
        for stmt in _CREATE_TABLES_PG:
            cursor.execute(stmt)
        conn.commit()
        cursor.close()
    else:
        cursor = conn.cursor()
        cursor.executescript(_CREATE_TABLES_SQLITE)
        conn.commit()
    conn.close()


# ============================================================
# PERSONAL - CRUD
# ============================================================

def hamta_all_personal(bara_aktiva=True):
    conn = get_connection()
    if bara_aktiva:
        rows = conn.execute("SELECT * FROM personal WHERE aktiv = 1 ORDER BY namn").fetchall()
    else:
        rows = conn.execute("SELECT * FROM personal ORDER BY namn").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def lagg_till_personal(namn, roll="", kapacitet_h=8.0):
    conn = get_connection()
    try:
        if _USE_POSTGRES:
            cursor = conn.execute(
                _q("INSERT INTO personal (namn, roll, kapacitet_h) VALUES (?, ?, ?) RETURNING id"),
                (namn.strip(), roll.strip(), kapacitet_h)
            )
            conn.commit()
            return cursor.fetchone()["id"]
        else:
            cursor = conn.execute(
                "INSERT INTO personal (namn, roll, kapacitet_h) VALUES (?, ?, ?)",
                (namn.strip(), roll.strip(), kapacitet_h)
            )
            conn.commit()
            return cursor.lastrowid
    except _IntegrityError:
        if _USE_POSTGRES:
            conn.rollback()
        return None
    finally:
        conn.close()


def uppdatera_personal(person_id, namn, roll, kapacitet_h, aktiv):
    conn = get_connection()
    try:
        conn.execute(
            _q("UPDATE personal SET namn=?, roll=?, kapacitet_h=?, aktiv=? WHERE id=?"),
            (namn.strip(), roll.strip(), kapacitet_h, aktiv, person_id)
        )
        conn.commit()
        return True
    except _IntegrityError:
        if _USE_POSTGRES:
            conn.rollback()
        return False
    finally:
        conn.close()


def ta_bort_personal(person_id):
    conn = get_connection()
    conn.execute(_q("DELETE FROM personal WHERE id=?"), (person_id,))
    conn.commit()
    conn.close()


# ============================================================
# PROJEKT - CRUD
# ============================================================

def hamta_alla_projekt(bara_aktiva=True):
    conn = get_connection()
    if bara_aktiva:
        rows = conn.execute("SELECT * FROM projekt WHERE aktiv = 1 ORDER BY namn").fetchall()
    else:
        rows = conn.execute("SELECT * FROM projekt ORDER BY namn").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def lagg_till_projekt(namn, farg="#3498db", startdatum=None, slutdatum=None):
    conn = get_connection()
    try:
        if _USE_POSTGRES:
            cursor = conn.execute(
                _q("INSERT INTO projekt (namn, farg, startdatum, slutdatum) VALUES (?, ?, ?, ?) RETURNING id"),
                (namn.strip(), farg, startdatum, slutdatum)
            )
            conn.commit()
            return cursor.fetchone()["id"]
        else:
            cursor = conn.execute(
                "INSERT INTO projekt (namn, farg, startdatum, slutdatum) VALUES (?, ?, ?, ?)",
                (namn.strip(), farg, startdatum, slutdatum)
            )
            conn.commit()
            return cursor.lastrowid
    except _IntegrityError:
        if _USE_POSTGRES:
            conn.rollback()
        return None
    finally:
        conn.close()


def uppdatera_projekt(projekt_id, namn, farg, startdatum, slutdatum, aktiv):
    conn = get_connection()
    try:
        conn.execute(
            _q("UPDATE projekt SET namn=?, farg=?, startdatum=?, slutdatum=?, aktiv=? WHERE id=?"),
            (namn.strip(), farg, startdatum, slutdatum, aktiv, projekt_id)
        )
        conn.commit()
        return True
    except _IntegrityError:
        if _USE_POSTGRES:
            conn.rollback()
        return False
    finally:
        conn.close()


def ta_bort_projekt(projekt_id):
    conn = get_connection()
    conn.execute(_q("DELETE FROM projekt WHERE id=?"), (projekt_id,))
    conn.commit()
    conn.close()


# ============================================================
# ALLOKERING - CRUD
# ============================================================

def hamta_allokeringar(personal_id=None, projekt_id=None, fran_datum=None, till_datum=None):
    conn = get_connection()
    query = """
        SELECT a.id, a.personal_id, a.projekt_id, a.datum, a.timmar,
               p.namn as personal_namn, pr.namn as projekt_namn, pr.farg as projekt_farg,
               p.kapacitet_h
        FROM allokering a
        JOIN personal p ON a.personal_id = p.id
        JOIN projekt pr ON a.projekt_id = pr.id
        WHERE 1=1
    """
    params = []
    if personal_id:
        query += " AND a.personal_id = ?"
        params.append(personal_id)
    if projekt_id:
        query += " AND a.projekt_id = ?"
        params.append(projekt_id)
    if fran_datum:
        query += " AND a.datum >= ?"
        params.append(str(fran_datum))
    if till_datum:
        query += " AND a.datum <= ?"
        params.append(str(till_datum))
    query += " ORDER BY a.datum, p.namn"
    rows = conn.execute(_q(query), params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def satt_allokering(personal_id, projekt_id, datum, timmar):
    """Upsert allokering. Om timmar <= 0 raderas posten."""
    conn = get_connection()
    datum_str = str(datum)
    if timmar <= 0:
        conn.execute(
            _q("DELETE FROM allokering WHERE personal_id=? AND projekt_id=? AND datum=?"),
            (personal_id, projekt_id, datum_str)
        )
    else:
        conn.execute(_q("""
            INSERT INTO allokering (personal_id, projekt_id, datum, timmar)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(personal_id, projekt_id, datum)
            DO UPDATE SET timmar = excluded.timmar
        """), (personal_id, projekt_id, datum_str, timmar))
    conn.commit()
    conn.close()


def bulk_allokera(personal_id, projekt_id, datum_lista, timmar_per_dag):
    """Allokera en person till ett projekt för en lista av datum."""
    conn = get_connection()
    for d in datum_lista:
        datum_str = str(d)
        if timmar_per_dag <= 0:
            conn.execute(
                _q("DELETE FROM allokering WHERE personal_id=? AND projekt_id=? AND datum=?"),
                (personal_id, projekt_id, datum_str)
            )
        else:
            conn.execute(_q("""
                INSERT INTO allokering (personal_id, projekt_id, datum, timmar)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(personal_id, projekt_id, datum)
                DO UPDATE SET timmar = excluded.timmar
            """), (personal_id, projekt_id, datum_str, timmar_per_dag))
    conn.commit()
    conn.close()


def kopiera_vecka(personal_id, fran_vecka_start, till_vecka_start):
    """Kopiera alla allokeringar från en vecka till en annan för en person."""
    conn = get_connection()
    fran_slut = fran_vecka_start + timedelta(days=4)  # Mån-Fre
    rows = conn.execute(_q("""
        SELECT projekt_id, datum, timmar FROM allokering
        WHERE personal_id=? AND datum >= ? AND datum <= ?
    """), (personal_id, str(fran_vecka_start), str(fran_slut))).fetchall()

    dag_diff = (till_vecka_start - fran_vecka_start).days
    for row in rows:
        gammalt_datum = datetime.strptime(row["datum"], "%Y-%m-%d").date()
        nytt_datum = gammalt_datum + timedelta(days=dag_diff)
        conn.execute(_q("""
            INSERT INTO allokering (personal_id, projekt_id, datum, timmar)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(personal_id, projekt_id, datum)
            DO UPDATE SET timmar = excluded.timmar
        """), (personal_id, row["projekt_id"], str(nytt_datum), row["timmar"]))

    conn.commit()
    conn.close()
    return len(rows)


def hamta_dagsbelastning(personal_id, datum):
    conn = get_connection()
    row = conn.execute(
        _q("SELECT COALESCE(SUM(timmar), 0) as total FROM allokering WHERE personal_id=? AND datum=?"),
        (personal_id, str(datum))
    ).fetchone()
    conn.close()
    return row["total"] if row else 0


# ============================================================
# KOMPETENSER
# ============================================================

def hamta_kompetenser(personal_id):
    conn = get_connection()
    rows = conn.execute(
        _q("SELECT tagg FROM kompetenser WHERE personal_id=? ORDER BY tagg"),
        (personal_id,)
    ).fetchall()
    conn.close()
    return [r["tagg"] for r in rows]


def hamta_alla_kompetenser():
    conn = get_connection()
    rows = conn.execute("SELECT DISTINCT tagg FROM kompetenser ORDER BY tagg").fetchall()
    conn.close()
    return [r["tagg"] for r in rows]


def satt_kompetenser(personal_id, taggar):
    conn = get_connection()
    conn.execute(_q("DELETE FROM kompetenser WHERE personal_id=?"), (personal_id,))
    for tagg in taggar:
        tagg = tagg.strip()
        if tagg:
            try:
                conn.execute(
                    _q("INSERT INTO kompetenser (personal_id, tagg) VALUES (?, ?)"),
                    (personal_id, tagg)
                )
            except _IntegrityError:
                if _USE_POSTGRES:
                    conn.rollback()
    conn.commit()
    conn.close()


# ============================================================
# FRÅNVARO (semester, sjuk, VAB, tjänstledigt, övrigt)
# ============================================================

FRANVARO_TYPER = {
    "semester": {"namn": "Semester", "ikon": "🌴", "farg": "#00b894"},
    "sjuk": {"namn": "Sjuk", "ikon": "🤒", "farg": "#e17055"},
    "vab": {"namn": "VAB", "ikon": "👶", "farg": "#fdcb6e"},
    "tjanstledig": {"namn": "Tjänstledig", "ikon": "📋", "farg": "#74b9ff"},
    "utbildning": {"namn": "Utbildning", "ikon": "📚", "farg": "#a29bfe"},
    "ovrigt": {"namn": "Övrigt", "ikon": "📌", "farg": "#636e72"},
}


def hamta_franvaro(personal_id=None, fran_datum=None, till_datum=None):
    """Hämta frånvaro med valfria filter."""
    conn = get_connection()
    query = """
        SELECT f.id, f.personal_id, f.datum, f.typ, f.notering,
               p.namn as personal_namn
        FROM franvaro f
        JOIN personal p ON f.personal_id = p.id
        WHERE 1=1
    """
    params = []
    if personal_id:
        query += " AND f.personal_id = ?"
        params.append(personal_id)
    if fran_datum:
        query += " AND f.datum >= ?"
        params.append(str(fran_datum))
    if till_datum:
        query += " AND f.datum <= ?"
        params.append(str(till_datum))
    query += " ORDER BY f.datum, p.namn"
    rows = conn.execute(_q(query), params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def satt_franvaro(personal_id, datum, typ, notering=""):
    """Registrera frånvaro (upsert). Typ='' tar bort frånvaron."""
    conn = get_connection()
    datum_str = str(datum)
    if not typ:
        conn.execute(
            _q("DELETE FROM franvaro WHERE personal_id=? AND datum=?"),
            (personal_id, datum_str)
        )
    else:
        conn.execute(_q("""
            INSERT INTO franvaro (personal_id, datum, typ, notering)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(personal_id, datum)
            DO UPDATE SET typ = excluded.typ, notering = excluded.notering
        """), (personal_id, datum_str, typ, notering))
    conn.commit()
    conn.close()


def bulk_franvaro(personal_id, datum_lista, typ, notering=""):
    """Registrera frånvaro för flera datum."""
    conn = get_connection()
    for d in datum_lista:
        conn.execute(_q("""
            INSERT INTO franvaro (personal_id, datum, typ, notering)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(personal_id, datum)
            DO UPDATE SET typ = excluded.typ, notering = excluded.notering
        """), (personal_id, str(d), typ, notering))
    conn.commit()
    conn.close()


def ta_bort_franvaro(personal_id, fran_datum, till_datum):
    """Ta bort all frånvaro för en person i ett intervall."""
    conn = get_connection()
    conn.execute(
        _q("DELETE FROM franvaro WHERE personal_id=? AND datum >= ? AND datum <= ?"),
        (personal_id, str(fran_datum), str(till_datum))
    )
    conn.commit()
    conn.close()


def ar_franvarande(personal_id, datum):
    """Kolla om en person är frånvarande ett specifikt datum."""
    conn = get_connection()
    row = conn.execute(
        _q("SELECT typ FROM franvaro WHERE personal_id=? AND datum=?"),
        (personal_id, str(datum))
    ).fetchone()
    conn.close()
    return dict(row) if row else None


# ============================================================
# KOMMENTARER
# ============================================================

def hamta_kommentar(personal_id, datum):
    conn = get_connection()
    row = conn.execute(
        _q("SELECT text FROM kommentarer WHERE personal_id=? AND datum=?"),
        (personal_id, str(datum))
    ).fetchone()
    conn.close()
    return row["text"] if row else ""


def satt_kommentar(personal_id, datum, text):
    """Sätt kommentar (upsert). Tom text raderar."""
    conn = get_connection()
    if not text.strip():
        conn.execute(
            _q("DELETE FROM kommentarer WHERE personal_id=? AND datum=?"),
            (personal_id, str(datum))
        )
    else:
        conn.execute(_q(f"""
            INSERT INTO kommentarer (personal_id, datum, text)
            VALUES (?, ?, ?)
            ON CONFLICT(personal_id, datum)
            DO UPDATE SET text = excluded.text, skapad = {_NOW_FUNC}
        """), (personal_id, str(datum), text.strip()))
    conn.commit()
    conn.close()


def hamta_kommentarer_period(personal_id, fran_datum, till_datum):
    conn = get_connection()
    rows = conn.execute(
        _q("SELECT datum, text FROM kommentarer WHERE personal_id=? AND datum >= ? AND datum <= ? ORDER BY datum"),
        (personal_id, str(fran_datum), str(till_datum))
    ).fetchall()
    conn.close()
    return {r["datum"]: r["text"] for r in rows}


# ============================================================
# SAMMANSTÄLLNINGAR (för startsida och lediga resurser)
# ============================================================

def hamta_overbelagda(fran_datum, till_datum):
    """Hitta alla person+datum som är överbelagda."""
    conn = get_connection()
    rows = conn.execute(_q("""
        SELECT a.personal_id, p.namn as personal_namn, a.datum,
               SUM(a.timmar) as total_timmar, p.kapacitet_h
        FROM allokering a
        JOIN personal p ON a.personal_id = p.id
        WHERE a.datum >= ? AND a.datum <= ? AND p.aktiv = 1
        GROUP BY a.personal_id, a.datum, p.namn, p.kapacitet_h
        HAVING SUM(a.timmar) > p.kapacitet_h
        ORDER BY a.datum, p.namn
    """), (str(fran_datum), str(till_datum))).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def hamta_oallokerade(fran_datum, till_datum, arbetsdagar):
    """Hitta alla aktiva personer som saknar allokering på arbetsdagar."""
    personal = hamta_all_personal()
    conn = get_connection()
    resultat = []
    for dag in arbetsdagar:
        dag_str = str(dag)
        for p in personal:
            # Kolla om personen har frånvaro
            franvaro = conn.execute(
                _q("SELECT typ FROM franvaro WHERE personal_id=? AND datum=?"),
                (p["id"], dag_str)
            ).fetchone()
            if franvaro:
                continue  # Frånvarande, hoppa över

            allok = conn.execute(
                _q("SELECT COALESCE(SUM(timmar), 0) as total FROM allokering WHERE personal_id=? AND datum=?"),
                (p["id"], dag_str)
            ).fetchone()
            if allok["total"] == 0:
                resultat.append({
                    "personal_id": p["id"],
                    "personal_namn": p["namn"],
                    "datum": dag_str,
                    "roll": p["roll"]
                })
    conn.close()
    return resultat


def hamta_lediga_resurser(datum):
    """Hitta personer som har ledig kapacitet på ett datum."""
    personal = hamta_all_personal()
    conn = get_connection()
    lediga = []
    for p in personal:
        # Kolla frånvaro
        franvaro = conn.execute(
            _q("SELECT typ FROM franvaro WHERE personal_id=? AND datum=?"),
            (p["id"], str(datum))
        ).fetchone()
        if franvaro:
            continue

        allok = conn.execute(
            _q("SELECT COALESCE(SUM(timmar), 0) as total FROM allokering WHERE personal_id=? AND datum=?"),
            (p["id"], str(datum))
        ).fetchone()
        ledig_tid = p["kapacitet_h"] - allok["total"]
        if ledig_tid > 0:
            lediga.append({
                "personal_id": p["id"],
                "namn": p["namn"],
                "roll": p["roll"],
                "kapacitet_h": p["kapacitet_h"],
                "allokerat": allok["total"],
                "ledigt": ledig_tid
            })
    conn.close()
    return sorted(lediga, key=lambda x: x["ledigt"], reverse=True)


def hamta_teamoversikt(fran_datum, till_datum, arbetsdagar):
    """
    Hämta komplett teamöversikt: per person, per dag - vad de gör.
    Returnerar dict: {personal_id: {datum_str: [{'projekt': namn, 'farg': hex, 'timmar': float}]}}
    """
    personal = hamta_all_personal()
    allokeringar = hamta_allokeringar(fran_datum=fran_datum, till_datum=till_datum)
    franvaro_data = hamta_franvaro(fran_datum=fran_datum, till_datum=till_datum)

    oversikt = {}
    for p in personal:
        oversikt[p["id"]] = {"namn": p["namn"], "roll": p["roll"],
                              "kapacitet_h": p["kapacitet_h"], "dagar": {}}
        for dag in arbetsdagar:
            dag_str = str(dag)
            oversikt[p["id"]]["dagar"][dag_str] = {"allokeringar": [], "franvaro": None}

    # Fyll i allokeringar
    for a in allokeringar:
        pid = a["personal_id"]
        dag_str = a["datum"]
        if pid in oversikt and dag_str in oversikt[pid]["dagar"]:
            oversikt[pid]["dagar"][dag_str]["allokeringar"].append({
                "projekt": a["projekt_namn"],
                "farg": a["projekt_farg"],
                "timmar": a["timmar"]
            })

    # Fyll i frånvaro
    for f in franvaro_data:
        pid = f["personal_id"]
        dag_str = f["datum"]
        if pid in oversikt and dag_str in oversikt[pid]["dagar"]:
            oversikt[pid]["dagar"][dag_str]["franvaro"] = f["typ"]

    return oversikt
