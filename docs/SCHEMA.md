# SellerPulse Database Schema
## Overview
SellerPulse uses a relational SQLite database with 12 tables. The schema covers seller accounts, listings, orders, order-to-seller participation, order lines, fulfillment, reviews, disputes, commission rules, payouts, payout lines, and lifecycle event history.
The field-level reference is maintained in `data/exports/data_dictionary.json`.
## Primary keys
| Table | Primary key |
|---|---|
| sellers | `id` |
| product_listings | `id` |
| orders | `id` |
| order_sellers | Composite: (`order_id`, `seller_id`) |
| order_lines | `id` |
| fulfillments | `id` |
| customer_reviews | `id` |
| disputes | `id` |
| commission_rules | `id` |
| payouts | `id` |
| payout_lines | `id` |
| entity_events | `id` |
## Foreign keys and relationships
| Source | Foreign key | Target | Relationship / notes |
|---|---|---|---|
| product_listings | `seller_id` | `sellers.id` | Seller 1:N listings |
| orders | `seller_id` | `sellers.id` | Seller 1:N orders; retained as the primary seller association |
| order_sellers | `order_id` | `orders.id` | Order 1:N seller-association rows |
| order_sellers | `seller_id` | `sellers.id` | Seller 1:N seller-association rows |
| order_lines | `order_id` | `orders.id` | Order 1:N order lines |
| order_lines | `listing_id` | `product_listings.id` | Listing 1:N order lines over time |
| fulfillments | `order_id` | `orders.id` | Order 1:N fulfillment records |
| fulfillments | `order_line_id` | `order_lines.id` | Optional order-line association; supports line-level/split fulfillment |
| customer_reviews | `order_id` | `orders.id` | Order 1:N reviews; no unique constraint on `order_id` is declared in the model |
| disputes | `order_id` | `orders.id` | Order 1:N disputes |
| commission_rules | `seller_id` | `sellers.id` | Optional seller scope; NULL means a global rule |
| payouts | `seller_id` | `sellers.id` | Seller 1:N payouts |
| payout_lines | `payout_id` | `payouts.id` | Payout 1:N payout lines |
| payout_lines | `order_id` | `orders.id` | Order can be referenced by payout lines |
| entity_events | None declared | — | Polymorphic `entity_type` + `entity_id`; no conventional FK is declared |
## Cardinality notes
- **Seller ↔ ProductListing:** one seller can own multiple listings.
- **Seller ↔ Order:** `orders.seller_id` records a primary seller association.
- **Order ↔ Seller:** `order_sellers` is a bridge table that supports multiple seller associations for an order. Its composite primary key prevents duplicate pairs. Conceptually, this is many-to-many through the bridge table.
- **Order ↔ OrderLine:** one order can contain multiple lines.
- **OrderLine ↔ ProductListing:** each line references one listing; a listing can appear on multiple order lines.
- **Order ↔ Fulfillment:** an order can have multiple fulfillment records. A fulfillment's `order_line_id` is nullable.
- **Order ↔ Review / Dispute:** both tables reference an order. The models do not declare `order_id` unique in these tables, so a one-to-one constraint should not be assumed.
- **Seller ↔ CommissionRule:** a commission rule may be global (`seller_id` NULL) or seller-specific.
- **Seller ↔ Payout:** a seller can receive multiple payouts.
- **Payout ↔ Order:** `payout_lines` links payout headers to orders. A unique constraint on (`payout_id`, `order_id`) prevents the same order from appearing twice within one payout.
- **EntityEvent:** event history is linked by entity type and identifier in application data rather than a declared FK.
## Declared constraints and business validation
The SQLAlchemy models declare the following checks:
- Customer review rating must be between 1 and 5.
- Dispute amount must be non-negative.
- Commission rate must be between 0 and 1.
- Commission end date cannot precede its start date when both are present.
- Payout total must be non-negative.
- Payout-line gross, commission, dispute deduction, refund, reserve, and net amounts must be non-negative.
- Payout-line (`payout_id`, `order_id`) pairs must be unique.
- Business IDs are unique where declared; several external business IDs are nullable.
Additional application/data-quality checks should verify:
1. Order totals reconcile to their order lines.
2. Fulfillment dates and order-line ownership are consistent.
3. Suspended sellers do not retain active listings.
4. Commission is not applied twice.
5. Eligible resolved disputes are reflected in deductions.
6. Payout timing respects delivery and hold release.
7. Payout totals reconcile to payout-line net amounts.
8. Entity event references and timestamps are plausible.
These business checks should not be confused with database-enforced constraints; their enforcement depends on the application and validation routines.
## Supporting artifacts
- Field definitions and per-field validation notes: `data/exports/data_dictionary.json`
- Dictionary audit: `data/exports/data_dictionary_audit.json`
- Data quality audit: `data/exports/data_quality_audit.json`
- Dataset counts and export checksums: `data/exports/validation_summary.json`
- Dataset provenance and generator metadata: `data/source_manifest.json`
