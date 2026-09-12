from django.db import models
import json


class Location(models.Model):
    """Maps physical locations to tenant organizations."""
    location_id = models.CharField(max_length=50, primary_key=True)
    location_name = models.CharField(max_length=200)
    org_id = models.CharField(max_length=50, db_index=True)
    org_name = models.CharField(max_length=200)
    address = models.CharField(max_length=500, blank=True, default='')
    city = models.CharField(max_length=100, blank=True, default='')
    state = models.CharField(max_length=50, blank=True, default='')

    class Meta:
        db_table = 'locations'

    def __str__(self):
        return f"{self.location_id} - {self.location_name} ({self.org_id})"


class SystemARecord(models.Model):
    """
    Records from System A (source of truth).
    Raw values are stored as text to avoid data loss during ingestion.
    """
    record_id = models.CharField(max_length=50, unique=True)
    normalized_id = models.CharField(max_length=50, db_index=True)
    date = models.CharField(max_length=50, blank=True, default='')
    location = models.ForeignKey(
        Location, on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='system_a_records'
    )
    amount = models.CharField(max_length=100, blank=True, default='')
    quantity = models.CharField(max_length=100, blank=True, default='')
    status = models.CharField(max_length=50, blank=True, default='')
    raw_data = models.TextField(blank=True, default='{}')

    class Meta:
        db_table = 'system_a_records'

    def __str__(self):
        return self.record_id

    def get_raw_data(self):
        return json.loads(self.raw_data)


class SystemBRecord(models.Model):
    """
    Records from System B referencing System A via record_ref.
    Stores both raw and normalized references for auditability.
    """
    system_b_id = models.CharField(max_length=50, unique=True)
    record_ref = models.CharField(max_length=100)
    normalized_ref = models.CharField(max_length=100, db_index=True)
    date = models.CharField(max_length=50, blank=True, default='')
    location = models.ForeignKey(
        Location, on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='system_b_records'
    )
    amount = models.CharField(max_length=100, blank=True, default='')
    quantity = models.CharField(max_length=100, blank=True, default='')
    status = models.CharField(max_length=50, blank=True, default='')
    raw_data = models.TextField(blank=True, default='{}')

    class Meta:
        db_table = 'system_b_records'

    def __str__(self):
        return f"{self.system_b_id} -> {self.record_ref}"


class Discrepancy(models.Model):
    """Persisted discrepancy results from reconciliation runs."""
    REASON_CHOICES = [
        ('MISSING_IN_SYSTEM_B', 'Missing in System B'),
        ('ORPHAN_IN_SYSTEM_B', 'Orphan in System B'),
        ('DUPLICATE_IN_SYSTEM_B', 'Duplicate in System B'),
        ('VALUE_MISMATCH', 'Value Mismatch'),
    ]

    reason = models.CharField(max_length=30, choices=REASON_CHOICES, db_index=True)
    record_id = models.CharField(max_length=100)
    location_id = models.CharField(max_length=50, blank=True, default='')
    org_id = models.CharField(max_length=50, db_index=True)
    system_a_value = models.CharField(max_length=200, blank=True, null=True)
    system_b_value = models.CharField(max_length=200, blank=True, null=True)
    field_name = models.CharField(max_length=50, blank=True, default='')
    details = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'discrepancies'
        ordering = ['org_id', 'reason', 'record_id']

    def __str__(self):
        return f"[{self.reason}] {self.record_id} (Org: {self.org_id})"
