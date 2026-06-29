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
