"""
CSV Lead Importer — Bulk-load leads from a CSV file into the database.

Expected CSV columns (header row required):
  business_name  — Required
  website_url    — Required (used for duplicate detection)
  email          — Optional
  phone          — Optional
  industry       — Optional
  location       — Optional

Any extra columns are silently ignored.
"""

import csv
import logging
from pathlib import Path
from database.repository import LeadRepository

logger = logging.getLogger(__name__)


class LeadImporter:
    """Import leads from a CSV file into the database."""

    REQUIRED_COLUMNS = {'business_name', 'website_url'}
    OPTIONAL_COLUMNS = {'email', 'phone', 'industry', 'location'}
    ALL_COLUMNS = REQUIRED_COLUMNS | OPTIONAL_COLUMNS

    @staticmethod
    def import_csv(filepath: str, source: str = 'csv_import') -> dict:
        """
        Read a CSV file and insert leads into the database.

        Returns a summary dict:
            { 'imported': int, 'duplicates': int, 'errors': int, 'total_rows': int }
        """
        path = Path(filepath)
        if not path.exists():
            logger.error(f"File not found: {filepath}")
            return {'imported': 0, 'duplicates': 0, 'errors': 0, 'total_rows': 0}

        imported = 0
        duplicates = 0
        errors = 0
        total_rows = 0

        with open(path, newline='', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)

            # ── Validate header ──────────────────────────────────────
            if reader.fieldnames is None:
                logger.error("CSV file is empty or has no header row.")
                return {'imported': 0, 'duplicates': 0, 'errors': 0, 'total_rows': 0}

            # Normalise header names (strip whitespace, lowercase)
            clean_headers = {h.strip().lower(): h for h in reader.fieldnames}
            missing = LeadImporter.REQUIRED_COLUMNS - set(clean_headers.keys())
            if missing:
                logger.error(f"CSV is missing required columns: {', '.join(missing)}")
                logger.info(f"Found columns: {', '.join(clean_headers.keys())}")
                logger.info("Required: business_name, website_url")
                return {'imported': 0, 'duplicates': 0, 'errors': 0, 'total_rows': 0}

            # ── Process rows ─────────────────────────────────────────
            for row_num, raw_row in enumerate(reader, start=2):  # row 2 = first data row
                total_rows += 1

                # Normalise keys
                row = {k.strip().lower(): (v.strip() if v else '') for k, v in raw_row.items()}

                business_name = row.get('business_name', '').strip()
                website_url = row.get('website_url', '').strip()

                # ── Validation ───────────────────────────────────────
                if not business_name:
                    logger.warning(f"Row {row_num}: missing business_name — skipped")
                    errors += 1
                    continue

                if not website_url:
                    logger.warning(f"Row {row_num}: missing website_url — skipped")
                    errors += 1
                    continue

                # Basic URL cleanup
                if not website_url.startswith(('http://', 'https://')):
                    website_url = 'https://' + website_url

                # ── Duplicate check ──────────────────────────────────
                if LeadRepository.exists(website_url):
                    logger.info(f"Row {row_num}: duplicate (already exists) — {business_name}")
                    duplicates += 1
                    continue

                # ── Insert ───────────────────────────────────────────
                try:
                    kwargs = {'source': source}
                    for col in LeadImporter.OPTIONAL_COLUMNS:
                        val = row.get(col, '').strip()
                        if val:
                            kwargs[col] = val

                    LeadRepository.create(
                        business_name=business_name,
                        website_url=website_url,
                        **kwargs
                    )
                    imported += 1
                    logger.info(f"Row {row_num}: ✓ imported — {business_name}")

                except Exception as e:
                    errors += 1
                    logger.error(f"Row {row_num}: error saving {business_name} — {e}")

        # ── Summary ──────────────────────────────────────────────────
        summary = {
            'imported': imported,
            'duplicates': duplicates,
            'errors': errors,
            'total_rows': total_rows,
        }

        logger.info(f"\n{'='*50}")
        logger.info(f"CSV Import Complete — {path.name}")
        logger.info(f"{'='*50}")
        logger.info(f"  Total rows:  {total_rows}")
        logger.info(f"  Imported:    {imported}")
        logger.info(f"  Duplicates:  {duplicates}")
        logger.info(f"  Errors:      {errors}")
        logger.info(f"{'='*50}\n")

        return summary

    @staticmethod
    def generate_template(filepath: str = None) -> str:
        """
        Write a sample CSV template file and return the path.
        Useful so users know the expected format.
        """
        if filepath is None:
            from config.settings import Config
            filepath = str(Config.DATA_DIR / 'sample_leads.csv')

        path = Path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)

        with open(path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['business_name', 'website_url', 'email', 'phone', 'industry', 'location'])
            writer.writerow([
                'Mama Rosa Pizzeria',
                'https://www.mamarosapizza.com',
                'info@mamarosapizza.com',
                '555-123-4567',
                'restaurant',
                'Brooklyn, NY',
            ])
            writer.writerow([
                'Bright Smile Dental',
                'https://www.brightsmile.com',
                'hello@brightsmile.com',
                '555-234-5678',
                'dental',
                'Austin, TX',
            ])
            writer.writerow([
                'Summit Realty Group',
                'https://www.summitrealty.com',
                '',
                '555-345-6789',
                'real estate',
                'Denver, CO',
            ])

        logger.info(f"Sample CSV template saved: {path}")
        return str(path)
