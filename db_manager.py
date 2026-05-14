"""
database/db_manager.py
----------------------
Query helpers for the DRAP SQLite database.
"""
import os
import sqlite3
from typing import Optional

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH  = os.path.join(BASE_DIR, "data", "drap.db")


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def lookup_by_registration(reg_no: str) -> Optional[dict]:
    """Return a dict with drug details, or None if not found."""
    reg_no = str(reg_no).strip()
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT * FROM drugs WHERE TRIM(registration_number) = ?",
            (reg_no,)
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def lookup_by_product_name(name: str) -> list:
    """Fuzzy search by product name (case-insensitive LIKE)."""
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT * FROM drugs WHERE product_name LIKE ?",
            (f"%{name.strip()}%",)
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_all_drugs() -> list:
    conn = get_connection()
    try:
        rows = conn.execute("SELECT * FROM drugs ORDER BY sr_no").fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def total_drugs() -> int:
    conn = get_connection()
    try:
        return conn.execute("SELECT COUNT(*) FROM drugs").fetchone()[0]
    finally:
        conn.close()


def mark_expired(registration_number: str) -> bool:
    """Mark a drug as expired by registration number. Returns True if updated."""
    conn = get_connection()
    try:
        cursor = conn.execute(
            "UPDATE drugs SET is_expired = 1 WHERE TRIM(registration_number) = ?",
            (str(registration_number).strip(),)
        )
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()


def search_drugs(query: str, limit: int = 20) -> list:
    """Search by product name, generic name, or company name."""
    conn = get_connection()
    q = f"%{query.strip()}%"
    try:
        rows = conn.execute(
            """
            SELECT * FROM drugs
            WHERE product_name LIKE ?
               OR generic_name LIKE ?
               OR company_name LIKE ?
               OR registration_number LIKE ?
            LIMIT ?
            """,
            (q, q, q, q, limit)
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()