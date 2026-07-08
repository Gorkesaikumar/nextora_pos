"""Discount and Combo Offer Engine.

Evaluates unassigned cart items against active combo rules.
Handles retrospective application of offers by grouping existing items.
"""
from decimal import Decimal
import uuid
from django.db import transaction
from django.utils import timezone

from contexts.ordering.models import Order, OrderItem, OrderCombo
from contexts.catalog.models import ComboOffer
from contexts.catalog.domain.enums import ComboStatus
from contexts.ordering.domain.enums import ItemStatus, OrderStatus
from contexts.ordering.domain.finance import q
from contexts.ordering.services.order_service import recalculate, _refresh_item_totals
from contexts.ordering.realtime import broadcast_tenant_event

def evaluate_order_combos(order: Order):
    """
    Returns a dict with 'eligible_offers' and 'ineligible_offers'.
    Each is a list of dicts: {"combo": ComboOffer, "savings": Decimal, "reason": str}
    """
    all_combos = ComboOffer.objects.filter(status=ComboStatus.ACTIVE).prefetch_related('groups__items')
    
    # We only care about active items that are not already in a combo
    available_items = list(order.items.filter(status=ItemStatus.ACTIVE, combo__isnull=True))
    
    eligible = []
    ineligible = []
    
    # Pre-calculate cart totals for eligibility checks
    cart_items_count = sum(item.qty for item in available_items)
    # Order subtotal might not include all current uncommitted items if not saved,
    # but for POS it's typically synced. We use the active items to be safe.
    cart_subtotal = sum(item.qty * item.unit_price for item in available_items)
    
    # Helper to check if order has customer with specific criteria
    customer = order.customer if hasattr(order, 'customer') else None
    
    for combo in all_combos:
        if not combo.is_currently_available:
            ineligible.append({"combo": combo, "reason": "Not available at this time"})
            continue
            
        # 1. Minimum Order Value
        if combo.min_order_value > 0 and cart_subtotal < combo.min_order_value:
            shortfall = combo.min_order_value - cart_subtotal
            ineligible.append({"combo": combo, "reason": f"Minimum Order ₹{combo.min_order_value}. Current Order ₹{cart_subtotal}. Spend ₹{shortfall} more to unlock."})
            continue
            
        # 2. Minimum Cart Items
        if combo.min_cart_items > 0 and cart_items_count < combo.min_cart_items:
            shortfall = combo.min_cart_items - cart_items_count
            ineligible.append({"combo": combo, "reason": f"Requires {combo.min_cart_items} items. Current Cart: {cart_items_count} items. Add {shortfall} more."})
            continue
            
        # 3. Customer Eligibility
        if combo.customer_eligibility != "all":
            if not customer:
                ineligible.append({"combo": combo, "reason": "Requires a registered customer."})
                continue
            
            if combo.customer_eligibility == "new":
                # Check if customer has any settled orders
                past_orders = Order.objects.filter(customer_id=customer.id, status=OrderStatus.SETTLED).exists()
                if past_orders:
                    ineligible.append({"combo": combo, "reason": "Valid for new customers only."})
                    continue
            elif combo.customer_eligibility == "returning":
                past_orders = Order.objects.filter(customer_id=customer.id, status=OrderStatus.SETTLED).exists()
                if not past_orders:
                    ineligible.append({"combo": combo, "reason": "Valid for returning customers only."})
                    continue
            elif combo.customer_eligibility == "vip":
                if customer.loyalty_tier != "platinum":
                    ineligible.append({"combo": combo, "reason": "Valid for VIP customers only."})
                    continue
            elif combo.customer_eligibility == "loyalty":
                if customer.loyalty_tier == "bronze": # Assuming anything above bronze is 'Loyalty' member
                    ineligible.append({"combo": combo, "reason": "Valid for Loyalty members only."})
                    continue

        # 4. Usage Limits
        if combo.usage_limit_type != "unlimited" and combo.usage_limit_value > 0:
            if combo.usage_limit_type == "once_per_order":
                # Ensure we don't apply it multiple times in the SAME order
                # This is handled mostly by the Greedy matching algorithm, but if they want strict 1 max
                pass # The greedy matcher will apply it once if we break out early, or we can enforce it.
                # Actually, the user says "Usage Limit", if it's already in the order, we block it.
                if OrderCombo.objects.filter(order=order, combo_offer_id=combo.id).exists():
                     ineligible.append({"combo": combo, "reason": "Offer already applied to this order."})
                     continue
            elif combo.usage_limit_type == "overall":
                if combo.current_uses >= combo.usage_limit_value:
                    ineligible.append({"combo": combo, "reason": "Global offer limit reached."})
                    continue
            elif combo.usage_limit_type == "once_per_customer":
                if not customer:
                    ineligible.append({"combo": combo, "reason": "Requires customer login to verify limit."})
                    continue
                uses = OrderCombo.objects.filter(order__customer_id=customer.id, combo_offer_id=combo.id).count()
                if uses >= combo.usage_limit_value:
                    ineligible.append({"combo": combo, "reason": "You have reached your limit for this offer."})
                    continue
            elif combo.usage_limit_type == "daily":
                today = timezone.localdate()
                uses = OrderCombo.objects.filter(combo_offer_id=combo.id, created_at__date=today).count()
                if uses >= combo.usage_limit_value:
                    ineligible.append({"combo": combo, "reason": "Daily offer limit reached."})
                    continue
            elif combo.usage_limit_type == "monthly":
                today = timezone.localdate()
                uses = OrderCombo.objects.filter(combo_offer_id=combo.id, created_at__year=today.year, created_at__month=today.month).count()
                if uses >= combo.usage_limit_value:
                    ineligible.append({"combo": combo, "reason": "Monthly offer limit reached."})
                    continue
            
        success, savings, _ = _match_combo(combo, available_items)
        if success:
            eligible.append({"combo": combo, "savings": savings, "reason": "Eligible"})
        else:
            ineligible.append({"combo": combo, "reason": "Add required items to qualify"})
            
    return {"eligible_offers": eligible, "ineligible_offers": ineligible}


def _match_combo(combo: ComboOffer, available_items: list[OrderItem]):
    """
    Greedy matching algorithm.
    Tries to satisfy all groups of a combo using the available_items.
    Returns (success, savings, matched_item_refs)
    matched_item_refs = [(order_item, qty_used_for_combo), ...]
    """
    # Clone available quantities so we can decrement as we match
    # Structure: dict[item_id] = qty_available
    item_qtys = {item.id: item.qty for item in available_items}
    item_map = {item.id: item for item in available_items}
    
    matched_refs = []
    total_value = Decimal("0")
    
    groups = combo.groups.all()
    if not groups:
        # Groupless combos apply to the entire cart (all available items)
        for item in available_items:
            matched_refs.append((item, item.qty))
            total_value += (item.unit_price * item.qty)
        
        # Savings calculation for order-level:
        if combo.offer_type == "fixed_price":
            savings = total_value - combo.discount_value
        elif combo.offer_type == "percentage":
            savings = (total_value * combo.discount_value) / Decimal("100")
        else: # flat_discount
            savings = combo.discount_value
            
        savings = max(Decimal("0"), savings)
        return True, savings, matched_refs
        
    for group in groups:
        selections_needed = group.min_selections
        selections_made = 0
        
        valid_product_ids = set(group.items.values_list('product_id', flat=True))
        
        # Find available items that match this group
        for item_id, available_qty in item_qtys.items():
            if selections_made >= selections_needed:
                break
                
            if available_qty <= 0:
                continue
                
            item = item_map[item_id]
            if item.product_id in valid_product_ids:
                # We can use this item!
                qty_to_take = min(available_qty, Decimal(selections_needed - selections_made))
                selections_made += qty_to_take
                item_qtys[item_id] -= qty_to_take
                matched_refs.append((item, qty_to_take))
                
                # The value contributed to the combo is the unit price of the item
                total_value += (item.unit_price * qty_to_take)
                
        if selections_made < selections_needed:
            # Failed to satisfy this group
            return False, Decimal("0"), []
            
    # If we got here, all groups are satisfied!
    # Savings calculation:
    if combo.offer_type == "fixed_price":
        savings = total_value - combo.discount_value
    elif combo.offer_type == "percentage":
        savings = (total_value * combo.discount_value) / Decimal("100")
    else: # flat_discount
        savings = combo.discount_value
        
    savings = max(Decimal("0"), savings) # Cannot have negative savings
    return True, savings, matched_refs


@transaction.atomic
def apply_retrospective_combo(order_id: uuid.UUID, combo_id: uuid.UUID):
    order = Order.objects.select_for_update().get(id=order_id)
    if order.status != OrderStatus.OPEN:
        raise ValueError("Order is not open")
        
    combo = ComboOffer.objects.get(id=combo_id)
    available_items = list(order.items.filter(status=ItemStatus.ACTIVE, combo__isnull=True))
    
    success, savings, matched_refs = _match_combo(combo, available_items)
    if not success:
        raise ValueError("Order does not satisfy combo requirements")
        
    # Create the OrderCombo block
    order_combo = OrderCombo.objects.create(
        order=order,
        combo_offer_id=combo.id,
        name_snapshot=combo.name,
        price=Decimal("0"), # Base price of grouped items
        savings=savings
    )
    
    total_value = sum((item.unit_price * qty) for item, qty in matched_refs)
    order_combo.price = total_value
    order_combo.save(update_fields=['price'])
    
    # Process matched items
    for item, qty_used in matched_refs:
        # If the item's qty exactly matches qty_used, just assign it
        if item.qty == qty_used:
            item.combo = order_combo
            # Calculate proportional discount
            item_value = item.unit_price * item.qty
            if total_value > 0:
                alloc = q(savings * item_value / total_value)
                item.line_discount = alloc
            _refresh_item_totals(item)
            item.save()
        else:
            # We need to split the item!
            # Reduce original item qty (it stays unassigned)
            remaining_qty = item.qty - qty_used
            item.qty = remaining_qty
            # update modifiers total for original
            sum_deltas = sum((m.price_delta for m in item.modifiers.all()), Decimal("0"))
            item.modifiers_total = q(sum_deltas * item.qty)
            _refresh_item_totals(item)
            item.save()
            
            # Create a clone for the combo
            clone = OrderItem.objects.get(id=item.id)
            clone.id = uuid.uuid4()
            clone.qty = qty_used
            clone.combo = order_combo
            # update modifiers total for clone
            clone.modifiers_total = q(sum_deltas * clone.qty)
            
            # proportional discount
            clone_value = clone.unit_price * clone.qty
            if total_value > 0:
                alloc = q(savings * clone_value / total_value)
                clone.line_discount = alloc
                
            _refresh_item_totals(clone)
            clone.save(force_insert=True)
            
            # Clone modifiers
            from contexts.ordering.models import OrderItemModifier
            for mod in item.modifiers.all():
                OrderItemModifier.objects.create(
                    item=clone,
                    modifier_id=mod.modifier_id,
                    name_snapshot=mod.name_snapshot,
                    price_delta=mod.price_delta
                )
                
    recalculate(order)
    transaction.on_commit(lambda: broadcast_tenant_event("order_changed"))
