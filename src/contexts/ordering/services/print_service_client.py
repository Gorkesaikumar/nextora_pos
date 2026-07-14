"""Centralized HTTP client for the Nextora Print Service.

Every local print request from Nextora POS goes through this single client.
It encapsulates server communication, error handling, timeout management, and
response normalization.

Service base URL is configured via Django setting NEXTORA_PRINT_SERVICE_URL
(default: http://127.0.0.1:8989).
"""

import json
import logging
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin

from django.conf import settings

logger = logging.getLogger(__name__)

_PRINT_SERVICE_TIMEOUT = 5  # seconds


@dataclass
class PrintServiceResult:
    """Normalized result from any Print Service API call."""
    success: bool = False
    data: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    error_code: Optional[str] = None
    status_code: int = 0


class PrintServiceClient:
    """Server-side client for the Nextora Print Service REST API.

    All communication is from Django backend → Print Service (not from browser).
    This avoids CORS, mixed-content, and cross-origin security concerns.
    """

    def __init__(self, base_url: Optional[str] = None):
        self.base_url = (base_url or
                         getattr(settings, "NEXTORA_PRINT_SERVICE_URL",
                                 "http://127.0.0.1:8989")).rstrip("/")

    # ── Health / Status ───────────────────────────────────────────────────

    def check_health(self) -> PrintServiceResult:
        """Check if the Print Service is running and responsive."""
        return self._get("/health")

    def get_status(self) -> PrintServiceResult:
        """Get full runtime status of the Print Service."""
        return self._get("/status")

    def get_version(self) -> PrintServiceResult:
        """Get Print Service version info."""
        return self._get("/version")

    # ── Printers ──────────────────────────────────────────────────────────

    def list_printers(
        self,
        *,
        physical_only: bool = True,
        include_virtual: bool = False,
        include_test: bool = False,
        online: Optional[bool] = None,
    ) -> PrintServiceResult:
        """List discovered printers from the Print Service.

        By default returns only physical, non-virtual, non-test printers.
        """
        params: Dict[str, Any] = {
            "physical_only": str(physical_only).lower(),
            "include_virtual": str(include_virtual).lower(),
            "include_test": str(include_test).lower(),
        }
        if online is not None:
            params["online"] = str(online).lower()
        return self._get("/printers", params=params)

    def list_pos_printers(self) -> PrintServiceResult:
        """List printers suitable for POS receipt printing.

        Returns only: physical, discovered, online, non-test printers with
        thermal receipt capability.
        """
        return self._get("/printers/pos")

    def validate_printer(self, printer_name: str) -> PrintServiceResult:
        """Validate a printer's readiness for printing."""
        return self._get("/printers/validate", params={"printer_name": printer_name})

    def get_printer_capabilities(self, printer_name: str) -> PrintServiceResult:
        """Get hardware capabilities of a specific printer."""
        return self._get("/printers/capabilities", params={"printer_name": printer_name})

    # ── Scanning ──────────────────────────────────────────────────────────

    def scan_printers(self) -> PrintServiceResult:
        """Trigger an immediate printer discovery scan."""
        return self._post("/printers/scan")

    # ── Printing ──────────────────────────────────────────────────────────

    def print_receipt(
        self,
        printer_name: str,
        receipt_data: Optional[Dict[str, Any]] = None,
        *,
        html: Optional[str] = None,
        copies: int = 1,
        idempotency_key: str = "",
        dry_run: bool = False,
    ) -> PrintServiceResult:
        """Submit a receipt print job to the Print Service.

        Args:
            printer_name: Target printer name (from Print Service discovery).
            receipt_data: Structured receipt payload (deprecated).
            html: Pre-rendered HTML receipt content.
            copies: Number of copies to print.
            idempotency_key: Unique key for duplicate-print protection.
            dry_run: Preview mode (no hardware output).

        Returns:
            PrintServiceResult with job_id, status, etc.
        """
        payload: Dict[str, Any] = {
            "printer_name": printer_name,
            "copies": copies,
            "idempotency_key": idempotency_key,
            "dry_run": dry_run,
        }
        if html is not None:
            payload["html"] = html
        if receipt_data is not None:
            payload["receipt"] = receipt_data
            
        return self._post("/print", payload=payload)

    def print_diagnostic(
        self,
        printer_name: str,
    ) -> PrintServiceResult:
        """Print a diagnostic/test page to verify printer communication."""
        payload: Dict[str, Any] = {
            "printer_name": printer_name,
            "diagnostic": True,
        }
        return self._post("/print", payload=payload)

    def print_test_page(self, printer_name: str) -> PrintServiceResult:
        """Send a test receipt to validate printer hardware communication."""
        payload: Dict[str, Any] = {
            "printer_name": printer_name,
        }
        return self._post("/print/test", payload=payload)

    # ── Job Management ────────────────────────────────────────────────────

    def get_job_status(self, job_id: str) -> PrintServiceResult:
        """Poll the status of a submitted print job."""
        return self._get(f"/jobs/{job_id}")

    def list_jobs(self) -> PrintServiceResult:
        """List recent print jobs."""
        return self._get("/jobs")

    def cancel_job(self, job_id: str) -> PrintServiceResult:
        """Cancel a pending print job."""
        return self._post("/jobs/cancel", payload={"job_id": job_id})

    # ── Cash Drawer ───────────────────────────────────────────────────────

    def open_cash_drawer(self, printer_name: str, pin: int = 2) -> PrintServiceResult:
        """Send cash drawer kick pulse to the target printer."""
        return self._post("/cash-drawer/open", payload={
            "printer_name": printer_name,
            "pin": pin,
        })

    # ── Printer Settings ──────────────────────────────────────────────────

    def get_default_printer(self) -> PrintServiceResult:
        """Get the Print Service's default printer setting."""
        return self._get("/settings/printer/default")

    def set_default_printer(self, printer_name: str) -> PrintServiceResult:
        """Set the Print Service's default printer."""
        return self._post("/settings/printer/default", payload={
            "default_printer": printer_name,
        })

    # ── Internal HTTP helpers ─────────────────────────────────────────────

    def _get(self, path: str, params: Optional[Dict[str, Any]] = None) -> PrintServiceResult:
        """Perform a GET request against the Print Service."""
        import urllib.request
        import urllib.error
        import urllib.parse

        url = urljoin(self.base_url, path.lstrip("/"))
        if params:
            qs = "&".join(f"{k}={urllib.parse.quote(str(v))}" for k, v in params.items())
            url = f"{url}?{qs}"

        try:
            req = urllib.request.Request(url, method="GET")
            with urllib.request.urlopen(req, timeout=_PRINT_SERVICE_TIMEOUT) as resp:
                body = resp.read().decode("utf-8")
                data = json.loads(body) if body else {}
                return PrintServiceResult(
                    success=True,
                    data=data,
                    status_code=resp.status,
                )
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="replace")
            try:
                data = json.loads(body)
            except (json.JSONDecodeError, ValueError):
                data = {"error": body}
            return PrintServiceResult(
                success=False,
                data=data,
                error=data.get("error", data.get("message", str(e))),
                error_code="HTTP_ERROR",
                status_code=e.code,
            )
        except urllib.error.URLError as e:
            reason = str(e.reason) if hasattr(e, "reason") else str(e)
            return PrintServiceResult(
                success=False,
                error=reason,
                error_code="CONNECTION_ERROR",
            )
        except Exception as e:
            logger.exception("PrintService GET %s failed: %s", path, e)
            return PrintServiceResult(
                success=False,
                error=str(e),
                error_code="UNEXPECTED_ERROR",
            )

    def _post(self, path: str, payload: Optional[Dict[str, Any]] = None) -> PrintServiceResult:
        """Perform a POST request against the Print Service."""
        import urllib.request
        import urllib.error

        url = urljoin(self.base_url, path.lstrip("/"))
        data_bytes = json.dumps(payload or {}).encode("utf-8")

        try:
            req = urllib.request.Request(
                url,
                data=data_bytes,
                method="POST",
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
            )
            with urllib.request.urlopen(req, timeout=_PRINT_SERVICE_TIMEOUT) as resp:
                body = resp.read().decode("utf-8")
                data = json.loads(body) if body else {}
                return PrintServiceResult(
                    success=True,
                    data=data,
                    status_code=resp.status,
                )
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="replace")
            try:
                data = json.loads(body)
            except (json.JSONDecodeError, ValueError):
                data = {"error": body}
            return PrintServiceResult(
                success=False,
                data=data,
                error=data.get("error", data.get("message", str(e))),
                error_code="HTTP_ERROR",
                status_code=e.code,
            )
        except urllib.error.URLError as e:
            reason = str(e.reason) if hasattr(e, "reason") else str(e)
            return PrintServiceResult(
                success=False,
                error=reason,
                error_code="CONNECTION_ERROR",
            )
        except Exception as e:
            logger.exception("PrintService POST %s failed: %s", path, e)
            return PrintServiceResult(
                success=False,
                error=str(e),
                error_code="UNEXPECTED_ERROR",
            )
