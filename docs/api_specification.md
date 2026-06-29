# REST API Architecture & OpenAPI Specification

This document defines the standardized REST API specification for Nextora POS, spanning all bounded contexts. It defines the global API conventions (versioning, pagination, filtering, rate limiting, error responses) followed by an endpoint directory and OpenAPI 3.0 specs.

---

## 1. Global API Conventions

### 1.1 Versioning
* All REST APIs are versioned using path-based versioning: `/api/v1/...`
* Breaking changes will increment the version prefix (e.g., `/api/v2/...`).

### 1.2 Tenancy & Authentication
* **Authentication:** Bearer JWT in the `Authorization` header: `Authorization: Bearer <token>`
* **Tenant Isolation:** The tenant is selected using the `X-Tenant-ID` header. The system maps this ID to PostgreSQL Row-Level Security (RLS) contexts:
  `X-Tenant-ID: 7b359f14-cb28-4ef8-8b9a-41e98d1a1b18`

### 1.3 Rate Limiting
Nextora POS implements sliding-window rate limiting in Redis:
* **Public/Auth Endpoints (e.g., `/login`):** 10 requests per minute per IP.
* **Standard Write Endpoints (e.g., `POST /orders`):** 100 requests per minute per IP + Tenant ID.
* **Standard Read Endpoints (e.g., `GET /products`):** 500 requests per minute per IP + Tenant ID.
* **Webhook Endpoints:** 200 requests per minute per provider IP range.

### 1.4 Pagination, Filtering, and Sorting
* **Offset Pagination (Master Data - Products, Customers):**
  - Parameters: `limit` (default: 20, max: 100) and `offset` (default: 0).
  - Response wraps results in a metadata object:
    ```json
    {
      "count": 145,
      "next": "https://nextora.app/api/v1/catalog/products/?limit=20&offset=20",
      "previous": null,
      "results": [...]
    }
    ```
* **Cursor Pagination (Transaction Feeds - Orders, Ledger Movements):**
  - Parameters: `limit` (default: 20) and `cursor` (encoded opaque string).
  - Keeps feed retrieval consistent and safe from pagination drift when new records are written.
* **Filtering & Sorting:**
  - Standardized URL query string keys: e.g., `GET /orders/?status=open&ordering=-opened_at`

### 1.5 RFC 7807 Error Response Schema
All error responses adhere to the RFC 7807 Problem Details standard:
```json
{
  "type": "https://nextora.app/errors/validation-failed",
  "title": "Bad Request",
  "status": 400,
  "detail": "The request payload contains invalid values.",
  "instance": "/api/v1/ordering/orders/",
  "invalid_params": [
    {
      "name": "service_charge_rate",
      "reason": "Ensure this value is less than or equal to 100.00."
    }
  ]
}
```

---

## 2. Bounded Context Endpoint Directory

### 2.1 Catalog Bounded Context
* **`GET /api/v1/catalog/products/`**
  - **Permission:** `catalog.view`
  - **Filters:** `category`, `is_active`, `search` (trigram SKU/name match)
  - **Sort fields:** `sort_order`, `name`, `base_price`
* **`POST /api/v1/catalog/products/`**
  - **Permission:** `catalog.manage`
* **`POST /api/v1/catalog/products/import_csv/`**
  - **Permission:** `catalog.manage`
  - Multi-part file upload carrying products list for bulk ingestion.

### 2.2 Ordering Bounded Context (POS Engine)
* **`POST /api/v1/ordering/orders/`**
  - **Permission:** `ordering.manage`
  - **Request Body:** `{ "location_id": "UUID", "type": "dine_in|takeaway", "table_id": "UUID" }`
* **`POST /api/v1/ordering/orders/{id}/add_item/`**
  - **Permission:** `ordering.manage`
  - **Request Body:** `{ "product_id": "UUID", "qty": 1, "modifiers": ["UUID"] }`
* **`POST /api/v1/ordering/orders/{id}/void_item/`**
  - **Permission:** `ordering.manage`
  - **Request Body:** `{ "item_id": "UUID" }`
* **`POST /api/v1/ordering/orders/{id}/apply_discount/`**
  - **Permission:** `ordering.manage`
  - **Request Body:** `{ "discount_type": "flat|percent", "value": 10.00 }`
* **`POST /api/v1/ordering/orders/{id}/split/`**
  - **Permission:** `ordering.manage`
  - **Request Body:** `{ "moves": [{"item_id": "UUID", "qty": 1.0}] }`
  - **Response:** The newly created split `Order` snapshot.
* **`POST /api/v1/ordering/orders/{id}/merge/`**
  - **Permission:** `ordering.manage`
  - **Request Body:** `{ "source_ids": ["UUID", "UUID"] }`
* **`POST /api/v1/ordering/orders/{id}/pay/`**
  - **Permission:** `ordering.manage`
  - **Request Body:** `{ "amount": 150.00, "method": "cash|card|upi", "tendered": 200.00, "idempotency_key": "string" }`
* **`POST /api/v1/ordering/orders/{id}/refund/`**
  - **Permission:** `ordering.manage`
  - **Request Body:** `{ "amount": 50.00, "method": "cash", "reason": "damaged_goods", "idempotency_key": "string" }`

### 2.3 Billing Bounded Context (SaaS Management)
* **`GET /api/v1/billing/invoices/`**
  - **Permission:** `billing.view`
  - **Filters:** `status`, `financial_year`, `number`
* **`GET /api/v1/billing/subscriptions/`**
  - **Permission:** `billing.view`

### 2.4 Inventory Bounded Context
* **`GET /api/v1/inventory/items/`**
  - **Permission:** `inventory.view`
  - **Filters:** `warehouse_id`, `product_sku`
* **`POST /api/v1/inventory/adjustments/`**
  - **Permission:** `inventory.manage`
  - **Request Body:** `{ "warehouse_id": "UUID", "reason": "reconciliation", "lines": [{"inventory_item_id": "UUID", "quantity_adjusted": 5.00}] }`

---

## 3. OpenAPI 3.0 Specification (YAML Snippet)

```yaml
openapi: 3.0.3
info:
  title: Nextora POS REST API
  description: Versioned, tenant-isolated API-first REST surface for Nextora POS.
  version: 1.0.0
servers:
  - url: /api/v1
paths:
  /ordering/orders/:
    post:
      summary: Create a new Order
      description: Creates an open order ticket at a branch location.
      security:
        - BearerAuth: []
        - TenantHeader: []
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              required:
                - location_id
                - type
              properties:
                location_id:
                  type: string
                  format: uuid
                type:
                  type: string
                  enum: [dine_in, takeaway, delivery]
                table_id:
                  type: string
                  format: uuid
                  nullable: true
                is_interstate:
                  type: boolean
                  default: false
      responses:
        '201':
          description: Order created successfully.
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/Order'
        '400':
          description: Invalid request payload.
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'

  /ordering/orders/{id}/pay/:
    post:
      summary: Add a Payment to an Order
      description: Capture payment against an open order. Fully idempotent via idempotency key.
      parameters:
        - name: id
          in: path
          required: true
          schema:
            type: string
            format: uuid
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              required:
                - amount
                - method
                - idempotency_key
              properties:
                amount:
                  type: number
                  format: decimal
                method:
                  type: string
                  enum: [cash, card, upi]
                tendered:
                  type: number
                  format: decimal
                  nullable: true
                reference:
                  type: string
                idempotency_key:
                  type: string
      responses:
        '201':
          description: Payment captured successfully.
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/Payment'
        '409':
          description: Idempotence conflict.

components:
  securitySchemes:
    BearerAuth:
      type: http
      scheme: bearer
      bearerFormat: JWT
    TenantHeader:
      type: apiKey
      in: header
      name: X-Tenant-ID
  schemas:
    Order:
      type: object
      properties:
        id:
          type: string
          format: uuid
        order_number:
          type: string
        location_id:
          type: string
          format: uuid
        type:
          type: string
        status:
          type: string
        subtotal:
          type: string
          format: decimal
        total:
          type: string
          format: decimal
        paid_amount:
          type: string
          format: decimal
        due_amount:
          type: string
          format: decimal
    Payment:
      type: object
      properties:
        id:
          type: string
          format: uuid
        amount:
          type: string
          format: decimal
        method:
          type: string
        captured_at:
          type: string
          format: date-time
    ErrorResponse:
      type: object
      properties:
        type:
          type: string
        title:
          type: string
        status:
          type: integer
        detail:
          type: string
```
