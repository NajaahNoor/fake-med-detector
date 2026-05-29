"""
app/services/database.py
------------------------
Database connection and initialization with JSON migration (FDA drugs dataset).
Maps FDA JSON fields to SQLite schema.
"""

import sqlite3
import json
import os
import re
from app.core.config import settings
from app.core.logging import logger
from app.core.exceptions import DatabaseException


class Database:
    """SQLite database wrapper with FDA JSON support."""
    
    def __init__(self, db_path: str = None):
        """Initialize database connection."""
        self.db_path = db_path or settings.db_path
        self._ensure_db_directory()
        self._init_db()
    
    def _ensure_db_directory(self):
        """Ensure database directory exists."""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
    
    def _init_db(self):
        """Initialize database schema for OpenFDA drugs."""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Create drugs table with OpenFDA fields
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS drugs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    product_ndc TEXT UNIQUE NOT NULL,
                    package_ndcs TEXT,
                    brand_name TEXT NOT NULL,
                    generic_name TEXT,
                    labeler_name TEXT,
                    active_ingredients TEXT,
                    dosage_form TEXT,
                    route TEXT,
                    marketing_category TEXT,
                    application_number TEXT,
                    marketing_start_date TEXT,
                    listing_expiration_date TEXT,
                    is_finished INTEGER DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS drug_packages (
                    package_ndc TEXT PRIMARY KEY,
                    product_ndc TEXT NOT NULL,
                    description TEXT,
                    marketing_start_date TEXT,
                    sample INTEGER DEFAULT 0,
                    FOREIGN KEY(product_ndc) REFERENCES drugs(product_ndc)
                )
            """)
            self._ensure_column(cursor, "drugs", "package_ndcs", "TEXT")
            
            conn.commit()
            logger.info(f"Database initialized at {self.db_path}")
        except sqlite3.Error as e:
            logger.error(f"Database initialization error: {e}")
            raise DatabaseException(f"Failed to initialize database: {e}")
        finally:
            if conn:
                conn.close()

    def _ensure_column(self, cursor, table_name: str, column_name: str, column_type: str):
        """Add a column to an existing SQLite table if it is missing."""
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = {row[1] for row in cursor.fetchall()}
        if column_name not in columns:
            cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}")
    
    def _get_connection(self):
        """Get database connection."""
        try:
            conn = sqlite3.connect(self.db_path, timeout=30)
            conn.row_factory = sqlite3.Row
            return conn
        except sqlite3.Error as e:
            raise DatabaseException(f"Failed to connect to database: {e}")

    def _normalize_lookup_value(self, value: str) -> tuple[str, str]:
        """Normalize OCR/user-entered NDC/application values for lookup."""
        exact = str(value or "").strip().upper()
        exact = exact.replace("–", "-").replace("—", "-")
        exact = re.sub(r"^(?:NDC|NDC\s*NO\.?|NDC\s*#)\s*[:#-]?\s*", "", exact)
        compact = re.sub(r"[^A-Z0-9]", "", exact)
        return exact, compact
    
    
    def migrate_json(self, json_path: str = "txt.json"):
        """Migrate OpenFDA JSON data to SQLite."""
        try:
            if not os.path.exists(json_path):
                logger.warning(f"JSON file not found: {json_path}")
                return
            
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Read JSON and insert data
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            records = data.get('results', [])
            logger.info(f"Processing {len(records)} drug records from OpenFDA JSON...")
            
            for record in records:
                try:
                    product_ndc = record.get('product_ndc', '')
                    brand_name = record.get('brand_name', '')
                    packaging = record.get('packaging', []) or []
                    package_ndcs = "; ".join([
                        pkg.get("package_ndc", "").strip()
                        for pkg in packaging
                        if pkg.get("package_ndc")
                    ])
                    
                    # Extract active ingredients as formatted string
                    active_ing = record.get('active_ingredients', [])
                    ingredients_str = "; ".join([
                        f"{ing['name']} {ing.get('strength', '')}" 
                        for ing in active_ing
                    ]) if active_ing else ""
                    
                    # Extract route as string
                    route_list = record.get('route', [])
                    route_str = "; ".join(route_list) if route_list else ""
                    
                    cursor.execute("""
                        INSERT OR REPLACE INTO drugs (
                            product_ndc, package_ndcs, brand_name, generic_name,
                            labeler_name, active_ingredients, dosage_form,
                            route, marketing_category, application_number,
                            marketing_start_date, listing_expiration_date,
                            is_finished
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        product_ndc,
                        package_ndcs or None,
                        brand_name,
                        record.get('generic_name', '') or None,
                        record.get('labeler_name', '') or None,
                        ingredients_str or None,
                        record.get('dosage_form', '') or None,
                        route_str or None,
                        record.get('marketing_category', '') or None,
                        record.get('application_number', '') or None,
                        record.get('marketing_start_date', '') or None,
                        record.get('listing_expiration_date', '') or None,
                        1 if record.get('finished', True) else 0
                    ))
                    for pkg in packaging:
                        package_ndc = (pkg.get("package_ndc") or "").strip()
                        if not package_ndc:
                            continue
                        cursor.execute("""
                            INSERT OR REPLACE INTO drug_packages (
                                package_ndc, product_ndc, description,
                                marketing_start_date, sample
                            ) VALUES (?, ?, ?, ?, ?)
                        """, (
                            package_ndc,
                            product_ndc,
                            pkg.get("description") or None,
                            pkg.get("marketing_start_date") or None,
                            1 if pkg.get("sample", False) else 0
                        ))
                except sqlite3.IntegrityError as e:
                    logger.debug(f"Duplicate record skipped: {e}")
                    continue
                except Exception as e:
                    logger.warning(f"Error processing record: {e}")
                    continue
            
            conn.commit()
            cursor.execute("SELECT COUNT(*) FROM drugs")
            count = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM drug_packages")
            package_count = cursor.fetchone()[0]
            logger.info(
                f"Migrated {count} drugs and {package_count} packages from OpenFDA JSON to SQLite"
            )
            conn.close()
            
        except Exception as e:
            logger.error(f"JSON migration error: {e}")
            raise DatabaseException(f"Failed to migrate JSON: {e}")
    
    
    def lookup_by_ndc(self, ndc: str) -> dict:
        """Lookup drug by product NDC or package NDC."""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            ndc, ndc_compact = self._normalize_lookup_value(ndc)
            cursor.execute(
                """
                SELECT * FROM drugs
                WHERE TRIM(product_ndc) = ?
                   OR REPLACE(REPLACE(TRIM(product_ndc), '-', ''), ' ', '') = ?
                """,
                (ndc, ndc_compact)
            )
            row = cursor.fetchone()
            if not row:
                cursor.execute("""
                    SELECT drugs.*, drug_packages.package_ndc AS matched_package_ndc,
                           drug_packages.description AS package_description
                    FROM drug_packages
                    JOIN drugs ON drugs.product_ndc = drug_packages.product_ndc
                    WHERE TRIM(drug_packages.package_ndc) = ?
                       OR REPLACE(REPLACE(TRIM(drug_packages.package_ndc), '-', ''), ' ', '') = ?
                """, (ndc, ndc_compact))
                row = cursor.fetchone()
            conn.close()
            return dict(row) if row else None
        except Exception as e:
            raise DatabaseException(f"Lookup failed: {e}")

    def lookup_ndc_prefix(self, ndc: str, limit: int = 10) -> list[dict]:
        """
        Return possible drugs for a short NDC labeler prefix.

        OCR sometimes captures only the first NDC segment, e.g. "NDC 13107".
        That prefix can be valid while still being too incomplete to verify a
        single medicine, so callers should treat these as ambiguous candidates.
        """
        try:
            _, compact = self._normalize_lookup_value(ndc)
            if not compact.isdigit() or len(compact) < 4:
                return []

            conn = self._get_connection()
            cursor = conn.cursor()
            prefix = f"{compact}-%"
            cursor.execute("""
                SELECT drugs.*, NULL AS matched_package_ndc,
                       NULL AS package_description
                FROM drugs
                WHERE drugs.product_ndc LIKE ?
                UNION
                SELECT drugs.*, drug_packages.package_ndc AS matched_package_ndc,
                       drug_packages.description AS package_description
                FROM drug_packages
                JOIN drugs ON drugs.product_ndc = drug_packages.product_ndc
                WHERE drug_packages.package_ndc LIKE ?
                LIMIT ?
            """, (prefix, prefix, limit))
            rows = cursor.fetchall()
            conn.close()
            return [dict(row) for row in rows]
        except Exception as e:
            raise DatabaseException(f"Prefix lookup failed: {e}")
    
    def lookup_by_application(self, app_num: str) -> dict:
        """Lookup drug by application number."""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            app_num, app_compact = self._normalize_lookup_value(app_num)
            cursor.execute(
                """
                SELECT * FROM drugs
                WHERE TRIM(UPPER(application_number)) = ?
                   OR REPLACE(REPLACE(TRIM(UPPER(application_number)), '-', ''), ' ', '') = ?
                """,
                (app_num, app_compact)
            )
            row = cursor.fetchone()
            conn.close()
            return dict(row) if row else None
        except Exception as e:
            raise DatabaseException(f"Lookup failed: {e}")
    
    def lookup_by_registration(self, reg_no: str) -> dict:
        """Lookup drug by registration number (maps to NDC or app number)."""
        # Try NDC first
        result = self.lookup_by_ndc(reg_no)
        if result:
            return result
        # Try application number
        return self.lookup_by_application(reg_no)
    
    
    def search_by_name(self, name: str, limit: int = 10) -> list:
        """Search drugs by brand name, generic name, or labeler."""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            query = """
                SELECT * FROM drugs 
                WHERE brand_name LIKE ? 
                   OR generic_name LIKE ? 
                   OR labeler_name LIKE ?
                LIMIT ?
            """
            search_term = f"%{name}%"
            cursor.execute(query, (search_term, search_term, search_term, limit))
            rows = cursor.fetchall()
            conn.close()
            return [dict(row) for row in rows]
        except Exception as e:
            raise DatabaseException(f"Search failed: {e}")
    
    def is_healthy(self) -> bool:
        """Check if database is accessible."""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            conn.close()
            return True
        except Exception:
            return False

    def get_stats(self) -> dict:
        """Return database path and table counts for diagnostics."""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM drugs")
            drug_count = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM drug_packages")
            package_count = cursor.fetchone()[0]
            conn.close()
            return {
                "path": os.path.abspath(self.db_path),
                "drug_count": drug_count,
                "package_count": package_count,
            }
        except Exception as e:
            raise DatabaseException(f"Failed to read database stats: {e}")


# Global database instance
db = Database()
