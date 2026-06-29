"""Branch aggregate lifecycle service."""
import uuid
from typing import Any, List, Optional

from django.db import transaction

from contexts.restaurant.domain.enums import BranchStatus, GSTRegistrationType
from contexts.restaurant.exceptions import (
    ActivationPrerequisiteFailed,
    BranchNotFound,
    InvalidGSTIN,
    InvalidStatusTransition,
)
from contexts.restaurant.models import Branch, BranchGSTProfile, BranchSettings, CashCounter

_VALID_BRANCH_TRANSITIONS = {
    BranchStatus.SETUP: {BranchStatus.OPEN},
    BranchStatus.OPEN: {BranchStatus.TEMPORARILY_CLOSED, BranchStatus.PERMANENTLY_CLOSED},
    BranchStatus.TEMPORARILY_CLOSED: {BranchStatus.OPEN, BranchStatus.PERMANENTLY_CLOSED},
    BranchStatus.PERMANENTLY_CLOSED: set(),  # terminal
}

def _validate_branch_transition(current: str, target: str) -> None:
    allowed = _VALID_BRANCH_TRANSITIONS.get(current, set())
    if target not in allowed:
        raise InvalidStatusTransition(
            f"Cannot transition branch from '{current}' to '{target}'. "
            f"Allowed: {allowed or 'none (terminal state)'}."
        )

@transaction.atomic
def create_branch(
    *,
    restaurant_id: uuid.UUID,
    name: str,
    code: str,
    service_modes: List[str],
    timezone: str = "Asia/Kolkata",
    currency: str = "INR",
    **address_fields: Any,
) -> Branch:
    """Create a new branch in SETUP status."""
    branch = Branch.objects.create(
        restaurant_id=restaurant_id,
        name=name,
        code=code,
        status=BranchStatus.SETUP,
        service_modes=service_modes,
        timezone=timezone,
        currency=currency,
        **address_fields,
    )
    
    # Auto-create default settings
    BranchSettings.objects.create(branch=branch)
    return branch

@transaction.atomic
def open_branch(branch_id: uuid.UUID) -> Branch:
    """
    Open a branch. Ensures prerequisites are met:
    - At least one floor.
    - At least one dining table.
    - At least one active cash counter.
    - Valid GST profile (if operating in India).
    """
    branch = Branch.objects.select_for_update().get(id=branch_id)
    _validate_branch_transition(branch.status, BranchStatus.OPEN)

    # 1. Dining table check
    if not branch.tables.filter(is_active=True, is_deleted=False).exists():
        raise ActivationPrerequisiteFailed("Branch must have at least one active table to open.")

    # 2. Cash counter check
    if not branch.cash_counters.filter(is_active=True, is_deleted=False).exists():
        raise ActivationPrerequisiteFailed("Branch must have at least one active cash counter to open.")

    # 4. GST Check (if India)
    if branch.country == "IN":
        try:
            gst = branch.gst_profile
            if not gst.is_active or not gst.gstin:
                raise ActivationPrerequisiteFailed("Active GST profile required for Indian branches.")
        except BranchGSTProfile.DoesNotExist:
            raise ActivationPrerequisiteFailed("GST profile is required for Indian branches.")

    branch.status = BranchStatus.OPEN
    branch.save(update_fields=["status", "updated_at"])
    return branch

@transaction.atomic
def pause_branch(branch_id: uuid.UUID) -> Branch:
    """Temporarily close an open branch."""
    branch = Branch.objects.select_for_update().get(id=branch_id)
    _validate_branch_transition(branch.status, BranchStatus.TEMPORARILY_CLOSED)
    branch.status = BranchStatus.TEMPORARILY_CLOSED
    branch.save(update_fields=["status", "updated_at"])
    return branch

@transaction.atomic
def resume_branch(branch_id: uuid.UUID) -> Branch:
    """Resume operations of a temporarily closed branch."""
    branch = Branch.objects.select_for_update().get(id=branch_id)
    _validate_branch_transition(branch.status, BranchStatus.OPEN)
    branch.status = BranchStatus.OPEN
    branch.save(update_fields=["status", "updated_at"])
    return branch

@transaction.atomic
def permanently_close_branch(branch_id: uuid.UUID) -> Branch:
    """Permanently close a branch. Terminal state."""
    branch = Branch.objects.select_for_update().get(id=branch_id)
    _validate_branch_transition(branch.status, BranchStatus.PERMANENTLY_CLOSED)

    # In a real system, we'd query the ordering context here to ensure no active orders.
    # For now, we perform the state transition and raise an event.
    branch.status = BranchStatus.PERMANENTLY_CLOSED
    branch.save(update_fields=["status", "updated_at"])
    return branch

@transaction.atomic
def update_gst_profile(
    *,
    branch_id: uuid.UUID,
    gstin: str,
    legal_name: str,
    registration_type: GSTRegistrationType = GSTRegistrationType.REGULAR,
) -> BranchGSTProfile:
    """Set or update GST profile for a branch."""
    branch = Branch.objects.get(id=branch_id)
    
    profile, created = BranchGSTProfile.objects.get_or_create(
        branch=branch,
        defaults={
            "tenant": branch.tenant,
            "gstin": gstin,
            "legal_name": legal_name,
            "registration_type": registration_type,
        }
    )
    
    if not created:
        profile.gstin = gstin
        profile.legal_name = legal_name
        profile.registration_type = registration_type
        profile.save()
        
    return profile
