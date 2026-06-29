import mimetypes
from uuid import UUID

from django.core.signing import BadSignature, SignatureExpired, TimestampSigner
from django.http import Http404, HttpResponse, HttpResponseForbidden
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from shared.tenancy.context import get_current_tenant
from ..gateways.local import LocalStorageAdapter


class PrivateFileDownloadView(APIView):
    """Serves private files for local storage.

    Validates token signature, expiration, and tenant ownership.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, token, *args, **kwargs):
        signer = TimestampSigner()
        try:
            # Token expires after 1 hour (3600 seconds)
            physical_key = signer.unsign(token, max_age=3600)
        except SignatureExpired:
            return HttpResponseForbidden("Secure link has expired.")
        except BadSignature:
            return HttpResponseForbidden("Invalid secure link signature.")

        try:
            tenant_part, _ = physical_key.split("/", 1)
            file_tenant_id = UUID(tenant_part)
        except ValueError:
            return HttpResponseForbidden("Malformed file key.")

        current_tenant_id = get_current_tenant()
        if not current_tenant_id or file_tenant_id != current_tenant_id:
            return HttpResponseForbidden("Access Denied: Cross-tenant file read block.")

        adapter = LocalStorageAdapter()
        try:
            content = adapter.read(physical_key)
        except FileNotFoundError:
            raise Http404("File not found.")

        content_type, _ = mimetypes.guess_type(physical_key)
        content_type = content_type or "application/octet-stream"

        response = HttpResponse(content, content_type=content_type)
        if request.GET.get("download") == "1":
            file_name = physical_key.split("/")[-1]
            response["Content-Disposition"] = f'attachment; filename="{file_name}"'

        return response
