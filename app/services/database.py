"""
app/services/database.py
------------------------
Database connection and initialization with JSON migration (FDA drugs dataset).
Maps FDA JSON fields to SQLite schema.
"""

import sqlite3
import json
import os
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
            
            conn.commit()
            logger.info(f"Database initialized at {self.db_path}")
        except sqlite3.Error as e:
            logger.error(f"Database initialization error: {e}")
            raise DatabaseException(f"Failed to initialize database: {e}")
        finally:
            if conn:
                conn.close()
    
    def _get_connection(self):
        """Get database connection."""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            return conn
        except sqlite3.Error as e:
            raise DatabaseException(f"Failed to connect to database: {e}")
    
    
    def migrate_json(self, json_path: str = "txt.json"):
        """Migrate OpenFDA JSON data to SQLite."""
        try:
            if not os.path.exists(json_path):
                logger.warning(f"JSON file not found: {json_path}")
                return
            
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Check if data already exists
            cursor.execute("SELECT COUNT(*) FROM drugs")
            if cursor.fetchone()[0] > 0:
                logger.info("Database already populated, skipping JSON migration")
                conn.close()
                return
            
            # Read JSON and insert data
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            records = data.get('results', [])
            logger.info(f"Processing {len(records)} drug records from OpenFDA JSON...")
            
            for record in records:
                try:
                    product_ndc = record.get('product_ndc', '')
                    brand_name = record.get('brand_name', '')
                    
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
                        INSERT INTO drugs (
                            product_ndc, brand_name, generic_name,
                            labeler_name, active_ingredients, dosage_form,
                            route, marketing_category, application_number,
                            marketing_start_date, listing_expiration_date,
                            is_finished
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        product_ndc,
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
                except sqlite3.IntegrityError as e:
                    logger.debug(f"Duplicate record skipped: {e}")
                    continue
                except Exception as e:
                    logger.warning(f"Error processing record: {e}")
                    continue
            
            conn.commit()
            cursor.execute("SELECT COUNT(*) FROM drugs")
            count = cursor.fetchone()[0]
            logger.info(f"Migrated {count} drugs from OpenFDA JSON to SQLite")
            conn.close()
            
        except Exception as e:
            logger.error(f"JSON migration error: {e}")
            raise DatabaseException(f"Failed to migrate JSON: {e}")
    
    
    def lookup_by_ndc(self, ndc: str) -> dict:
        """Lookup drug by NDC (National Drug Code)."""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM drugs WHERE TRIM(product_ndc) = ?",
                (str(ndc).strip(),)
            )
            row = cursor.fetchone()
            conn.close()
            return dict(row) if row else None
        except Exception as e:
            raise DatabaseException(f"Lookup failed: {e}")
    
    def lookup_by_application(self, app_num: str) -> dict:
        """Lookup drug by application number."""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM drugs WHERE TRIM(application_number) = ?",
                (str(app_num).strip(),)
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


# Global database instance
db = Database()
