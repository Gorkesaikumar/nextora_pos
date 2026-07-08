from decimal import Decimal
from django.test import TestCase
from shared.tenancy.context import tenant_context
from contexts.tenants.models import Tenant

from contexts.catalog.domain.enums import ComboOfferType, ComboStatus
from contexts.catalog.models import Product, ComboOffer, TaxClass, Category
from contexts.ordering.models import Order
from contexts.ordering.services import order_service
from contexts.ordering.domain.enums import OrderType, OrderStatus


class ComboMathTestCase(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(name="Test Tenant")
        
        with tenant_context(self.tenant.id):
            self.tax_class = TaxClass.objects.create(
                tenant=self.tenant, name="GST 5%", gst_rate=Decimal("5.00")
            )
            self.category = Category.objects.create(tenant=self.tenant, name="Burgers")

            self.product1 = Product.objects.create(
                tenant=self.tenant, name="Burger", base_price=Decimal("150.00"),
                tax_class=self.tax_class, category=self.category
            )
            self.product2 = Product.objects.create(
                tenant=self.tenant, name="Fries", base_price=Decimal("100.00"),
                tax_class=self.tax_class, category=self.category
            )
            self.product3 = Product.objects.create(
                tenant=self.tenant, name="Cola", base_price=Decimal("50.00"),
                tax_class=self.tax_class, category=self.category
            )
            
            self.combo = ComboOffer.objects.create(
                tenant=self.tenant,
                name="Value Meal",
                status=ComboStatus.ACTIVE,
                offer_type=ComboOfferType.FIXED_PRICE,
                discount_value=Decimal("250.00")  # Savings = 300 - 250 = 50
            )

            self.order = Order.objects.create(
                tenant=self.tenant, type=OrderType.TAKEAWAY, status=OrderStatus.OPEN
            )

    def test_add_combo_proportional_discount(self):
        with tenant_context(self.tenant.id):
            selections = [
                {"product": self.product1, "qty": Decimal("1")},
                {"product": self.product2, "qty": Decimal("1")},
                {"product": self.product3, "qty": Decimal("1")},
            ]
            
            order_combo = order_service.add_combo(self.order.id, self.combo, selections)
            
            self.assertEqual(order_combo.price, Decimal("250.00"))
            self.assertEqual(order_combo.savings, Decimal("50.00"))
            
            burger = self.order.items.get(product_id=self.product1.id)
            fries = self.order.items.get(product_id=self.product2.id)
            cola = self.order.items.get(product_id=self.product3.id)
            
            # 50 * (150/300) = 25.00
            self.assertEqual(burger.line_discount, Decimal("25.00"))
            # 50 * (100/300) = 16.67
            self.assertEqual(fries.line_discount, Decimal("16.67"))
            # 50 - 25.00 - 16.67 = 8.33
            self.assertEqual(cola.line_discount, Decimal("8.33"))
            
            self.order.refresh_from_db()
            self.assertEqual(self.order.subtotal, Decimal("250.00"))
