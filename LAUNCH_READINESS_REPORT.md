# Olid Stores Launch Readiness Report

**Date:** August 28, 2026  
**Assessment conducted by:** Kilo Code (AI assistant)  
**Scope:** Full codebase review for production launch readiness

---

## Part 1: Sample Data / "Populate" Button Investigation

### Location in UI

| Button | Location | Template File |
|--------|----------|---------------|
| "Populate Sample Products" | Admin → Products list | `templates/admin_dashboard/products/product_list.html:792-798` |
| "Remove Sample Products" | Admin → Products list | `templates/admin_dashboard/products/product_list.html:799-805` |
| "Populate Sample Categories" | Admin → Categories list | `templates/admin_dashboard/categories/category_list.html:537-543` |
| "Remove Sample Categories" | Admin → Categories list | `templates/admin_dashboard/categories/category_list.html:544-550` |
| "Generate Sample Data" | Admin → Analytics (empty state + action panel) | `admin_dashboard/templates/admin_dashboard/analytics.html:1824,1874,1953` |

### What Each Does

| Button | View | What It Creates |
|--------|------|-----------------|
| Populate Sample Products | `admin_dashboard/views.py:464-477` | Calls `populate_sample` management command — creates 120 sample products across 9 categories (Electronics, Fashion, Home Appliances, Cosmetics, Books, Sports, Toys, Furniture, Gaming). Marks all with `is_sample=True`. **Deletes all existing products first.** |
| Remove Sample Products | `admin_dashboard/views.py:479-490` | Deletes ALL products from the database. No filter — removes everything. |
| Populate Sample Categories | `admin_dashboard/views.py:655-668` | Same as product populate — calls same `populate_sample` command. |
| Remove Sample Categories | `admin_dashboard/views.py:671-679` | Deletes ALL categories (cascades to products). |
| Generate Sample Data | `admin_dashboard/views.py:1488-1561` | Creates 5 sample customers + 1-4 orders each (20 total orders) with random products, dates spanning last 60 days, weighted status distribution. |

### Intended Use

These are **development/testing tools only**. They are:
- Protected by `@admin_role_required` decorator (only admin users can trigger)
- Located in the admin dashboard (not customer-facing)
- Designed for populating a demo environment

### Production Risk Assessment

**Risk Level: MEDIUM**

While these buttons are admin-only, they pose risks:
1. **No environment gate** — buttons work identically in production and development
2. **Destructive operations** — "Remove Sample Products" deletes ALL products, not just sample ones
3. **No soft-delete** — deletions are permanent
4. **No confirmation beyond JS popup** — a misclick could wipe the product catalog

### Recommendation

**Before launch, either:**
- **Option A (Recommended):** Hide/disable these buttons when `DEBUG=False` by wrapping in `{% if DEBUG %}` blocks in templates
- **Option B:** Add an explicit "production mode" check that returns 404 when `DEBUG=False`
- **Option C:** Remove destructive "Remove" buttons entirely; keep "Populate" for initial setup only

The `generate_sample_data` view should also be gated — it creates fake orders that would pollute real analytics.

---

## Part 2: Full Launch-Readiness Assessment

### Core Commerce

| Area | Rating | Notes |
|------|--------|-------|
| Product catalog | **Ready** | Full CRUD, categories, images, variants, stock tracking. Well-implemented. |
| Search | **Needs work** | Search works but `search_results.html:591,709,719` uses undefined `category` variable instead of `selected_categories` — breaks pagination/sort on search results. |
| Shop filtering | **Ready** | Price range, category, rating, stock status, sorting all functional. |
| Cart | **Needs work** | `cart_update_view` (`orders/views.py:606-608`) allows incrementing beyond stock. No stock validation on increment. |
| Checkout | **Ready** | Supports Paystack, bank transfer, pay-on-delivery. Stock validation, price change warnings, delivery options. |
| Order confirmation | **Ready** | Uses `confirmation_token` for secure public access. Order success page shows full details. |
| Payment (Paystack) | **Ready** | Live keys configured. Webhook handling is robust with HMAC validation, idempotency, API verification. |
| Order management | **Ready** | Admin can view, filter, update status, bulk actions, add tracking numbers, view audit logs. |
| Stock/inventory | **Needs work** | Race condition: checkout pre-check (`orders/views.py:64-82`) runs outside atomic block. TOCTOU vulnerability under concurrent access. Also blocks products with exactly 1 unit from being ordered. |

### Accounts & Security

| Area | Rating | Notes |
|------|--------|-------|
| Username/Olid system | **Ready** | Migration complete. 5 existing users migrated to Olid format. New signups generate correctly. |
| Password reset | **Ready** | Uses security questions (no email). Temporary password displayed on-screen. |
| Account recovery | **Needs work** | Security questions flow works. No rate limiting on `/users/recovery/` — brute-forceable. |
| Security settings | **Needs work** | All production settings correct (HSTS, secure cookies, CSRF). **BUT** `CSRF_TRUSTED_ORIGINS` not set in `render.yaml` — will cause CSRF failures on Render. |
| OTP code | **Ready** | Still actively used for: admin-created customer verification, existing user email verification. Not dead code. Properly secured. |

### Content & Trust

| Area | Rating | Notes |
|------|--------|-------|
| Business content | **Missing** | Bank details, contact info use fallback defaults (`GTBank`, `OD Ltd`, `0123456789`). No real business info configured. |
| Policy pages | **Missing** | Privacy, Terms, Shipping, Returns all populated with boilerplate via migration `core/migrations/0019_populate_default_policy_content.py`. Contains placeholder emails (`support@od.com`, `privacy@e-stores.com`) and placeholder phone numbers. |
| "Olid" branding | **Missing** | 7 SVG logo files still contain "Olid" branding. CSS comments reference "Olid". Promo code defaults to `OLID10`. |
| Placeholder text | **Missing** | Checkout page has pizza placeholder text (`templates/orders/checkout.html:384`). Order success has fallback bank details. |

### Production Readiness

| Area | Rating | Notes |
|------|--------|-------|
| Environment variables | **Missing** | `render.yaml` only sets `DJANGO_DEBUG` and `DJANGO_ALLOWED_HOSTS`. Missing: `DJANGO_SECRET_KEY`, `DATABASE_URL`, `SUPABASE_*`, `PAYSTACK_*`, `REDIS_URL`. |
| Database | **Ready** | PostgreSQL via Supabase with connection pooling. Production-ready. |
| Email delivery | **Ready** | SMTP/Brevo/Resend supported. Configure email backend in Render environment variables. |
| Error handling | **Missing** | 500/404 pages are bare-bones (no branding, no navigation). Order failed page has no error details or next steps. |
| Performance | **Ready** | GZip, WhiteNoise, template caching, database indexes, query optimization. |
| Caching | **Needs work** | No `REDIS_URL` in `render.yaml` — falls back to LocMemCache (not suitable for multi-worker production). |
| Time zone | **Needs work** | Set to UTC (`settings.py:199`). Should be `Africa/Lagos` for Nigerian business. |

### Polish

| Area | Rating | Notes |
|------|--------|-------|
| Mobile responsiveness | **Ready** | Comprehensive responsive CSS with breakpoints at 360px, 390px, 480px, 576px, 768px, 992px, 1200px. |
| Header logo | **Ready** | Handbag icon restored, "Olid Stores" text clean, no overlap. |
| Dark mode | **Ready** | Full dark mode support with toggle, persisted in localStorage. |
| Accessibility | **Ready** | ARIA labels, focus management, keyboard navigation. |
| Live chat | **Ready** | Floating chat widget with auto-reply bot. |

---

## Prioritized Action List

### Must Fix Before Launch

| # | Issue | File(s) | Effort |
|---|-------|---------|--------|
| 1 | **CSRF_TRUSTED_ORIGINS missing** — will break all POST requests on Render | `render.yaml` | Low |
| 2 | **Placeholder pizza text visible to customers** | `templates/orders/checkout.html:384` | Low |
| 3 | **"Olid" branding in 7 SVG files** — customer-facing | `static/images/*.svg` | Medium |
| 4 | **"OD" references in policy templates** | `templates/terms_conditions.html`, `templates/privacy_policy.html` | Low |
| 5 | **Fallback bank details on order success** | `templates/orders/order_success.html:234-238` | Low |
| 6 | **Password reset uses security questions** | `users/views_verification.py:351` | Low |
| 7 | **Sample data buttons work in production** — risk of accidental data loss | `templates/admin_dashboard/products/product_list.html`, `templates/admin_dashboard/categories/category_list.html` | Medium |
| 8 | **Search results pagination broken** | `templates/products/search_results.html:591,709,719` | Low |
| 9 | **Missing environment variables in render.yaml** | `render.yaml` | Medium |
| 10 | **No Redis configured** — LocMemCache not suitable for production | `render.yaml` | Low |

### Can Fix After Launch

| # | Issue | File(s) | Effort |
|---|-------|---------|--------|
| 1 | Cart increment allows exceeding stock | `orders/views.py:606-608` | Low |
| 2 | Checkout stock race condition (TOCTOU) | `orders/views.py:64-82` | Medium |
| 3 | No rate limiting on account recovery | `users/urls.py` | Medium |
| 4 | 500/404 pages need branding | `templates/500.html`, `templates/404.html` | Low |
| 5 | Time zone should be Africa/Lagos | `settings.py:199` | Low |
| 6 | Email sender should use domain address | `.env` / `render.yaml` | Low |
| 7 | Promo code default references OLID10 | `core/models.py:165`, `core/context_processors.py:90` | Low |
| 8 | CSS class `.logo-olid` is misleading | `templates/base.html:329` | Low |
| 9 | Account ID length inconsistency (4-char vs 8-char) | `users/migrations/0015_*.py` | Low |
| 10 | No low-stock alerting mechanism | `products/models.py` | Medium |

---

## Summary

The codebase is **functional and well-architected** but has several **content and configuration gaps** that must be addressed before launch. The core commerce flow (browse → cart → checkout → payment → order confirmation) is solid. Security settings are properly configured for production.

**The main blockers are:**
1. Configuration issues (CSRF_TRUSTED_ORIGINS, missing env vars)
2. Placeholder/legacy content (Olid branding, pizza text, fallback bank details)
3. Sample data tools that could cause accidental data loss in production

**Estimated time to launch-ready:** 4-8 hours of focused work on the "Must Fix" items.
