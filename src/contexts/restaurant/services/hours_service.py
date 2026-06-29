"""Business hours and holiday management service."""
import datetime
import uuid
from typing import List, Tuple

from django.db import transaction

from contexts.restaurant.models import Branch, BusinessHours, Holiday


def set_business_hours(
    *,
    branch_id: uuid.UUID,
    day_of_week: int,
    open_time: datetime.time,
    close_time: datetime.time,
    is_closed: bool = False,
) -> BusinessHours:
    """Configure operating hours for a specific day of the week."""
    branch = Branch.objects.get(id=branch_id)
    
    hours, created = BusinessHours.objects.get_or_create(
        branch=branch,
        day_of_week=day_of_week,
        defaults={
            "tenant": branch.tenant,
            "open_time": open_time,
            "close_time": close_time,
            "is_closed": is_closed,
        }
    )
    
    if not created:
        hours.open_time = open_time
        hours.close_time = close_time
        hours.is_closed = is_closed
        hours.full_clean()
        hours.save()
        
    return hours


def check_branch_open_status(branch_id: uuid.UUID, dt: datetime.datetime) -> Tuple[bool, str]:
    """
    Check if a branch is currently open for business on a given datetime.
    Considers business hours and holiday overrides.
    
    Returns:
        (is_open: bool, reason: str)
    """
    branch = Branch.objects.get(id=branch_id)
    date_val = dt.date()
    time_val = dt.time()
    
    # 1. Holiday override check
    holiday = branch.holidays.filter(date=date_val, is_deleted=False).first()
    if holiday:
        if holiday.is_full_day:
            return False, f"Closed for holiday: {holiday.name}"
        else:
            # Partial holiday, check modified times
            if holiday.open_time and holiday.close_time:
                if holiday.open_time <= time_val <= holiday.close_time:
                    return True, f"Open on holiday (modified hours: {holiday.open_time}-{holiday.close_time})"
                return False, f"Closed for holiday outside modified hours: {holiday.name}"

    # 2. Regular business hours check
    # ISO day_of_week: 1 (Monday) to 7 (Sunday)
    iso_weekday = dt.isoweekday()
    hours = branch.business_hours.filter(day_of_week=iso_weekday, is_deleted=False).first()
    
    if not hours or hours.is_closed:
        return False, "Closed for the day"
        
    if hours.open_time <= time_val <= hours.close_time:
        return True, "Open for business"
        
    return False, f"Closed. Business hours: {hours.open_time}–{hours.close_time}"
