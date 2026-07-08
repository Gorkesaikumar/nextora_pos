/**
 * Nextora POS Enterprise Offline POS Controller (pos-offline.js)
 * Implements Phase 5: Complete Offline Billing, Cart, Barcode Scanning & Settlement
 */

(function (global) {
  'use strict';

  const NextoraOfflinePOS = {
    activeCart: {
      items: [],
      discountAmount: 0.0,
      customer: null
    },

    /**
     * Search products directly from Dexie IndexedDB
     */
    async searchProductsOffline(queryText, categoryId = null) {
      if (!global.NextoraOfflineDB) return [];
      const products = await global.NextoraOfflineDB.products.toArray();
      const q = (queryText || '').toLowerCase().trim();

      return products.filter((p) => {
        if (!p.is_active) return false;
        if (categoryId && p.category_id !== categoryId) return false;
        if (!q) return true;
        return (
          (p.name && p.name.toLowerCase().includes(q)) ||
          (p.sku && p.sku.toLowerCase().includes(q)) ||
          (p.barcode && p.barcode.toLowerCase() === q)
        );
      });
    },

    /**
     * Add product to local offline cart
     */
    async addToCart(product, quantity = 1) {
      const existingIdx = this.activeCart.items.findIndex(i => i.product_id === product.id);
      if (existingIdx >= 0) {
        this.activeCart.items[existingIdx].quantity += quantity;
      } else {
        this.activeCart.items.push({
          product_id: product.id,
          name: product.name,
          sku: product.sku,
          unit_price: parseFloat(product.base_price || 0),
          tax_rate: parseFloat(product.tax_rate || 5.0),
          quantity: quantity
        });
      }
      await this.persistCart();
      return this.computeTotals();
    },

    /**
     * Compute deterministic bill totals matching Python domain calculation
     */
    computeTotals() {
      let subtotal = 0.0;
      let taxTotal = 0.0;

      this.activeCart.items.forEach((item) => {
        const lineTotal = item.unit_price * item.quantity;
        subtotal += lineTotal;
        const lineTax = lineTotal * (item.tax_rate / 100.0);
        taxTotal += lineTax;
      });

      const taxableAmount = Math.max(0, subtotal - (this.activeCart.discountAmount || 0));
      const finalTotal = Math.round((taxableAmount + taxTotal) * 100) / 100;

      return {
        subtotal: subtotal.toFixed(2),
        discount: (this.activeCart.discountAmount || 0).toFixed(2),
        tax_total: taxTotal.toFixed(2),
        grand_total: finalTotal.toFixed(2),
        item_count: this.activeCart.items.reduce((acc, i) => acc + i.quantity, 0)
      };
    },

    /**
     * Persist current cart state in Dexie
     */
    async persistCart() {
      if (!global.NextoraOfflineDB) return;
      await global.NextoraOfflineDB.cart.put({
        id: 'active_cart',
        tenant_id: 'local',
        items: this.activeCart.items,
        discountAmount: this.activeCart.discountAmount,
        updated_at: Date.now()
      });
    },

    /**
     * Execute offline checkout & settlement
     */
    async settleOrderOffline(paymentsArray) {
      if (this.activeCart.items.length === 0) {
        throw new Error('Cannot settle an empty cart.');
      }

      const totals = this.computeTotals();
      const dateStr = new Date().toISOString().slice(0, 10).replace(/-/g, '');
      const randomSeq = Math.floor(1000 + Math.random() * 9000);
      const offlineInvoiceNo = `OFF-${dateStr}-${randomSeq}`;
      const offlineOrderId = 'OFF-ORD-' + Date.now();

      const orderRecord = {
        id: offlineOrderId,
        offline_reference_id: offlineOrderId,
        offline_invoice_no: offlineInvoiceNo,
        items: [...this.activeCart.items],
        subtotal: totals.subtotal,
        tax_total: totals.tax_total,
        grand_total: totals.grand_total,
        payments: paymentsArray,
        status: 'PAID',
        created_at: Date.now()
      };

      if (global.NextoraOfflineDB) {
        // Save local order & payment history
        await global.NextoraOfflineDB.orders.put(orderRecord);
        await global.NextoraOfflineDB.sales.put(orderRecord);

        // Deduct stock in IndexedDB inventory store
        for (const line of this.activeCart.items) {
          const invItems = await global.NextoraOfflineDB.inventory
            .where('product_id')
            .equals(line.product_id);
          if (invItems && invItems.length > 0) {
            const inv = invItems[0];
            inv.qty_available = Math.max(0, (inv.qty_available || 0) - line.quantity);
            await global.NextoraOfflineDB.inventory.put(inv);
          }
        }

        // Queue order mutation for authoritative server sync
        if (global.NextoraOfflineSync) {
          await global.NextoraOfflineSync.enqueueMutation('CREATE_OFFLINE_ORDER', orderRecord);
        }
      }

      // Clear local cart
      this.activeCart.items = [];
      this.activeCart.discountAmount = 0.0;
      await this.persistCart();

      return {
        success: true,
        offline_invoice_no: offlineInvoiceNo,
        order: orderRecord
      };
    }
  };

  global.NextoraOfflinePOS = NextoraOfflinePOS;
})(typeof window !== 'undefined' ? window : this);
