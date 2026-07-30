"""Base view and viewset foundations for Nextora POS API."""
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet

from shared.api.filters import OrderingFilter, SearchFilter, SimpleFilterBackend
from shared.api.pagination import StandardPagination
from shared.api.permissions import BasePermission
from shared.api.renderers import StandardJSONRenderer


class BaseAPIView(APIView):
    """Base APIView class enforcing standard renderers, authentication, and permissions."""

    renderer_classes = [StandardJSONRenderer]
    permission_classes = [IsAuthenticated, BasePermission]


class BaseModelViewSet(ModelViewSet):
    """Base ModelViewSet class pre-configured for standard listing and mutations.

    Configured with standard formatting, pagination, query filtering, and
    permissions to eliminate boilerplate across bounded context APIs.
    """

    renderer_classes = [StandardJSONRenderer]
    permission_classes = [IsAuthenticated, BasePermission]
    pagination_class = StandardPagination
    filter_backends = [SimpleFilterBackend, SearchFilter, OrderingFilter]
