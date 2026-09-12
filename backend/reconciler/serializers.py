"""
API Serializers for the reconciliation engine.
"""

from rest_framework import serializers
from .models import Discrepancy, Location


class DiscrepancySerializer(serializers.ModelSerializer):
    """Serializes discrepancy records for API responses."""

    class Meta:
        model = Discrepancy
        fields = [
            'id', 'reason', 'record_id', 'location_id',
            'org_id', 'system_a_value', 'system_b_value',
            'field_name', 'details', 'created_at',
        ]


class OrganizationSerializer(serializers.Serializer):
    """Serializes organization data for the tenant selector."""
    org_id = serializers.CharField()
    org_name = serializers.CharField()
    location_count = serializers.IntegerField()


class StatsSerializer(serializers.Serializer):
    """Serializes summary statistics."""
    total = serializers.IntegerField()
    missing_in_system_b = serializers.IntegerField()
    orphan_in_system_b = serializers.IntegerField()
    duplicate_in_system_b = serializers.IntegerField()
    value_mismatch = serializers.IntegerField()
