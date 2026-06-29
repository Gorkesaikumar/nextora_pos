"""Restaurant domain enumerations."""
from django.db import models


class RestaurantStatus(models.TextChoices):
    DRAFT = "draft", "Draft"
    ACTIVE = "active", "Active"
    SUSPENDED = "suspended", "Suspended"
    CLOSED = "closed", "Closed"


class BranchStatus(models.TextChoices):
    SETUP = "setup", "Setup"
    OPEN = "open", "Open"
    TEMPORARILY_CLOSED = "temporarily_closed", "Temporarily Closed"
    PERMANENTLY_CLOSED = "permanently_closed", "Permanently Closed"


class TableStatus(models.TextChoices):
    VACANT = "vacant", "Vacant"
    OCCUPIED = "occupied", "Occupied"
    RESERVED = "reserved", "Reserved"
    DIRTY = "dirty", "Cleaning"
    BILLING = "billing", "Billing Pending"
    BLOCKED = "blocked", "Blocked"
    MERGED = "merged", "Merged"


class TableShape(models.TextChoices):
    SQUARE = "square", "Square"
    ROUND = "round", "Round"
    RECTANGLE = "rectangle", "Rectangle"
    BAR_SEAT = "bar_seat", "Bar Seat"
    BOOTH = "booth", "Booth"


class PrinterKind(models.TextChoices):
    RECEIPT = "receipt", "Receipt"
    KITCHEN = "kitchen", "Kitchen (KOT)"
    LABEL = "label", "Label"
    KOT = "kot", "Kitchen Order Ticket"


class StationKind(models.TextChoices):
    HOT = "hot", "Hot Kitchen"
    COLD = "cold", "Cold Kitchen"
    GRILL = "grill", "Grill"
    BAR = "bar", "Bar"
    TANDOOR = "tandoor", "Tandoor"
    DESSERT = "dessert", "Dessert"
    PREP = "prep", "Prep Station"
    OTHER = "other", "Other"


class ServiceMode(models.TextChoices):
    DINE_IN = "dine_in", "Dine In"
    TAKEAWAY = "takeaway", "Takeaway"
    DELIVERY = "delivery", "Delivery"
    DRIVE_THROUGH = "drive_through", "Drive Through"


class DayOfWeek(models.IntegerChoices):
    MONDAY = 1, "Monday"
    TUESDAY = 2, "Tuesday"
    WEDNESDAY = 3, "Wednesday"
    THURSDAY = 4, "Thursday"
    FRIDAY = 5, "Friday"
    SATURDAY = 6, "Saturday"
    SUNDAY = 7, "Sunday"


class GSTRegistrationType(models.TextChoices):
    REGULAR = "regular", "Regular"
    COMPOSITION = "composition", "Composition"
    UNREGISTERED = "unregistered", "Unregistered"
