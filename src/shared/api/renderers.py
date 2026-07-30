"""Standard JSON Renderer for Nextora POS API.

Ensures every successful API response matches the structured format:
{
    "success": true,
    "message": "...",
    "data": { ... } or [ ... ],
    "errors": [],
    "meta": { ... }
}
"""
from rest_framework.renderers import JSONRenderer


class StandardJSONRenderer(JSONRenderer):
    """Envelops API responses into a standard JSON structure."""

    def render(self, data, accepted_media_type=None, renderer_context=None):
        response = renderer_context.get("response") if renderer_context else None
        status_code = response.status_code if response else 200

        # Check if the data is already wrapped (escape hatch)
        if isinstance(data, dict) and all(
            k in data for k in ("success", "message", "data", "errors", "meta")
        ):
            return super().render(data, accepted_media_type, renderer_context)

        success = status_code < 400
        message = "Operation successful" if success else "Operation failed"
        errors = []
        meta = {}
        data_payload = data

        if not success:
            # Errors should already be formatted by the global exception handler as a list.
            # If not (e.g. bypass DRF exception flow), wrap it.
            if isinstance(data, list):
                errors = data
            elif isinstance(data, dict):
                # Standard DRF detail errors could fall here if exception handler was bypassed
                if "detail" in data:
                    errors = [{"message": str(data["detail"]), "code": "error"}]
                else:
                    errors = [
                        {"field": field, "message": str(errs), "code": "validation_error"}
                        for field, errs in data.items()
                    ]
            else:
                errors = [{"message": str(data), "code": "error"}]
            data_payload = {}
        else:
            # Extract standard DRF pagination fields into meta object
            if isinstance(data, dict) and any(
                k in data for k in ("results", "count", "next", "previous")
            ):
                meta = {
                    "count": data.get("count"),
                    "next": data.get("next"),
                    "previous": data.get("previous"),
                }
                data_payload = data.get("results")
            elif isinstance(data, dict):
                # Extract descriptive message or detail from dictionary success payload
                data_copy = data.copy()
                if "detail" in data_copy:
                    message = data_copy.pop("detail")
                elif "message" in data_copy:
                    message = data_copy.pop("message")
                data_payload = data_copy

            # Check for custom message and meta attributes set on the response
            if response:
                custom_message = getattr(response, "custom_message", None)
                if custom_message:
                    message = custom_message
                custom_meta = getattr(response, "custom_meta", None)
                if custom_meta:
                    meta.update(custom_meta)

        # Enforce that data is either a dict or list (no null or primitive base types)
        if data_payload is None:
            data_payload = {}

        envelope = {
            "success": success,
            "message": message,
            "data": data_payload,
            "errors": errors,
            "meta": meta,
        }

        # ponytail simplified: use super JSONRenderer to output clean json string
        return super().render(envelope, accepted_media_type, renderer_context)
