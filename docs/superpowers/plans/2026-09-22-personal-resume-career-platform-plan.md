# Personal Resume Career Platform Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a database-backed personal resume and portfolio platform using Next.js, PostgreSQL, and Prisma, with a secure admin interface for managing profile, experience, skills, projects, education, articles, and contact leads.

**Architecture:** Use a single Next.js application with app-router pages for the public site and a protected admin area for content management. Store all structured career content in PostgreSQL through Prisma, exposing a small server-side data layer that powers both the public pages and the admin CRUD flows. This keeps content centralized, reusable, and easy to extend without a redesign.

**Tech Stack:** Next.js (App Router), TypeScript, Prisma ORM, PostgreSQL, NextAuth or a minimal auth library, Tailwind CSS, Zod validation, ESLint, dotenv, and a small server-side admin interface with secure session auth.

**Spec:** `docs/superpowers/specs/2026-09-15-personal-resume-career-platform-design.md`

## Global Constraints

- v1 must remain focused on core content + admin management; no full SaaS features in the first release.
- Public pages and admin routes must be driven by database content rather than static hard-coded blocks.
- Admin access must use secure authentication and session management.
- Contact submissions must validate and sanitize user input.
- Content must support draft, published, archived, and featured states.
- The design must allow growth into case studies, article publishing, and lead capture without a destructive schema rewrite.
- The initial stack is Next.js + PostgreSQL + Prisma + custom admin.

---

### Task 1: Initialize the app skeleton and project conventions

**Files:**
- Create: `package.json`, `.env.example`, `next.config.mjs`, `tsconfig.json`, `prisma/schema.prisma`, `src/app/**`, `src/lib/**`, `src/components/**`, `src/server/**`, `src/app/admin/**`, `src/app/api/**`, `src/styles/globals.css`
- Create: `prisma/seed.ts`, `eslint.config.mjs`, `postcss.config.mjs`, `tailwind.config.ts`
- Modify: `README.md`

**Interfaces:**
- Consumes: none
- Produces: working Next.js app shell, Prisma config, env template, lint/build scripts, and shared UI conventions for all later tasks

- [ ] **Step 1: Scaffold the Next.js app with TypeScript and app-router conventions**

```bash
npm init -y
npm install next@latest react@latest react-dom@latest
npm install -D typescript @types/node @types/react @types/react-dom eslint eslint-config-next tailwindcss postcss autoprefixer prisma @types/uuid zod
npx prisma init --datasource-provider postgresql
```

- [ ] **Step 2: Configure project defaults and environment template**

```bash
cat > .env.example <<'EOF'
DATABASE_URL="postgresql://postgres:postgres@localhost:5432/career_platform?schema=public"
NEXTAUTH_SECRET="replace-me"
NEXTAUTH_URL="http://localhost:3000"
NEXT_PUBLIC_APP_URL="http://localhost:3000"
EOF
```

- [ ] **Step 3: Add base app layout, CSS reset, and reusable page shell**

Create the app root layout, global CSS, and a small shared layout wrapper for the public site and admin area.

- [ ] **Step 4: Verify the baseline project compiles**

Run:

```bash
npm run lint
npm run build
```

Expected: both commands complete successfully with no configuration errors.

**Done looks like:** A clean baseline app exists, the repo is ready for database and page work, and the default app loads without build errors.

**How to check:** Run `npm run lint` and `npm run build`; success means the project starts from a stable baseline before feature work begins.

---

### Task 2: Define the PostgreSQL schema and Prisma models

**Files:**
- Modify: `prisma/schema.prisma`
- Create: `prisma/seed.ts`
- Create: `src/lib/prisma.ts`
- Create: `src/server/profile.ts`, `src/server/experience.ts`, `src/server/project.ts`, `src/server/article.ts`, `src/server/contact.ts`

**Interfaces:**
- Consumes: app/base setup from Task 1
- Produces: Prisma schema and typed server access helpers for all content entities

- [ ] **Step 1: Write the schema for the core entities**

Model the following in Prisma:
- `Profile`
- `Experience`
- `Skill`
- `Education`
- `Project`
- `CaseStudy`
- `Article`
- `ContactLead`
- `ProjectSkill` or similar join table if many-to-many skill relations are needed

Example excerpt:

```prisma
model Profile {
  id          String      @id @default(cuid())
  fullName    String
  headline    String
  summary     String
  email       String?
  location    String?
  websiteUrl  String?
  linkedinUrl String?
  githubUrl   String?
  portfolioUrl String?
  createdAt   DateTime    @default(now())
  updatedAt   DateTime    @updatedAt
  experiences Experience[]
  education   Education[]
  articles    Article[]
}
```

- [ ] **Step 2: Add enum fields and indexes for publish status, sorting, and timestamps**

Add enums for `ContentStatus`, `SkillCategory`, and `LeadStatus`, plus indexes on `published`, `featured`, `status`, and date fields for public listing queries.

- [ ] **Step 3: Add a seed file with realistic sample resume data**

Seed a single profile, 3–5 experiences, 10–20 skills, 2–3 education entries, 2–4 projects, and one sample contact lead row.

- [ ] **Step 4: Run Prisma generate and migrate**

Run:

```bash
npx prisma generate
npx prisma migrate dev --name init-career-platform
npx prisma db seed
```

Expected: migration succeeds and database contains seeded data.

**Done looks like:** Schema matches the design and is queryable through Prisma; the database can store and retrieve all core content categories from the spec.

**How to check:** Run `npx prisma studio` or use `npx prisma db seed` and query data via Prisma in a Node script to confirm records are inserted and relationships work.

---

### Task 3: Implement authentication and admin access control

**Files:**
- Create: `src/app/admin/login/page.tsx`, `src/app/admin/layout.tsx`, `src/app/admin/page.tsx`, `src/auth.config.ts`, `src/lib/auth.ts`, `src/middleware.ts`, `src/app/api/auth/[...nextauth]/route.ts`
- Modify: `package.json`, `.env.example`

**Interfaces:**
- Consumes: Prisma user/admin model or a minimal `AdminUser` table from the database
- Produces: auth session and protected admin routes for later CRUD tasks

- [ ] **Step 1: Add a minimal admin authentication model**

Use NextAuth with a credentials provider or a GitHub-provider pattern; keep the first implementation simple and secure.

Example model:

```prisma
model AdminUser {
  id       String @id @default(cuid())
  email    String @unique
  password String
  name     String?
  role     String @default("admin")
  createdAt DateTime @default(now())
}
```

- [ ] **Step 2: Protect admin routes and enforce session checks**

Add middleware that redirects unauthenticated users to `/admin/login` and denies access to non-admin sessions.

- [ ] **Step 3: Add a login screen and admin landing page**

Create a simple login form and a dashboard with cards for “Profile”, “Experience”, “Projects”, “Articles”, and “Leads”.

- [ ] **Step 4: Run an auth verification flow**

Test the unauthenticated redirect and successful login flow.

```bash
npm run build
```

**Done looks like:** Only authenticated admins can reach the CMS, while public visitors cannot access internal routes.

**How to check:** Open `/admin` while signed out and confirm redirect; sign in with known credentials and confirm access is granted.

---

### Task 4: Build the public resume and portfolio pages

**Files:**
- Create: `src/app/page.tsx`, `src/app/about/page.tsx`, `src/app/experience/page.tsx`, `src/app/skills/page.tsx`, `src/app/education/page.tsx`, `src/app/projects/page.tsx`, `src/app/projects/[slug]/page.tsx`, `src/app/case-studies/page.tsx`, `src/app/contact/page.tsx`, `src/app/not-found.tsx`
- Create: `src/components/public/**`
- Create: `src/server/public-data.ts`

**Interfaces:**
- Consumes: Prisma models and typed query helpers from Task 2
- Produces: homepage, resume, projects, contact, and about pages rendered from live database data

- [ ] **Step 1: Implement server-side data fetching for homepage and resume sections**

Write a `getPublicProfile` helper that loads the profile, experiences, education, skills, and featured projects.

- [ ] **Step 2: Build the homepage**

The homepage must include a hero, short value proposition, top skills, featured work, and a contact CTA.

- [ ] **Step 3: Build the experience, education, and skills pages**

Render experience entries chronologically, education in a clean list, and skills grouped by category.

- [ ] **Step 4: Build project listing and detail pages**

Support cards on `/projects` and detail routing on `/projects/[slug]`, including status, traits, repo/demo links, and optional case-study linkage.

- [ ] **Step 5: Add a public contact page and inquiry CTA**

The page should render a working contact form that posts to the API route created in Task 6.

- [ ] **Step 6: Verify public-page rendering**

Run:

```bash
npm run build
npm run dev
```

Then open each public route in a browser and confirm the data is live.

**Done looks like:** Public pages render all core content from the database, and the designed sections match the spec’s site structure.

**How to check:** Visit `/`, `/experience`, `/skills`, `/projects`, `/projects/[slug]`, and `/contact`; verify that each page shows unique data loaded from Prisma and not static placeholders.

---

### Task 5: Build the admin content management flows

**Files:**
- Create: `src/app/admin/profile/page.tsx`, `src/app/admin/experience/page.tsx`, `src/app/admin/projects/page.tsx`, `src/app/admin/articles/page.tsx`, `src/app/admin/leads/page.tsx`
- Create: `src/app/api/admin/**` for CRUD endpoints
- Create: `src/components/admin/**`

**Interfaces:**
- Consumes: auth from Task 3 and Prisma models from Task 2
- Produces: content-editing actions for profile, experience, education, skills, projects, articles, and lead review

- [ ] **Step 1: Implement create/read/update/delete flows for profile data**

Add an editable profile form covering name, headline, summary, contact links, and location.

- [ ] **Step 2: Implement experience, education, and skill management**

Add forms for add/edit/delete operations, plus ordering fields and current/featured values.

- [ ] **Step 3: Implement project and article publish management**

Add fields for title, slug, short/long description, status, publication flags, and optional case-study linkage.

- [ ] **Step 4: Implement lead review in the admin dashboard**

Create a list view that shows inbound contact submissions and marks them as new/read/replied.

- [ ] **Step 5: Validate the full admin loop**

Create at least one record in each model using the admin UI and confirm it appears on the public site.

**Done looks like:** An authenticated admin can create, edit, publish, archive, and delete every major content entity without touching code.

**How to check:** Log in as admin, create a new project and experience record, publish it, then confirm the public site shows the new record immediately.

---

### Task 6: Add API endpoints and lead capture validation

**Files:**
- Create: `src/app/api/contact/route.ts`, `src/app/api/admin/profile/route.ts`, `src/app/api/admin/experience/route.ts`, `src/app/api/admin/projects/route.ts`, `src/app/api/admin/articles/route.ts`
- Create: `src/lib/validation.ts`

**Interfaces:**
- Consumes: validated client submissions and admin session cookies
- Produces: safe create/update/delete actions and sanitized contact-lead records

- [ ] **Step 1: Write Zod schemas for all public and admin payloads**

Examples:

```ts
const contactSchema = z.object({
  name: z.string().min(1).max(120),
  email: z.string().email(),
  message: z.string().min(10).max(2000),
});
```

- [ ] **Step 2: Create the public contact endpoint**

Validate input, sanitize strings, store a `ContactLead`, and return a success/failure response without leaking internal errors.

- [ ] **Step 3: Add protected admin API endpoints**

Each CRUD operation must require a valid admin session and validate the payload before modifying the database.

- [ ] **Step 4: Verify failure handling**

Send invalid data and ensure the API returns clean validation errors rather than crashing.

**Done looks like:** Contact forms work, data is validated before persistence, and admin routes are protected from unauthenticated requests.

**How to check:** Submit an invalid form, confirm 400 responses; submit a valid form, confirm a lead is stored; hit a protected endpoint without auth and confirm it rejects access.

---

### Task 7: Add SEO, metadata, performance, and deployment readiness

**Files:**
- Modify: `src/app/layout.tsx`, `src/app/page.tsx`, `src/app/projects/[slug]/page.tsx`, `src/app/contact/page.tsx`
- Create: `src/lib/metadata.ts`, `src/lib/site-config.ts`
- Create: `Dockerfile` or deployment config if required

**Interfaces:**
- Consumes: public data and page metadata
- Produces: SEO metadata, social tags, performance-ready page structure, and deployable config

- [ ] **Step 1: Implement canonical metadata and Open Graph defaults**

Set `title`, `description`, canonical URL, and Open Graph metadata for homepage, project pages, and contact page.

- [ ] **Step 2: Add structured page exports and semantic headings**

Use structured layouts with `h1`, `h2`, and semantic HTML for accessibility and SEO.

- [ ] **Step 3: Add caching and list-query optimizations**

Use `revalidate` or cached fetch patterns for public pages and indexes while keeping admin updates responsive.

- [ ] **Step 4: Build and run production output**

Run:

```bash
npm run build
npm run start
```

Then verify the site and API endpoints respond at production settings.

**Done looks like:** Public pages are indexed and shareable, the site loads cleanly in production mode, and content changes are reflected without major performance problems.

**How to check:** Inspect rendered HTML headers and metadata, run Lighthouse or PageSpeed basics if available, and verify the production build starts successfully.

---

### Task 8: End-to-end validation and launch checklist

**Files:**
- Modify: `README.md`
- Create: `docs/operations/runbook.md` if needed

**Interfaces:**
- Consumes: everything implemented above
- Produces: launch-ready validation and reproducible local setup instructions

- [ ] **Step 1: Validate the core user journeys**

Test all major flows end-to-end:
- visitor can view homepage
- visitor can browse projects and read details
- admin can sign in
- admin can create/edit project and profile
- admin can review contact leads
- contact form stores submissions
- production build succeeds

- [ ] **Step 2: Run full project verification**

Run:

```bash
npm run lint
npm run build
npx prisma validate
```

- [ ] **Step 3: Write final documentation**

Document local setup, environment variables, admin login, seeded data, and deployment steps in `README.md`.

- [ ] **Step 4: Final sanity check**

Confirm the UI quality, content flow, and admin actions align with the spec and user expectations.

**Done looks like:** The app works end-to-end, basic setup is documented, and the project is ready for approval or deployment.

**How to check:** Confirm every acceptance criterion from the spec is covered: public site exists, content is database-driven, admin can update core sections, growth paths remain open, and the app is maintainable.

---

## Implementation Order

1. Initialize app skeleton and project conventions
2. Define Prisma schema and local database setup
3. Secure admin authentication
4. Build public site pages from database records
5. Build admin manage/edit screens and CRUD APIs
6.Add contact validation and lead storage
7. Add SEO/performance and production checks
8. Final launch validation and documentation

## Risks to Watch During Execution

- Overbuilding the app before the content model is stable
- Making the admin interface larger than needed for v1
- Mixing data logic directly into page components instead of using a server layer
- Adding unnecessary features before the core design is proven
- Delaying validation around security and contact input handling

This plan keeps the initial release focused on the spec while preserving extension points for case studies, article publishing, and lead generation.
