"""
database/db_manager.py
----------------------
Query helpers for the DRAP SQLite database.
"""
import os
import re
import sqlite3
from typing import Optional

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH  = os.path.join(BASE_DIR, "data", "drap.db")


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _normalize_lookup_value(value: str) -> tuple[str, str]:
    exact = str(value or "").strip().upper()
    exact = exact.replace("–", "-").replace("—", "-")
    exact = re.sub(r"^(?:NDC|NDC\s*NO\.?|NDC\s*#)\s*[:#-]?\s*", "", exact)
    compact = re.sub(r"[^A-Z0-9]", "", exact)
    return exact, compact


def _has_column(conn: sqlite3.Connection, table: str, column: str) -> bool:
    cursor = conn.execute(f"PRAGMA table_info({table})")
    return any(row[1] == column for row in cursor.fetchall())


def lookup_by_registration(reg_no: str) -> Optional[dict]:
    """Return a dict with drug details, or None if not found."""
    reg_no, compact = _normalize_lookup_value(reg_no)
    conn = get_connection()
    try:
        if _has_column(conn, "drugs", "registration_number"):
            row = conn.execute(
                "SELECT * FROM drugs WHERE TRIM(registration_number) = ?",
                (reg_no,)
            ).fetchone()
            if row:
                return dict(row)

        if _has_column(conn, "drugs", "product_ndc"):
            row = conn.execute(
                """
                SELECT drugs.*, drug_packages.package_ndc AS matched_package_ndc,
                       drug_packages.description AS package_description
                FROM drugs
                LEFT JOIN drug_packages ON drugs.product_ndc = drug_packages.product_ndc
                WHERE TRIM(drugs.product_ndc) = ?
                   OR REPLACE(REPLACE(TRIM(drugs.product_ndc), '-', ''), ' ', '') = ?
                   OR TRIM(drug_packages.package_ndc) = ?
                   OR REPLACE(REPLACE(TRIM(drug_packages.package_ndc), '-', ''), ' ', '') = ?
                """,
                (reg_no, compact, reg_no, compact),
            ).fetchone()
            if row:
                return dict(row)

        return None
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