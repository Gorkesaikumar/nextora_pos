"""Onboarding wizard forms — one Django Form per step.

Each step is its own form so server-side validation can produce focused
field-level errors. The view orchestrates them as a single submission and
calls ``RegisterService.provision_workspace`` if all four validate.
"""
from __future__ import annotations

from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.utils.text import slugify

from contexts.billing.domain.enums import BillingInterval
from contexts.billing.models import Plan, SubscriptionCoupon

User = get_user_model()


BUSINESS_TYPES = [
    ("restaurant", "Restaurant"),
    ("cafe", "Cafe"),
    ("bar", "Bar / Pub"),
    ("cloud_kitchen", "Cloud Kitchen"),
    ("qsr", "Quick Service Restaurant"),
    ("bakery", "Bakery"),
    ("food_truck", "Food Truck"),
    ("other", "Other"),
]

COMMON_TIMEZONES = [
    ("Asia/Kolkata", "Asia/Kolkata  (IST, UTC+5:30)"),
    ("Asia/Dubai", "Asia/Dubai  (GST, UTC+4:00)"),
    ("Asia/Singapore", "Asia/Singapore  (SGT, UTC+8:00)"),
    ("Europe/London", "Europe/London  (GMT)"),
    ("America/New_York", "America/New_York  (EST/EDT)"),
    ("Australia/Sydney", "Australia/Sydney  (AEST)"),
    ("UTC", "UTC"),
]

COMMON_CURRENCIES = [
    ("INR", "INR — Indian Rupee"),
    ("USD", "USD — US Dollar"),
    ("AED", "AED — UAE Dirham"),
    ("GBP", "GBP — Pound Sterling"),
    ("EUR", "EUR — Euro"),
    ("SGD", "SGD — Singapore Dollar"),
]

COUNTRIES = [
    ("IN", "India"),
    ("AE", "United Arab Emirates"),
    ("SG", "Singapore"),
    ("GB", "United Kingdom"),
    ("US", "United States"),
    ("AU", "Australia"),
]


class AccountForm(forms.Form):
    """Step 1 — who the operator is."""

    first_name = forms.CharField(max_length=80, strip=True)
    last_name = forms.CharField(max_length=80, strip=True)
    email = forms.EmailField()
    phone = forms.CharField(max_length=24, strip=True)
    password = forms.CharField(min_length=12, max_length=128)
    confirm_password = forms.CharField(min_length=12, max_length=128)

    def clean_email(self) -> str:
        email = self.cleaned_data["email"].lower().strip()
        if User.objects.filter(email__iexact=email).exists():
            raise ValidationError("An account already exists for this email.")
        return email

    def clean(self) -> dict:
        cleaned = super().clean()
        pwd = cleaned.get("password")
        confirm = cleaned.get("confirm_password")
        if pwd and confirm and pwd != confirm:
            self.add_error("confirm_password", "Passwords do not match.")
        if pwd:
            try:
                validate_password(pwd)
            except ValidationError as exc:
                self.add_error("password", exc)
        return cleaned

    @property
    def full_name(self) -> str:
        return f"{self.cleaned_data['first_name']} {self.cleaned_data['last_name']}".strip()


class RestaurantForm(forms.Form):
    """Step 2 — the business identity."""

    restaurant_name = forms.CharField(max_length=255, strip=True)
    business_type = forms.ChoiceField(choices=BUSINESS_TYPES)
    country = forms.ChoiceField(choices=COUNTRIES)
    state = forms.CharField(max_length=80, strip=True)
    city = forms.CharField(max_length=80, strip=True)
    postal_code = forms.CharField(max_length=16, strip=True)

    def clean_restaurant_name(self) -> str:
        name = self.cleaned_data["restaurant_name"].strip()
        # Need at least one slug-safe character for Tenant.slug derivation.
        if not slugify(name):
            raise ValidationError("Restaurant name must contain letters or numbers.")
        return name


class PlanForm(forms.Form):
    """Step 3 — chosen plan + billing interval."""

    plan_code = forms.ChoiceField(choices=[])  # populated in __init__
    interval = forms.ChoiceField(
        choices=[(BillingInterval.MONTHLY.value, "Monthly"), (BillingInterval.YEARLY.value, "Yearly")],
        initial=BillingInterval.MONTHLY.value,
    )
    coupon_code = forms.CharField(max_length=50, required=False, strip=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        active = Plan.objects.filter(is_active=True, is_public=True).order_by("name")
        self.fields["plan_code"].choices = [(p.code, p.name) for p in active]

    def clean_coupon_code(self):
        code = self.cleaned_data.get("coupon_code", "").strip().upper()
        if not code:
            return ""
            
        try:
            coupon = SubscriptionCoupon.objects.get(code=code)
        except SubscriptionCoupon.DoesNotExist:
            raise ValidationError("Invalid coupon code.")
            
        is_valid, msg = coupon.is_valid_now(tenant_status="new")
        if not is_valid:
            raise ValidationError(msg)
            
        # We don't have the chosen plan ID directly here (it's plan_code), but we can validate against plan later.
        return code


class BranchForm(forms.Form):
    """Step 4 — first branch + GSTIN/currency/timezone."""

    branch_name = forms.CharField(max_length=255, strip=True)
    branch_code = forms.CharField(max_length=20, strip=True)
    currency = forms.ChoiceField(choices=COMMON_CURRENCIES, initial="INR")
    timezone = forms.ChoiceField(choices=COMMON_TIMEZONES, initial="Asia/Kolkata")
    gstin = forms.CharField(max_length=15, required=False, strip=True)
    accept_terms = forms.BooleanField(
        required=True,
        error_messages={"required": "You must accept the Terms and Privacy Policy."},
    )

    def clean_branch_code(self) -> str:
        code = self.cleaned_data["branch_code"].upper().strip()
        if not code.isalnum():
            raise ValidationError("Branch code can only contain letters and numbers.")
        return code

    def clean_gstin(self) -> str:
        gstin = (self.cleaned_data.get("gstin") or "").upper().strip()
        if gstin and len(gstin) != 15:
            raise ValidationError("GSTIN must be exactly 15 characters.")
        return gstin
