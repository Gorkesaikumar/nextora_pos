"""Restaurant aggregate lifecycle service."""
import uuid
from typing import Any, Optional

from django.db import transaction
from django.utils.text import slugify

from contexts.restaurant.domain.enums import BranchStatus, RestaurantStatus
from contexts.restaurant.exceptions import (
    ActivationPrerequisiteFailed,
    InvalidStatusTransition,
    RestaurantNotFound,
)
from contexts.restaurant.models import Restaurant


_VALID_TRANSITIONS = {
    RestaurantStatus.DRAFT: {RestaurantStatus.ACTIVE},
    RestaurantStatus.ACTIVE: {RestaurantStatus.SUSPENDED, RestaurantStatus.CLOSED},
    RestaurantStatus.SUSPENDED: {RestaurantStatus.ACTIVE, RestaurantStatus.CLOSED},
    RestaurantStatus.CLOSED: set(),  # terminal
}


def _validate_transition(current: str, target: str) -> None:
    allowed = _VALID_TRANSITIONS.get(current, set())
    if target not in allowed:
        raise InvalidStatusTransition(
            f"Cannot transition restaurant from '{current}' to '{target}'. "
            f"Allowed: {allowed or 'none (terminal state)'}."
        )


@transaction.atomic
def create_restaurant(
    *,
    tenant_id: uuid.UUID,
    name: str,
    description: str = "",
    is_default: bool = False,
    **address_fields: Any,
) -> Restaurant:
    """Create a new restaurant in DRAFT status."""
    restaurant = Restaurant.objects.create(
        tenant_id=tenant_id,
        name=name,
        slug=slugify(name)[:80],
        description=description,
        status=RestaurantStatus.DRAFT,
        is_default=is_default,
        **address_fields,
    )
    return restaurant


@transaction.atomic
def activate_restaurant(restaurant_id: uuid.UUID) -> Restaurant:
    """
    Activate a restaurant. Requires at least one OPEN branch.
    """
    restaurant = Restaurant.objects.select_for_update().get(id=restaurant_id)
    _validate_transition(restaurant.status, RestaurantStatus.ACTIVE)

    open_branches = restaurant.branches.filter(
        status=BranchStatus.OPEN, is_deleted=False
    ).count()
    if open_branches == 0:
        raise ActivationPrerequisiteFailed(
            "Cannot activate restaurant without at least one OPEN branch."
        )

    restaurant.status = RestaurantStatus.ACTIVE
    restaurant.save(update_fields=["status", "updated_at"])
    return restaurant


@transaction.atomic
def suspend_restaurant(restaurant_id: uuid.UUID) -> Restaurant:
    """Suspend a restaurant. All branches are temporarily closed."""
    restaurant = Restaurant.objects.select_for_update().get(id=restaurant_id)
    _validate_transition(restaurant.status, RestaurantStatus.SUSPENDED)

    # Cascade: temporarily close all open branches.
    restaurant.branches.filter(
        status=BranchStatus.OPEN, is_deleted=False
    ).update(status=BranchStatus.TEMPORARILY_CLOSED)

    restaurant.status = RestaurantStatus.SUSPENDED
    restaurant.save(update_fields=["status", "updated_at"])
    return restaurant


@transaction.atomic
def reactivate_restaurant(restaurant_id: uuid.UUID) -> Restaurant:
    """Reactivate a suspended restaurant."""
    restaurant = Restaurant.objects.select_for_update().get(id=restaurant_id)
    _validate_transition(restaurant.status, RestaurantStatus.ACTIVE)

    restaurant.status = RestaurantStatus.ACTIVE
    restaurant.save(update_fields=["status", "updated_at"])
    return restaurant


@transaction.atomic
def close_restaurant(restaurant_id: uuid.UUID) -> Restaurant:
    """Permanently close a restaurant. Terminal state."""
    restaurant = Restaurant.objects.select_for_update().get(id=restaurant_id)
    _validate_transition(restaurant.status, RestaurantStatus.CLOSED)

    # Ensure no open branches remain.
    active_branches = restaurant.branches.exclude(
        status=BranchStatus.PERMANENTLY_CLOSED
    ).filter(is_deleted=False).count()
    if active_branches > 0:
        raise ActivationPrerequisiteFailed(
            f"Cannot close restaurant: {active_branches} branch(es) are still active. "
            "Close all branches first."
        )

    restaurant.status = RestaurantStatus.CLOSED
    restaurant.save(update_fields=["status", "updated_at"])
    return restaurant


def ensure_default_restaurant(tenant_id: uuid.UUID) -> Restaurant:
    """Ensure a default restaurant exists for a tenant. Idempotent.

    Called during tenant onboarding so single-restaurant tenants
    never need to explicitly create a restaurant.
    """
    restaurant, created = Restaurant.objects.get_or_create(
        tenant_id=tenant_id,
        is_default=True,
        defaults={
            "name": "My Restaurant",
            "slug": "default",
            "status": RestaurantStatus.DRAFT,
        },
    )
    return restaurant
