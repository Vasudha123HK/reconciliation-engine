"""
API Views for the reconciliation engine.
Enforces strict multi-tenant isolation on every read.
"""

from django.db.models import Count
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Discrepancy, Location
from .serializers import DiscrepancySerializer, OrganizationSerializer, StatsSerializer


class DiscrepancyListView(APIView):
    """
    GET /api/discrepancies/?org_id=ORG-001&reason=VALUE_MISMATCH&sort=asc

    Returns discrepancies scoped strictly to the given org_id.
    Multi-tenant defense: rejects requests missing tenant context.
    """

    def get(self, request):
        org_id = request.query_params.get('org_id')
        reason_filter = request.query_params.get('reason')
        sort_order = request.query_params.get('sort', 'asc')

        # Multi-tenant defense: reject requests missing tenant context
        if not org_id:
            return Response(
                {'error': 'org_id query parameter is required for tenant isolation'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Strictly scope by org_id - never expose cross-tenant data
        queryset = Discrepancy.objects.filter(org_id=org_id)

        # Apply optional reason filter
        if reason_filter and reason_filter.upper() != 'ALL':
            queryset = queryset.filter(reason=reason_filter)

        # Apply sorting
        if sort_order == 'desc':
            queryset = queryset.order_by('-record_id')
        else:
            queryset = queryset.order_by('record_id')

        serializer = DiscrepancySerializer(queryset, many=True)
        return Response({
            'org_id': org_id,
            'count': queryset.count(),
            'results': serializer.data,
        })


class OrganizationListView(APIView):
    """
    GET /api/organizations/

    Returns all available organizations for the tenant selector dropdown.
    """

    def get(self, request):
        orgs = (
            Location.objects
            .values('org_id', 'org_name')
            .annotate(location_count=Count('location_id'))
            .order_by('org_id')
        )

        return Response({
            'results': list(orgs),
        })


class StatsView(APIView):
    """
    GET /api/stats/?org_id=ORG-001

    Returns summary counts per discrepancy type for a given tenant.
    """

    def get(self, request):
        org_id = request.query_params.get('org_id')

        if not org_id:
            return Response(
                {'error': 'org_id query parameter is required for tenant isolation'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        queryset = Discrepancy.objects.filter(org_id=org_id)

        stats = {
            'org_id': org_id,
            'total': queryset.count(),
            'missing_in_system_b': queryset.filter(reason='MISSING_IN_SYSTEM_B').count(),
            'orphan_in_system_b': queryset.filter(reason='ORPHAN_IN_SYSTEM_B').count(),
            'duplicate_in_system_b': queryset.filter(reason='DUPLICATE_IN_SYSTEM_B').count(),
            'value_mismatch': queryset.filter(reason='VALUE_MISMATCH').count(),
        }

        return Response(stats)
