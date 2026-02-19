"""
database.py - Databashantering för Teammanager
Hanterar all CRUD-logik mot SQLite-databasen.
"""

import sqlite3
import os
from datetime import datetime

# Sökväg till databasen (samma mapp som scriptet)
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "teammanager.db")


def get_connection():
    """Skapa och returnera en databasanslutning med foreign keys aktiverade."""
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Skapa alla tabeller om de inte redan finns."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.executescript("""
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
    """)

    conn.commit()
    conn.close()


# ============================================================
# PERSONAL - CRUD
# ============================================================

def hamta_all_personal(bara_aktiva=True):
    """Hämta alla medarbetare. Returnerar lista av dict."""
    conn = get_connection()
    if bara_aktiva:
        rows = conn.execute("SELECT * FROM personal WHERE aktiv = 1 ORDER BY namn").fetchall()
    else:
        rows = conn.execute("SELECT * FROM personal ORDER BY namn").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def lagg_till_personal(namn, roll="", kapacitet_h=8.0):
    """Lägg till en ny medarbetare. Returnerar id eller None vid fel."""
    conn = get_connection()
    try:
        cursor = conn.execute(
            "INSERT INTO personal (namn, roll, kapacitet_h) VALUES (?, ?, ?)",
            (namn.strip(), roll.strip(), kapacitet_h)
        )
        conn.commit()
        return cursor.lastrowid
    except sqlite3.IntegrityError:
        return None
    finally:
        conn.close()


def uppdatera_personal(person_id, namn, roll, kapacitet_h, aktiv):
    """Uppdatera en medarbetare."""
    conn = get_connection()
    try:
        conn.execute(
            "UPDATE personal SET namn=?, roll=?, kapacitet_h=?, aktiv=? WHERE id=?",
            (namn.strip(), roll.strip(), kapacitet_h, aktiv, person_id)
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()


def ta_bort_personal(person_id):
    """Ta bort en medarbetare och alla dess allokeringar."""
    conn = get_connection()
    conn.execute("DELETE FROM personal WHERE id=?", (person_id,))
    conn.commit()
    conn.close()


# ============================================================
# PROJEKT - CRUD
# ============================================================

def hamta_alla_projekt(bara_aktiva=True):
    """Hämta alla projekt."""
    conn = get_connection()
    if bara_aktiva:
        rows = conn.execute("SELECT * FROM projekt WHERE aktiv = 1 ORDER BY namn").fetchall()
    else:
        rows = conn.execute("SELECT * FROM projekt ORDER BY namn").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def lagg_till_projekt(namn, farg="#3498db", startdatum=None, slutdatum=None):
    """Lägg till ett nytt projekt."""
    conn = get_connection()
    try:
        cursor = conn.execute(
            "INSERT INTO projekt (namn, farg, startdatum, slutdatum) VALUES (?, ?, ?, ?)",
            (namn.strip(), farg, startdatum, slutdatum)
        )
        conn.commit()
        return cursor.lastrowid
    except sqlite3.IntegrityError:
        return None
    finally:
        conn.close()


def uppdatera_projekt(projekt_id, namn, farg, startdatum, slutdatum, aktiv):
    """Uppdatera ett projekt."""
    conn = get_connection()
    try:
        conn.execute(
            "UPDATE projekt SET namn=?, farg=?, startdatum=?, slutdatum=?, aktiv=? WHERE id=?",
            (namn.strip(), farg, startdatum, slutdatum, aktiv, projekt_id)
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()


def ta_bort_projekt(projekt_id):
    """Ta bort ett projekt och alla dess allokeringar."""
    conn = get_connection()
    conn.execute("DELETE FROM projekt WHERE id=?", (projekt_id,))
    conn.commit()
    conn.close()


# ============================================================
# ALLOKERING - CRUD
# ============================================================

def hamta_allokeringar(personal_id=None, projekt_id=None, fran_datum=None, till_datum=None):
    """
    Hämta allokeringar med valfria filter.
    Returnerar lista av dict med joinade namn.
    """
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
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def satt_allokering(personal_id, projekt_id, datum, timmar):
    """
    Sätt allokering (upsert). Om timmar=0 tas allokeringen bort.
    """
    conn = get_connection()
    datum_str = str(datum)

    if timmar <= 0:
        conn.execute(
            "DELETE FROM allokering WHERE personal_id=? AND projekt_id=? AND datum=?",
            (personal_id, projekt_id, datum_str)
        )
    else:
        conn.execute("""
            INSERT INTO allokering (personal_id, projekt_id, datum, timmar)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(personal_id, projekt_id, datum)
            DO UPDATE SET timmar = excluded.timmar
        """, (personal_id, projekt_id, datum_str, timmar))

    conn.commit()
    conn.close()


def hamta_dagsbelastning(personal_id, datum):
    """Hämta total belastning för en person på ett datum."""
    conn = get_connection()
    row = conn.execute(
        "SELECT COALESCE(SUM(timmar), 0) as total FROM allokering WHERE personal_id=? AND datum=?",
        (personal_id, str(datum))
    ).fetchone()
    conn.close()
    return row["total"] if row else 0


# ============================================================
# KOMPETENSER
# ============================================================

def hamta_kompetenser(personal_id):
    """Hämta alla kompetenstaggar för en person."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT tagg FROM kompetenser WHERE personal_id=? ORDER BY tagg",
        (personal_id,)
    ).fetchall()
    conn.close()
    return [r["tagg"] for r in rows]


def hamta_alla_kompetenser():
    """Hämta alla unika kompetenstaggar i systemet."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT DISTINCT tagg FROM kompetenser ORDER BY tagg"
    ).fetchall()
    conn.close()
    return [r["tagg"] for r in rows]


def satt_kompetenser(personal_id, taggar):
    """Sätt kompetenser för en person (ersätter befintliga)."""
    conn = get_connection()
    conn.execute("DELETE FROM kompetenser WHERE personal_id=?", (personal_id,))
    for tagg in taggar:
        tagg = tagg.strip()
        if tagg:
            try:
                conn.execute(
                    "INSERT INTO kompetenser (personal_id, tagg) VALUES (?, ?)",
                    (personal_id, tagg)
                )
            except sqlite3.IntegrityError:
                pass
    conn.commit()
    conn.close()
