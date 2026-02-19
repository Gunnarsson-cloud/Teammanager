"""
calendar_utils.py - Kalenderberäkningar för Teammanager
Hanterar svenska helgdagar, arbetsdagar och kalendervyer.
"""

import holidays
import pandas as pd
from datetime import date, timedelta
from functools import lru_cache


@lru_cache(maxsize=10)
def hamta_svenska_helgdagar(ar_start, ar_slut):
    """
    Hämta alla svenska röda dagar för ett intervall av år.
    Returnerar en dict {datum: namn_på_helgdag}.
    Cachad för prestanda.
    """
    se_holidays = holidays.Sweden(years=range(ar_start, ar_slut + 1))
    return dict(se_holidays)


def ar_arbetsdag(datum, helgdagar=None):
    """
    Kontrollera om ett datum är en arbetsdag.
    Arbetsdag = inte lördag, inte söndag, inte röd dag.
    """
    if datum.weekday() >= 5:  # Lördag=5, Söndag=6
        return False
    if helgdagar is None:
        helgdagar = hamta_svenska_helgdagar(datum.year, datum.year)
    return datum not in helgdagar


def hamta_arbetsdagar(fran_datum, till_datum):
    """
    Returnera en lista av alla arbetsdagar i ett datumintervall.
    """
    helgdagar = hamta_svenska_helgdagar(fran_datum.year, till_datum.year)
    arbetsdagar = []
    current = fran_datum
    while current <= till_datum:
        if ar_arbetsdag(current, helgdagar):
            arbetsdagar.append(current)
        current += timedelta(days=1)
    return arbetsdagar


def antal_arbetsdagar_i_manad(ar, manad):
    """Räkna antal arbetsdagar i en specifik månad."""
    fran = date(ar, manad, 1)
    if manad == 12:
        till = date(ar, 12, 31)
    else:
        till = date(ar, manad + 1, 1) - timedelta(days=1)
    return len(hamta_arbetsdagar(fran, till))


def skapa_manadskalender(ar, manad):
    """
    Skapa kalenderdata för en månad.
    Returnerar en lista av veckors-listor med daginfo.
    Varje dag = dict med {datum, dag, typ, helgdagsnamn}
    typ: 'arbetsdag', 'helg', 'rod_dag'
    """
    helgdagar = hamta_svenska_helgdagar(ar, ar)
    fran = date(ar, manad, 1)
    if manad == 12:
        till = date(ar, 12, 31)
    else:
        till = date(ar, manad + 1, 1) - timedelta(days=1)

    # Bygg lista av dagar
    dagar = []
    current = fran
    while current <= till:
        if current in helgdagar:
            typ = "rod_dag"
            helgnamn = helgdagar[current]
        elif current.weekday() >= 5:
            typ = "helg"
            helgnamn = "Lördag" if current.weekday() == 5 else "Söndag"
        else:
            typ = "arbetsdag"
            helgnamn = ""

        dagar.append({
            "datum": current,
            "dag": current.day,
            "veckodag": current.weekday(),  # 0=Måndag
            "typ": typ,
            "helgdagsnamn": helgnamn,
            "vecka": current.isocalendar()[1]
        })
        current += timedelta(days=1)

    return dagar


VECKODAG_NAMN = ["Mån", "Tis", "Ons", "Tor", "Fre", "Lör", "Sön"]
MANAD_NAMN = [
    "", "Januari", "Februari", "Mars", "April", "Maj", "Juni",
    "Juli", "Augusti", "September", "Oktober", "November", "December"
]
