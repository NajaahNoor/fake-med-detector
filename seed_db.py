"""
database/seed_db.py
-------------------
Ingests data/drap_smpc_output.csv into an SQLite database at data/drap.db.
Run once before launching the app:
    python database/seed_db.py
"""
import os
import sqlite3
import pandas as pd

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_PATH = os.path.join(BASE_DIR, "data", "drap_smpc_output.csv")
DB_PATH  = os.path.join(BASE_DIR, "data", "drap.db")


def create_tables(conn: sqlite3.Connection) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS drugs (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            sr_no               INTEGER,
            registration_number TEXT UNIQUE NOT NULL,
            product_name        TEXT,
            generic_name        TEXT,
            company_name        TEXT,
            tablet_core         TEXT,
            tablet_coat         TEXT,
            excipients          TEXT,
            is_expired          INTEGER DEFAULT 0,
            date_added          TEXT DEFAULT (date('now'))
        )
    """)
    conn.commit()


def ingest_csv(conn: sqlite3.Connection, csv_path: str) -> int:
    df = pd.read_csv(csv_path, dtype=str, encoding="utf-8-sig")
    df.columns = df.columns.str.strip()

    column_map = {
        "Sr No":                    "sr_no",
        "Registration Number":      "registration_number",
        "Product Name":             "product_name",
        "Generic Name":             "generic_name",
        "Company Name":             "company_name",
        "Tablet Core":              "tablet_core",
        "Tablet Coat":              "tablet_coat",
        "Excipients (non-tablet)":  "excipients",
    }
    df = df.rename(columns=column_map)
    df = df[[c for c in column_map.values() if c in df.columns]]
    df = df.fillna("")
    df["registration_number"] = df["registration_number"].str.strip()

    inserted = 0
    for _, row in df.iterrows():
        try:
            conn.execute(
                """
                INSERT OR IGNORE INTO drugs
                    (sr_no, registration_number, product_name, generic_name,
                     company_name, tablet_core, tablet_coat, excipients)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    row.get("sr_no", ""),
                    row["registration_number"],
                    row.get("product_name", ""),
                    row.get("generic_name", ""),
                    row.get("company_name", ""),
                    row.get("tablet_core", ""),
                    row.get("tablet_coat", ""),
                    row.get("excipients", ""),
                ),
            )
            inserted += 1
        except sqlite3.Error as e:
            print(f"  [WARN] Skipping row {row.get('sr_no', '?')}: {e}")

    conn.commit()
    return inserted


def main() -> None:
    print(f"[seed_db] CSV  : {CSV_PATH}")
    print(f"[seed_db] DB   : {DB_PATH}")
    if not os.path.exists(CSV_PATH):
        raise FileNotFoundError(f"Seed CSV not found: {CSV_PATH}")

    conn = sqlite3.connect(DB_PATH)
    create_tables(conn)
    n = ingest_csv(conn, CSV_PATH)
    conn.close()
    print(f"[seed_db] Done — {n} rows inserted/ignored.")


if __name__ == "__main__":
    main()