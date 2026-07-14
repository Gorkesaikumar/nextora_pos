import re

def rewrite():
    path = 'd:/NEXTORA_POS/templates/ordering/partials/invoice_config_preview.html'
    with open(path, 'r', encoding='utf-8') as f:
        html = f.read()

    # Define exact replacements to preserve the Alpine.js directives while adding Django fallback text
    replacements = {
        # HEADER
        'x-text="config.restaurant_name || \'RESTAURANT NAME\'">': 'x-text="config.restaurant_name || \'RESTAURANT NAME\'">{% if not is_preview %}{{ business_name|default:"RESTAURANT NAME" }}{% endif %}',
        'x-text="config.receipt_header || \'TAX INVOICE\'">': 'x-text="config.receipt_header || \'TAX INVOICE\'">{% if not is_preview %}{{ config.receipt_header|default:"TAX INVOICE" }}{% endif %}',
        'x-text="\'GSTIN: \' + config.gstin"': 'x-text="\'GSTIN: \' + config.gstin">{% if not is_preview %}GSTIN: {{ business_gstin }}{% endif %}</span', # span tag fix below
        'x-text="\'FSSAI: \' + config.fssai"': 'x-text="\'FSSAI: \' + config.fssai">{% if not is_preview %}FSSAI: {{ business_fssai }}{% endif %}</span',
        'x-text="config.address"': 'x-text="config.address">{% if not is_preview %}{{ business_address }}{% endif %}</div',
        'x-text="config.phone"': 'x-text="config.phone">{% if not is_preview %}{{ business_phone }}{% endif %}</span',
        'x-text="config.email"': 'x-text="config.email">{% if not is_preview %}{{ config.email }}{% endif %}</span',
        'x-text="config.website"': 'x-text="config.website">{% if not is_preview %}{{ config.website }}{% endif %}</div',
        'x-text="config.custom_header_text"': 'x-text="config.custom_header_text">{% if not is_preview %}{{ custom_header_text }}{% endif %}</div',

        # META
        'x-text="previewData.invoice_number || \'INV-250714-0001\'">': 'x-text="previewData.invoice_number || \'INV-250714-0001\'">{% if not is_preview %}{{ invoice_number }}{% endif %}',
        'x-text="previewData.order_number || \'ORD-250714-0001\'">': 'x-text="previewData.order_number || \'ORD-250714-0001\'">{% if not is_preview %}{{ order_number }}{% endif %}',
        'x-text="previewData.table_number || \'T7\'">': 'x-text="previewData.table_number || \'T7\'">{% if not is_preview %}{{ table_number }}{% endif %}',
        'x-text="previewData.customer_name || \'Rahul Sharma\'">': 'x-text="previewData.customer_name || \'Rahul Sharma\'">{% if not is_preview %}{{ customer_name }}{% endif %}',
        'x-text="previewData.cashier_name || \'Asha Singh\'">': 'x-text="previewData.cashier_name || \'Asha Singh\'">{% if not is_preview %}{{ cashier_name }}{% endif %}',
        'x-text="previewData.order_type || \'DINE-IN\'">': 'x-text="previewData.order_type || \'DINE-IN\'">{% if not is_preview %}{{ order_type }}{% endif %}',
        'x-text="(previewData.date || \'14 Jul 2026\') + \' · \' + (previewData.time || \'14:30\')">': 'x-text="(previewData.date || \'14 Jul 2026\') + \' · \' + (previewData.time || \'14:30\')">{% if not is_preview %}{{ date }} · {{ time }}{% endif %}',

        # ITEMS
        # Wait, the items table is wrapped in a <template x-for="...">
        # We need to prepend a Django {% for item in items %} block if not preview!

        # TOTALS
        'x-text="getCurrency() + parseFloat(previewData.subtotal || 0).toFixed(2)">': 'x-text="getCurrency() + parseFloat(previewData.subtotal || 0).toFixed(2)">{% if not is_preview %}{{ currency_symbol }}{{ subtotal }}{% endif %}',
        'x-text="getCurrency() + parseFloat(previewData.discount_amount || 0).toFixed(2)">': 'x-text="getCurrency() + parseFloat(previewData.discount_amount || 0).toFixed(2)">{% if not is_preview %}{{ currency_symbol }}{{ discount_amount }}{% endif %}',
        'x-text="getCurrency() + parseFloat(previewData.service_charge_amount || 0).toFixed(2)">': 'x-text="getCurrency() + parseFloat(previewData.service_charge_amount || 0).toFixed(2)">{% if not is_preview %}{{ currency_symbol }}{{ service_charge_amount }}{% endif %}',
        'x-text="getCurrency() + parseFloat(previewData.cgst || 0).toFixed(2)">': 'x-text="getCurrency() + parseFloat(previewData.cgst || 0).toFixed(2)">{% if not is_preview %}{{ currency_symbol }}{{ cgst }}{% endif %}',
        'x-text="getCurrency() + parseFloat(previewData.sgst || 0).toFixed(2)">': 'x-text="getCurrency() + parseFloat(previewData.sgst || 0).toFixed(2)">{% if not is_preview %}{{ currency_symbol }}{{ sgst }}{% endif %}',
        'x-text="getCurrency() + parseFloat(previewData.igst || 0).toFixed(2)">': 'x-text="getCurrency() + parseFloat(previewData.igst || 0).toFixed(2)">{% if not is_preview %}{{ currency_symbol }}{{ igst }}{% endif %}',
        'x-text="getCurrency() + parseFloat(previewData.round_off || 0).toFixed(2)">': 'x-text="getCurrency() + parseFloat(previewData.round_off || 0).toFixed(2)">{% if not is_preview %}{{ currency_symbol }}{{ round_off }}{% endif %}',
        'x-text="getCurrency() + parseFloat(previewData.total || 0).toFixed(2)">': 'x-text="getCurrency() + parseFloat(previewData.total || 0).toFixed(2)">{% if not is_preview %}{{ currency_symbol }}{{ total }}{% endif %}',

        # PAYMENT
        'x-text="previewData.payment_method || \'CASH\'">': 'x-text="previewData.payment_method || \'CASH\'">{% if not is_preview %}{{ payment_method }}{% endif %}',
        'x-text="getCurrency() + parseFloat(previewData.amount_paid || 0).toFixed(2)">': 'x-text="getCurrency() + parseFloat(previewData.amount_paid || 0).toFixed(2)">{% if not is_preview %}{{ currency_symbol }}{{ amount_paid }}{% endif %}',
        'x-text="getCurrency() + parseFloat(previewData.change_returned || 0).toFixed(2)">': 'x-text="getCurrency() + parseFloat(previewData.change_returned || 0).toFixed(2)">{% if not is_preview %}{{ currency_symbol }}{{ change_returned }}{% endif %}',
        'x-text="previewData.payment_status || \'PAID\'">': 'x-text="previewData.payment_status || \'PAID\'">{% if not is_preview %}Paid{% endif %}',

        # TAX SUMMARY
        'x-text="getCurrency() + parseFloat(previewData.taxable_amount || 0).toFixed(2)">': 'x-text="getCurrency() + parseFloat(previewData.taxable_amount || 0).toFixed(2)">{% if not is_preview %}{{ currency_symbol }}{{ taxable_amount }}{% endif %}',
        'x-text="getCurrency() + parseFloat(previewData.tax_amount || 0).toFixed(2)">': 'x-text="getCurrency() + parseFloat(previewData.tax_amount || 0).toFixed(2)">{% if not is_preview %}{{ currency_symbol }}{{ tax_amount }}{% endif %}',

        # FOOTER
        'x-text="config.tax_inclusive_message"': 'x-text="config.tax_inclusive_message">{% if not is_preview %}{{ config.tax_inclusive_message }}{% endif %}</div',
        'x-text="config.custom_footer_text"': 'x-text="config.custom_footer_text">{% if not is_preview %}{{ custom_footer_text }}{% endif %}</div',
        'x-text="config.thank_you_message || \'Thank you for your visit!\'">': 'x-text="config.thank_you_message || \'Thank you for your visit!\'">{% if not is_preview %}{{ thank_you_message }}{% endif %}',
        'x-text="config.terms_notes"': 'x-text="config.terms_notes">{% if not is_preview %}{{ config.terms_notes }}{% endif %}</div',
    }

    # Replace x-cloak closing tags correctly
    html = html.replace('x-cloak></span>', 'x-cloak>')
    html = html.replace('x-cloak></div>', 'x-cloak>')

    for old, new in replacements.items():
        if old in html:
            html = html.replace(old, new)
        else:
            print("COULD NOT FIND:", old)

    # Now fix the closing tags that we omitted
    html = html.replace('</span</span>', '</span>')
    html = html.replace('</div</div>', '</div>')

    # Add Django loop for items BEFORE the alpine loop
    django_items = """
        {% if not is_preview %}
          {% for item in items %}
            <tr class="receipt-item-row">
              <td class="receipt-col-desc">
                <span class="receipt-item-name">{{ item.name }}</span>
                {% for mod in item.modifiers %}
                  <span class="receipt-item-modifier">
                    + {{ mod.name }}
                    {% if mod.price_delta and mod.price_delta != '0.00' %}
                      ({{ currency_symbol }}{{ mod.price_delta }})
                    {% endif %}
                  </span>
                {% endfor %}
                {% if item.notes %}
                  <span class="receipt-item-notes">Note: {{ item.notes }}</span>
                {% endif %}
                {% if config.show_item_hsn and item.hsn_code %}
                  <span class="receipt-item-hsn">HSN: {{ item.hsn_code }}</span>
                {% endif %}
                {% if config.show_item_discount and item.line_discount and item.line_discount != '0.00' %}
                  <span class="receipt-item-discount">Disc: -{{ currency_symbol }}{{ item.line_discount }}</span>
                {% endif %}
              </td>
              <td class="receipt-col-qty">{{ item.qty }}</td>
              <td class="receipt-col-rate">{{ currency_symbol }}{{ item.unit_price }}</td>
              <td class="receipt-col-amount">{{ currency_symbol }}{{ item.line_total }}</td>
            </tr>
          {% endfor %}
        {% endif %}
    """
    
    html = html.replace('<tbody>\n        <template x-for="(item, idx) in (previewData.items || [])" :key="idx">', 
                       f'<tbody>\\n{django_items}\\n        <template x-for="(item, idx) in (previewData.items || [])" :key="idx">')
    
    # Hide the template in Django? No, <template> is invisible in the DOM anyway, but Print Service might print it if it parses its inner text!
    # Wait, the Print Service parses HTML to ESC/POS. Does it ignore <template> tags? It might not!
    # If the Print Service sees the x-text bindings, it might print them as empty text anyway, but wait!
    # What if the Print Service just strips tags and prints ALL inner text?
    # If it prints all inner text, the <template> doesn't have any inner text because its spans use `x-text` and have no inner content!
    # So it prints nothing for the template! Excellent!
    # Wait, what about `+ <span x-text="mod.name"></span>`? It has a hardcoded `+ `!
    # It will print `+ `!
    # We should hide the AlpineJS elements from the server entirely using `{% if is_preview %}`!
    
    # Wait, if we wrap the Alpine JS logic in `{% if is_preview %}`, then the Alpine logic IS NEVER rendered by Django when `is_preview=False`.
    # And when `is_preview=True`, we don't render the Django logic!
    # YES! THIS IS THE BEST WAY!

    print("DONE. Writing back...")
    with open('d:/NEXTORA_POS/rewrite.py', 'w') as f:
        pass # just a check
"""

# Wait! The above thought is BRILLIANT!
# If I just wrap the entire AlpineJS section of the HTML in `{% if is_preview %}` and the Django section in `{% else %}`?
# NO, the Dashboard HTML needs BOTH if we want the preview to be live!
# Wait, if `is_preview=True`, it's the dashboard. The dashboard ONLY needs Alpine.
# If `is_preview=False`, it's the Print Service! The Print Service ONLY needs Django variables, NO ALPINE!

def rewrite_v2():
    path = 'd:/NEXTORA_POS/templates/ordering/partials/invoice_config_preview.html'
    with open(path, 'r', encoding='utf-8') as f:
        html = f.read()
    
    # We can just change receipt_data_mapper to render a DIFFERENT template entirely.
    # But wait, the prompt says "My requirement is that the Invoice Configuration Dashboard must become the single source of truth for all printed receipts. Load the saved invoice configuration... The HTML used for the Preview and the HTML sent to the Print Service must be identical."
    
    # If the HTML must be IDENTICAL, I cannot use `{% if is_preview %}` to hide Alpine code from the Print Service, 
    # but maybe the Print Service is smart enough to ignore `<template>` tags?
    
    # Actually, if I just insert the text into the tags, the Print Service will see the text!
    with open(path, 'w', encoding='utf-8') as f:
        f.write(html)
        
rewrite()
