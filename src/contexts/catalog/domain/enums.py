"""Catalog enumerations."""
from django.db import models


class ProductType(models.TextChoices):
    FOOD = "food"
    BEVERAGE = "beverage"
    COMBO = "combo"
    GOODS = "goods"          # packaged retail item
    SERVICE = "service"


class PrinterKind(models.TextChoices):
    RECEIPT = "receipt"
    KITCHEN = "kitchen"
    LABEL = "label"


class ComboStatus(models.TextChoices):
    DRAFT = "draft"
    ACTIVE = "active"
    INACTIVE = "inactive"
    EXPIRED = "expired"


class ComboOfferType(models.TextChoices):
    FIXED_PRICE = "fixed_price"
    BUNDLE = "bundle"
    PERCENTAGE = "percentage"
    FLAT_DISCOUNT = "flat_discount"
    BUY_X_GET_Y = "buy_x_get_y"


class ComboSelectionType(models.TextChoices):
    EXACT = "exact"
    UP_TO = "up_to"
    AT_LEAST = "at_least"


class CustomerEligibility(models.TextChoices):
    ALL = "all", "All Customers"
    NEW = "new", "New Customers Only"
    RETURNING = "returning", "Returning Customers Only"
    VIP = "vip", "VIP Customers"
    LOYALTY = "loyalty", "Loyalty Members"


class UsageLimitType(models.TextChoices):
    UNLIMITED = "unlimited", "Unlimited"
    ONCE_PER_ORDER = "once_per_order", "Once Per Order"
    ONCE_PER_CUSTOMER = "once_per_customer", "Once Per Customer"
    DAILY = "daily", "Daily Limit"
    MONTHLY = "monthly", "Monthly Limit"
    OVERALL = "overall", "Overall Usage Limit"

