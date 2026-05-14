"""
database/scraper.py
-------------------
Scrapes drug registrations from dra.gov.pk and inserts them into the local
SQLite database.

Usage:
    python database/scraper.py

NOTE: The DRAP portal is a dynamic site. This scraper uses Playwright for
JavaScript rendering. Install browser binaries once:
    playwright install chromium
"""
import asyncio
import os
import sqlite3
import time

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH  = os.path.join(BASE_DIR, "data", "drap.db")

DRAP_SEARCH_URL = "https://www.dra.gov.pk/drug_registration"


async def scrape_drap(max_pages: int = 10) -> list:
    """
    Scrape drug registration records from the DRAP public portal.
    Returns a list of dicts matching the drugs table schema.
    """
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        print("[scraper] playwright not installed. Run: pip install playwright && playwright install chromium")
        return []

    records = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page    = await browser.new_page()

        print(f"[scraper] Navigating to {DRAP_SEARCH_URL}")
        await page.goto(DRAP_SEARCH_URL, timeout=30000)
        await page.wait_for_load_state("networkidle")

        for page_num in range(1, max_pages + 1):
            print(f"[scraper] Scraping page {page_num} …")

            rows = await page.query_selector_all("table tbody tr")
            for row in rows:
                cells = await row.query_selector_all("td")
                if len(cells) < 4:
                    continue
                texts = [await c.inner_text() for c in cells]
                records.append({
                    "registration_number": texts[0].strip(),
                    "product_name":        texts[1].strip() if len(texts) > 1 else "",
                    "generic_name":        texts[2].strip() if len(texts) > 2 else "",
                    "company_name":        texts[3].strip() if len(texts) > 3 else "",
                })

            try:
                next_btn = page.locator("a:has-text('Next'), li.next a")
                if await next_btn.count() == 0:
                    print("[scraper] No more pages.")
                    break
                await next_btn.first.click()
                await page.wait_for_load_state("networkidle")
                time.sleep(0.5)
            except Exception:
                break

        await browser.close()

    print(f"[scraper] Scraped {len(records)} records.")
    return records


def save_to_db(records: list) -> int:
    conn = sqlite3.connect(DB_PATH)
    inserted = 0
    for rec in records:
        try:
            conn.execute(
                """
                INSERT OR IGNORE INTO drugs
                    (registration_number, product_name, generic_name, company_name)
                VALUES (?, ?, ?, ?)
                """,
                (rec["registration_number"], rec["product_name"],
                 rec["generic_name"],        rec["company_name"]),
            )
            inserted += 1
        except sqlite3.Error as e:
            print(f"  [WARN] {e}")
    conn.commit()
    conn.close()
    return inserted


def main() -> None:
    records  = asyncio.run(scrape_drap(max_pages=50))
    inserted = save_to_db(records)
    print(f"[scraper] Done — {inserted} new records saved to {DB_PATH}")


if __name__ == "__main__":
    main()