"""
import_data management command
==============================
Ingests CSV data from the data/ directory into the database.
Handles messy data gracefully without dropping rows.
Also runs the reconciliation engine and persists discrepancies.
"""

import csv
import json
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import models

from reconciler.models import Location, SystemARecord, SystemBRecord, Discrepancy
from reconciler.services.comparator import (
    normalize_reference,
    reconcile_records,
)


class Command(BaseCommand):
    help = 'Import CSV data from data/ directory and run reconciliation'

    def add_arguments(self, parser):
        parser.add_argument(
            '--data-dir',
            type=str,
            default=str(settings.DATA_DIR),
            help='Path to the directory containing CSV files',
        )
        parser.add_argument(
            '--skip-reconcile',
            action='store_true',
            help='Skip running the reconciliation engine after import',
        )

    def handle(self, *args, **options):
        data_dir = Path(options['data_dir'])

        if not data_dir.exists():
            raise CommandError(f"Data directory not found: {data_dir}")

        self.stdout.write(self.style.NOTICE(f"Importing from: {data_dir}"))

        # Import in dependency order
        self._import_locations(data_dir / 'locations.csv')
        self._import_system_a(data_dir / 'system_a.csv')
        self._import_system_b(data_dir / 'system_b.csv')

        if not options['skip_reconcile']:
            self._run_reconciliation()

        self.stdout.write(self.style.SUCCESS("Import complete!"))

    def _import_locations(self, filepath: Path):
        """Import locations.csv - establishes tenant mapping."""
        if not filepath.exists():
            raise CommandError(f"File not found: {filepath}")

        self.stdout.write(f"  Importing locations from {filepath.name}...")

        # Clear existing data
        Location.objects.all().delete()

        count = 0
        with open(filepath, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    Location.objects.create(
                        location_id=row.get('location_id', '').strip(),
                        location_name=row.get('location_name', '').strip(),
                        org_id=row.get('org_id', '').strip(),
                        org_name=row.get('org_name', '').strip(),
                        address=row.get('address', '').strip(),
                        city=row.get('city', '').strip(),
                        state=row.get('state', '').strip(),
                    )
                    count += 1
                except Exception as e:
                    self.stderr.write(
                        self.style.WARNING(f"  Skipped location row: {row} - {e}")
                    )

        self.stdout.write(self.style.SUCCESS(f"  -> Imported {count} locations"))

    def _import_system_a(self, filepath: Path):
        """Import system_a.csv - stores raw values to avoid data loss."""
        if not filepath.exists():
            raise CommandError(f"File not found: {filepath}")

        self.stdout.write(f"  Importing System A from {filepath.name}...")

        SystemARecord.objects.all().delete()

        count = 0
        with open(filepath, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    record_id = row.get('record_id', '').strip()
                    location_id = row.get('location_id', '').strip()

                    # Try to link to location; don't fail if missing
                    location = None
                    if location_id:
                        try:
                            location = Location.objects.get(location_id=location_id)
                        except Location.DoesNotExist:
                            pass

                    SystemARecord.objects.create(
                        record_id=record_id,
                        normalized_id=normalize_reference(record_id),
                        date=row.get('date', '').strip(),
                        location=location,
                        amount=row.get('amount', '').strip(),
                        quantity=row.get('quantity', '').strip(),
                        status=row.get('status', '').strip(),
                        raw_data=json.dumps(dict(row)),
                    )
                    count += 1
                except Exception as e:
                    self.stderr.write(
                        self.style.WARNING(f"  Skipped System A row: {row} - {e}")
                    )

        self.stdout.write(self.style.SUCCESS(f"  -> Imported {count} System A records"))

    def _import_system_b(self, filepath: Path):
        """Import system_b.csv - stores both raw and normalized references."""
        if not filepath.exists():
            raise CommandError(f"File not found: {filepath}")

        self.stdout.write(f"  Importing System B from {filepath.name}...")

        SystemBRecord.objects.all().delete()

        count = 0
        with open(filepath, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    record_ref = row.get('record_ref', '')
                    location_id = row.get('location_id', '').strip()
                    system_b_id = row.get('id', '').strip()

                    location = None
                    if location_id:
                        try:
                            location = Location.objects.get(location_id=location_id)
                        except Location.DoesNotExist:
                            pass

                    SystemBRecord.objects.create(
                        system_b_id=system_b_id,
                        record_ref=record_ref.strip(),
                        normalized_ref=normalize_reference(record_ref),
                        date=row.get('date', '').strip(),
                        location=location,
                        amount=row.get('amount', '').strip(),
                        quantity=row.get('quantity', '').strip(),
                        status=row.get('status', '').strip(),
                        raw_data=json.dumps(dict(row)),
                    )
                    count += 1
                except Exception as e:
                    self.stderr.write(
                        self.style.WARNING(f"  Skipped System B row: {row} - {e}")
                    )

        self.stdout.write(self.style.SUCCESS(f"  -> Imported {count} System B records"))

    def _run_reconciliation(self):
        """Execute reconciliation engine and persist discrepancies."""
        self.stdout.write("  Running reconciliation engine...")

        # Build location -> org mapping
        location_org_map = dict(
            Location.objects.values_list('location_id', 'org_id')
        )

        # Convert DB records to plain dicts for the comparator
        records_a = list(
            SystemARecord.objects.values(
                'record_id', 'date', 'amount', 'quantity', 'status'
            ).annotate(location_id=models.F('location__location_id'))
        )
        # Handle None location_id
        for r in records_a:
            if r['location_id'] is None:
                r['location_id'] = ''

        records_b = list(
            SystemBRecord.objects.values(
                'record_ref', 'date', 'amount', 'quantity', 'status'
            ).annotate(location_id=models.F('location__location_id'))
        )
        for r in records_b:
            if r['location_id'] is None:
                r['location_id'] = ''

        # Run the pure-function reconciliation
        results = reconcile_records(records_a, records_b, location_org_map)

        # Persist discrepancies
        Discrepancy.objects.all().delete()

        discrepancy_objects = [
            Discrepancy(
                reason=d.reason,
                record_id=d.record_id,
                location_id=d.location_id,
                org_id=d.org_id,
                system_a_value=d.system_a_value,
                system_b_value=d.system_b_value,
                field_name=d.field_name,
                details=d.details,
            )
            for d in results
        ]
        Discrepancy.objects.bulk_create(discrepancy_objects)

        self.stdout.write(self.style.SUCCESS(
            f"  -> Found {len(results)} discrepancies"
        ))

        # Summary by reason
        from collections import Counter
        reason_counts = Counter(d.reason for d in results)
        for reason, count in sorted(reason_counts.items()):
            self.stdout.write(f"     {reason}: {count}")

        # Summary by org
        org_counts = Counter(d.org_id for d in results)
        for org, count in sorted(org_counts.items()):
            self.stdout.write(f"     {org}: {count}")
