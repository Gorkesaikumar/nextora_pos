"""Gateway webhook receiver (unauthenticated, CSRF-exempt, tenant-agnostic).

The endpoint lives on the platform domain and is exempt from tenant resolution
(the tenant is derived from the event payload). Signature verification is the
security boundary.
"""
import logging

from django.http import HttpRequest, HttpResponseBadRequest, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from contexts.billing.exceptions import GatewayError
from contexts.billing.services.webhook_service import handle_webhook

logger = logging.getLogger("nextora.billing")


@csrf_exempt
@require_POST
def razorpay_webhook(request: HttpRequest) -> JsonResponse:
    signature = request.headers.get("X-Razorpay-Signature", "")
    try:
        result = handle_webhook(request.body, signature)
    except GatewayError:
        logger.warning("Rejected billing webhook (signature/parse failure).")
        return HttpResponseBadRequest("invalid")
    return JsonResponse({"status": result})
