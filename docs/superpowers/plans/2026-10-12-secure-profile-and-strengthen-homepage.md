# Secure Profile and Strengthen Homepage Implementation Plan

**Goal:** Protect every admin read/write route and make the public career profile's strongest existing evidence easier to find.

**Architecture:** Add one FastAPI HTTP Basic authentication dependency to the existing admin route group. Credentials come from two non-empty environment variables and missing configuration fails closed. Refine the existing Jinja homepage and CSS using current profile records; do not add a data model, dependency, or deployment service.

**Tech Stack:** FastAPI, Python standard library, Jinja2, existing CSS, SQLite (read-only for homepage evidence selection).

**Spec:** User request and approved in-chat scope, 2026-10-12.

## Constraints

- Preserve all existing profile records, SQLite database contents and schema, public routes, responsive behavior, and existing Azure network and HTTPS setup.
- Keep `/admin`, `/admin/profile`, `/admin/add/{entity}`, and `/admin/delete/{entity}/{item_id}` at their current paths; require authentication on every one.
- Validate same-origin `Origin` headers on authenticated admin writes to prevent cross-site form submissions using browser-cached Basic credentials.
- Do not change or deploy remote Azure configuration in this task.
- Do not put credentials in source control. `ADMIN_USERNAME` and `ADMIN_PASSWORD` are necessary application configuration; document them and add blank placeholders to `.env.example`. Empty or missing values must leave admin unavailable, never public.
- Use only existing profile and project fields for homepage claims. Do not hardcode example seed metrics unless the persisted profile data confirms them.
- Make no database writes or schema changes.

## Current Findings

- `main.py` has no authentication middleware or route dependency. `/admin` reads profile data, and its three POST routes mutate profile or career records directly.
- `templates/base.html` shows "Manage content" to every visitor.
- The repository has a SQLite file at `data/career-platform.db`. The local shell has no Python or SQLite CLI, so its live rows could not be queried in this review. `main.py` contains seed examples, including order volume, trainee counts, and a warehouse optimization outcome; these are not assumed to match current persisted data.
- `.env.example` currently documents only `DATA_DIR`. Deployment docs conflict: `README.md` shows `DATA_DIR` inline in the systemd unit, while the newer VM operation plan uses a protected `EnvironmentFile`. The active VM's service config has not been inspected; this plan leaves it untouched.

## Files and Responsibilities

- `main.py`: define fail-closed HTTP Basic auth and apply it to all admin routes without changing route paths or database code.
- `templates/base.html`: remove the public admin link while retaining the brand/home link and footer.
- `templates/home.html`: sharpen the hero with truthful profile-backed language, show existing evidence conditionally, give major sections stable IDs, and add a semantic section index only for sections that have content.
- `static/styles.css`: establish evidence hierarchy and readable section navigation using existing tokens; ensure links wrap at narrow widths, have visible keyboard focus and adequate tap height, and anchor targets are not obscured.
- `.env.example`: document blank `ADMIN_USERNAME` and `ADMIN_PASSWORD` entries without providing usable defaults.
- `README.md`: explain local admin credentials and that a future deployment must add both credential variables to its existing protected service environment source. Do not change the active VM or DNS, HTTPS, Nginx, NSG, or systemd configuration in this task.

## Implementation Sequence

### 1. Protect the existing admin flow

- Use FastAPI's built-in HTTP Basic support; compare both submitted values against non-empty `ADMIN_USERNAME` and `ADMIN_PASSWORD` with constant-time comparison.
- Apply the guard across the entire admin route group so direct POST requests cannot bypass the check.
- For authenticated writes, require an `Origin` matching the request scheme and host; reject missing or cross-origin values with `403` before the handler runs.
- Return a standard `401` Basic challenge for absent or incorrect submitted credentials. If server credentials are unset or blank, fail closed with `503` and a safe configuration message.
- When a future deployment is separately approved, add only `ADMIN_USERNAME` and `ADMIN_PASSWORD` to the environment source the active service already uses; preserve its `DATA_DIR` and all other settings. Without those values, admin remains safely unavailable.
- Keep public `/`, `/static`, admin route names, form destinations, redirects, and SQLite operations unchanged.
- Remove the "Manage content" link from the global public navigation. The authenticated admin page's "View public site" link remains.

### 2. Make the hero specific and evidence-led

- Read the persisted profile, experience achievements, and project outcome before fixing exact copy. Use the local database read-only when an SQLite-capable runtime is available.
- Prefer a concise line along the lines of "Logistics operations experience paired with business analytics," only if the current profile fields support it.
- Promote one existing accomplishment and one existing project result near the hero, conditionally rendered from current records. Do not manufacture totals, savings, impact, or project details; omit a proof item if its record is empty.
- Keep existing profile data intact and avoid repeating a long achievement verbatim in both the hero and its full section.

### 3. Add section navigation and hierarchy

- Add a labeled `<nav>` with native fragment links to populated sections: About, Experience, Education, Projects, Skills, Certifications, and Volunteer Experience.
- Give each section a stable ID and a heading referenced by `aria-labelledby`; omit its nav link when that section has no content.
- Use section-specific eyebrow labels, distinguish the strongest project outcome from routine card metadata, and retain the current green/neutral palette and type family.
- At mobile widths, let the navigation wrap instead of hiding links; preserve visible keyboard focus and comfortable tap targets. Add anchor scroll margin without introducing a sticky overlay or JavaScript dependency.

## Review Focus

- Direct unauthenticated POSTs to all three write paths must receive the same protection as the admin page.
- Cross-origin or origin-less authenticated POSTs must not mutate data; same-origin admin forms must continue to work.
- Missing/blank credential configuration must never allow access and must not expose a traceback or secret.
- Existing routes, record ordering, and all stored fields remain unchanged.
- Hero proof must come from the current database, not only the seed statements in `main.py`.
- Empty profile sections must not produce dead navigation links; the navigation must remain usable at narrow widths and by keyboard.

## Out of Scope

- Deploying code or changing the Azure VM's `.env`, systemd service, Nginx, DNS, HTTPS, firewall, or port configuration.
- Changing the database schema, records, or content through the admin interface.
- Adding a login page, session store, password-reset flow, new dependency, or JavaScript navigation behavior.
- Changing profile sections, resume facts, or claims beyond the requested hero and evidence hierarchy.
