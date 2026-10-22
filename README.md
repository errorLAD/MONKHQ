# SOCIALFLOW AI — Next-Gen Social Commerce Platform

**SocialFlow AI** is a production-grade, monolithic Django SaaS platform for Instagram/Facebook comment automation, AI sales agents, unified inbox CRM, creator bio link hubs, digital product delivery, brand marketplace collaborations, and super admin platform control.

---

## Key Features

### 1. Three Separate User Roles & Portals
- **Creator Portal** (`/creator/login/` -> `/creator/dashboard/`): Visual canvas builder, comment-to-DM, historical re-trigger engine, AI sales agent, Link Hub (`/@username`), products & digital downloads, brand deal applications, sales attribution.
- **Brand Portal** (`/brand/login/` -> `/brand/dashboard/`): Promotions marketplace manager, creator discovery, application review, campaign tracking, revenue attribution.
- **Super Admin Platform** (`/admin-platform/login/` -> `/admin-platform/dashboard/`): Global database stats, user ban/unban enforcement with mandatory audit logging, workspace manager, promotion moderation, system health diagnostics, support impersonation sessions.

### 2. Security & Audit Logging
- Server-side role authorization & multi-tenant workspace isolation middleware.
- Security headers middleware (`X-Frame-Options`, `X-Content-Type-Options`, `X-XSS-Protection`).
- Immutable `AuditLog` model recording every admin action, login attempt, ban, and impersonation.

### 3. Meta & Background Processing
- Webhook receiver at `/webhooks/meta/` supporting Meta verification (`hub.verify_token`, `hub.challenge`) and HMAC-SHA256 signature verification.
- Celery & Redis task architecture for async DM queues and re-trigger comment scanning.

---

## Quick Start Guide

### 1. Run Migrations & Seed Real Production Demo Data
```bash
python manage.py makemigrations
python manage.py migrate
python manage.py seed_demo
```

### 2. Default Seeded Credentials
- **Creator**: `alex_creator` / `password123`
- **Brand**: `acme_brand` / `password123`
- **Super Admin**: `admin_platform` / `password123`

### 3. Start Local Server
```bash
python manage.py runserver
```
Visit:
- Creator Dashboard: `http://127.0.0.1:8000/creator/dashboard/`
- Brand Workspace: `http://127.0.0.1:8000/brand/dashboard/`
- Platform Admin: `http://127.0.0.1:8000/admin-platform/dashboard/`
- Public Creator Link Hub: `http://127.0.0.1:8000/linkhub/@alex_creator/`

### 4. Running Automated Tests
```bash
python manage.py test
```
