# Kliff & Chao — Production Build Plan (v2, merged)

This replaces the earlier `BUILD_PLAN.md`. It merges two documents:

- **`PLAN.md`** is the spec for **design, frontend and the password gate**. `prototype/index.html` is the spec for look-and-feel; `docs/design/website2.0.pdf` (glass) is the current client direction behind it.
- **This file** is the spec for **architecture**: Supabase Postgres as the source of truth, Prisma, admin, Sheets sync, launch.

**Precedence rule.** Where the two disagree, the prototype wins on visuals, `PLAN.md` wins on the gate, and this file wins on data, RSVP, admin and sync. Every `PLAN.md` section about the Sheets append-only log, `RSVP_Current` as source of truth, Sheets read caching, and `lib/sheets/guests.ts` is **superseded** here.

---

## Decisions locked

| Topic | Decision |
|---|---|
| Source of truth | **Supabase Postgres** via Prisma. Sheets is an input (guest list) and a mirror (RSVPs). |
| RSVP model | **Household.** One guest answers attending/not attending for each named member of their party, plus one message per party. No plus-one counts, no meal or contact fields. |
| Edits | **Allowed until `RSVP_DEADLINE`**, with the form prefilled from current answers. Read-only after the deadline, enforced server-side (409). |
| Finding yourself | **Shared password + server-side name search** (per `PLAN.md`). No invitation codes. |
| Guest auth | Shared password → `jose` JWT cookie (per `PLAN.md`). |
| Admin auth | Supabase Auth, admin-only. |
| Region | Vercel `sin1` + Supabase **Southeast Asia (Singapore)**. Both must match. |
| Animation | GSAP + ScrollTrigger + Lenis only. No Framer Motion. |
| Visual language | Glass (per `website2.0.pdf`), journey is a coverflow, top chrome is three separate objects. Details in `PLAN.md`. |
| UI kit | shadcn/ui for the RSVP form and admin only. The story panels are custom, ported from the prototype. |

**Dropped from the earlier plan:** `invitationCode`, `maxGuests`, `numberAttending`, `guestNames`, the "already RSVP'd, blocked" screen, `ThemeToggle`, and porting the *old* single-file site.

---

## Stack

Next.js (App Router) + TypeScript · Tailwind CSS v4 · shadcn/ui · Prisma · Supabase Postgres · Supabase Auth (admin) · Zod · React Hook Form · `jose` · `node:crypto` scrypt · GSAP/ScrollTrigger · Lenis · Leaflet + OSM · Resend · Vercel · Cloudflare DNS · `google-auth-library` (Sheets mirror only).

> ⚠️ **Verify versions in Phase 0, don't trust this file.** `PLAN.md` pins Next.js 15; newer majors have shipped, and newer Next.js releases appear to have renamed `middleware.ts` and changed its runtime. Prisma's newer majors also changed how the datasource URL is configured. Have Claude Code read the current docs for both, then either pin deliberately or update the gate and Prisma sections below before writing code.

---

## Reusability split

| Location | Contains | Reusable? |
|---|---|---|
| `config/site.ts` | Couple names, date, venue, deadline display, external links, feature flags | Swap per project |
| `content/` | All copy: chapters and stories, verses, wedding details, motif, entourage, FAQ | Swap per project |
| `components/site/` | The ported prototype design | Swap per project |
| `components/rsvp/`, `components/ui/` | RSVP flow, shadcn | Mostly generic |
| `lib/`, `app/api/`, `app/admin/`, `prisma/` | Gate, DB, search, RSVP, sync, admin | Generic |

---

## Repo layout

This is the single source for folder structure; `PLAN.md` points here. Keep it that way: two trees drift.

```text
kliffandchao/
  CLAUDE.md                 Claude Code reads this automatically; must stay at the root
  README.md                 how to run it, for humans
  docs/
    PLAN.md                 design, frontend, gate
    BUILD_PLAN.md           this file
    design/
      website.pdf           original 7-frame mock
      website2.0.pdf        client review board (glass), current
  prototype/                REFERENCE ONLY: ported from, never built or edited
    index.html
    serve.py
    img/  audio/  video/
  app/  components/  config/  content/  lib/  prisma/  public/
  scripts/
    hash-password.ts        prints SITE_PASSWORD_HASH
    concurrent-rsvp.ts      Phase 3 concurrency check
  .env.example              every variable name, no values; committed
  .env.local  .env.test     real values; gitignored
  vercel.json  next.config.ts  tsconfig.json  vitest.config.ts
  eslint.config.mjs  .prettierrc  package.json  .gitignore
```

Rules that go with it:

- **`prototype/` is excluded** from `tsconfig.json`, ESLint and Prettier, so its single-file code doesn't fail the checks.
- **`.gitignore`** covers `.env*` (except `.env.example`), `prototype/video/intro2.mp4` (the 2 GB source, per `PLAN.md`), and any raw exports.
- **Don't port `prototype/index-timeline.html`.** It's the rejected linear variant; delete it or leave it out of the repo.
- Unit tests sit next to the file they test (`match.ts` → `match.test.ts`); database tests go in `tests/db/`.

## App source

```text
app/
  layout.tsx                      fonts, Lenis provider, AudioProvider + <audio>
  globals.css                     design tokens + glass primitives (.g / .g-l, @supports fallback)
  page.tsx                        password gate (ENTER starts the song)
  (gated)/
    layout.tsx                    await requireGate(); top bar + audio disc
    story/page.tsx                ONE page: <HorizontalTrack> wrapping Intro/Journey/Wedding panels
    rsvp/page.tsx                 full-screen glass overlay route
  admin/
    login/page.tsx                Supabase Auth
    page.tsx                      stats + guest table (auth-gated)
  api/
    gate/route.ts                 POST password → cookie (Node runtime, scrypt)
    guests/search/route.ts        GET ?q= → ≤8 { id, displayName }
    party/route.ts                GET ?guestId= → Party + current answers
    rsvp/route.ts                 POST submission → transaction → fresh Party
    sync/route.ts                 POST Apps Script webhook (shared secret)
    admin/sync/route.ts           POST "Sync now" full pull (Supabase-auth'd)
    health/route.ts               DB reachable?
middleware.ts (or its renamed equivalent)   redirect UX only, NOT the sole check
config/site.ts                    names, date, venue, links (chaodesign URL with UTMs, defined once)
content/
  chapters.ts                     5 chapters, each with its stories (photo, caption, paragraph)
  verses.ts                       5 verses
  wedding.ts                      details + day-of timeline
  motif.ts                        5 groups: palette, attire note, sample tiles
  entourage.ts  faq.ts
components/
  ui/                             shadcn
  site/
    HorizontalTrack.tsx           the one pinned ScrollTrigger; owns progress
    glass/GlassWash.tsx           blurred botanical wash so glass has something to refract
    gate/{GateScreen,Loader,Ambience,Birds}.tsx
    chrome/{TopBar,Wordmark,SectionNav,RsvpPill,AudioToggle,Credit}.tsx
    intro/{IntroPanel,VerseCycler}.tsx
    journey/{JourneyPanel,ChapterStepper,Coverflow,StoryCard,ChapterArrows}.tsx
    journey/useCoverflowGestures.ts   drag + horizontal wheel → jumpTo()
    wedding/{WeddingPanel,TabBar,DetailTab,Countdown,VenueMap,TimelineTab,MotifTab,MotifGroup,EntourageTab,FaqTab}.tsx
  rsvp/{GuestSearch,PartyForm,RsvpBanner,Confirmation}.tsx
lib/
  env.ts                          zod-validated env; fails the build, not a guest
  prisma.ts                       client singleton
  supabase/{server,client}.ts     admin auth helpers
  auth/{password,session,require-gate,require-admin,safe-next}.ts
  search/match.ts                 raw SQL search (pg_trgm + fuzzystrmatch)
  rsvp/{rules,submit,build-party,notify}.ts   rules.ts = pure checks, submit.ts = transaction
  sheets/{client,mirror,escape,retry}.ts
  track/progress.ts               pure: scroll progress → panel, story index, nav capsule position
  track/coverflow.ts              pure: card offset → transform, scale, opacity
  audio/fade.ts
  ambience.ts
  validation.ts                   shared zod schemas
  types.ts
prisma/
  schema.prisma  migrations/  seed.ts  seed-data.csv
public/
  video/  img/  fonts/general-sans/
  (audio: see open items — PLAN.md says the licensed track must not be on a public URL)
tests/db/                         integration tests against the test database
```

`lib/track/` holds the scroll maths from `PLAN.md` ("One pinned ScrollTrigger", the coverflow `paintFlow` numbers) as pure functions, so the components just apply the results and the maths gets unit tests.

---

## Data model

```prisma
enum Side { KLIFF CHAO BOTH }
enum AttendanceStatus { ATTENDING NOT_ATTENDING }

model Party {
  id          String   @id @default(cuid())
  externalId  String   @unique          // party_id from the Guests sheet
  label       String                    // never returned by search
  members     Guest[]
  submissions RsvpSubmission[]
  createdAt   DateTime @default(now())
  updatedAt   DateTime @updatedAt
}

model Guest {
  id           String     @id @default(cuid())   // opaque id sent to the client
  externalId   String     @unique                // guest_id from the sheet — pasted as VALUES
  firstName    String
  lastName     String
  nickname     String?
  side         Side
  notesPrivate String?
  archivedAt   DateTime?                         // soft delete when removed from sheet
  partyId      String
  party        Party      @relation(fields: [partyId], references: [id])
  current      GuestRsvp?
  responses    RsvpResponse[]
  createdAt    DateTime   @default(now())
  updatedAt    DateTime   @updatedAt

  @@index([partyId])
}

// Immutable history: one row per form submit
model RsvpSubmission {
  id                String   @id                 // = clientSubmissionId (idempotency key)
  partyId           String
  party             Party    @relation(fields: [partyId], references: [id])
  submittedByGuestId String
  message           String?  @db.VarChar(500)
  ipHash            String?
  responses         RsvpResponse[]
  createdAt         DateTime @default(now())
}

model RsvpResponse {
  id           String           @id @default(cuid())
  submissionId String
  submission   RsvpSubmission   @relation(fields: [submissionId], references: [id])
  guestId      String
  guest        Guest            @relation(fields: [guestId], references: [id])
  status       AttendanceStatus
  createdAt    DateTime         @default(now())

  @@unique([submissionId, guestId])            // no duplicate guest within one submit
}

// Current state: exactly one row per guest (the DB-level dedupe rule)
model GuestRsvp {
  guestId            String           @id
  guest              Guest            @relation(fields: [guestId], references: [id])
  status             AttendanceStatus
  respondedAt        DateTime
  respondedByGuestId String
  lastSubmissionId   String
}
```

Why two layers: `RsvpSubmission`/`RsvpResponse` keep the full edit history with attribution (the recoverability `PLAN.md` got from its append-only log), and `GuestRsvp` gives one authoritative current answer per guest. Both are written in **one transaction**, so concurrent submits from the same household can't leave them inconsistent. The party message shown in the form is the `message` of the party's most recent submission.

### Supabase security — do this in the first migration

Supabase exposes the `public` schema through its Data API, and the anon key ships to the browser (needed for admin login). **With RLS off, anyone could read the guest list with that key.** Pick one:

- **Enable RLS on every table with no policies** (Prisma connects as the table owner and bypasses RLS; the Data API gets nothing), or
- Put the Prisma tables in a dedicated schema that is not exposed to the Data API.

Add a check to Phase 1's "done when": a request to the Supabase REST endpoint for `Guest` with the anon key returns nothing.

### Connections on Vercel

`DATABASE_URL` = Supabase **pooled** connection (transaction mode) for the app; `DIRECT_URL` = direct connection for migrations. Confirm the exact flags against current Prisma + Supabase docs in Phase 0.

---

## Guest search

Server-side only, as `PLAN.md` requires — never ship the guest list to the client.

Enable the `pg_trgm` and `fuzzystrmatch` extensions in a migration. Search via `$queryRaw` (Prisma can't express these functions) across first name, last name, both name orders and nickname, excluding archived guests. Apply `PLAN.md`'s scoring ladder in SQL: exact 100 → prefix 90 → substring 70 → trigram similarity 65 → `dmetaphone` match 55, threshold 50, top 8.

At ~200 guests a full scan is fine; add a GIN trigram index only if `EXPLAIN` says you need it.

Return `{ id, displayName }` only. Client: debounce 150ms, `AbortController` per keystroke, min 2 chars.

> Test against the real misspellings list before calling this done: `Co`/`Kho`, `Chow`/`Chao`, `See`/`Sy`, `Wy`/`Uy`, `Dee`/`Dy`, `Ong`/`Ang`, plus nicknames. If Postgres `dmetaphone` misses any that the JS `double-metaphone` catches, precompute codes in JS at sync time into a `phoneticCodes String[]` column instead.

---

## RSVP flow

### `GET /api/party?guestId=`

`requireGate()` → load guest (not archived) → return `Party`: members with current `GuestRsvp` state, latest message, `hasSubmission`, `lastRespondedAt`, `editable` (server clock vs `RSVP_DEADLINE`), `deadlineIso`. No `GET /api/parties/:id` — enumeration risk.

### `POST /api/rsvp`

Payload (no `partyId` — the server derives it):

```ts
{
  submittedByGuestId: string;
  responses: { guestId: string; status: 'ATTENDING' | 'NOT_ATTENDING' }[];
  message?: string;              // ≤500
  clientSubmissionId: string;    // uuid per form mount
}
```

Order of checks: `requireGate()` → rate limit (optional) → zod parse → deadline (409) → resolve submitter's party → **reject any `guestId` outside that party (403 `outside_party`)** → reject duplicate guest ids (400) → transaction:

1. Insert `RsvpSubmission` with `id = clientSubmissionId`. On unique violation (Prisma `P2002`) → return `200 { deduped: true, party }`, write nothing else.
2. Insert the `RsvpResponse` rows.
3. Upsert `GuestRsvp` for each responded guest.

After commit, fire-and-forget: **Resend** email to the couple and **Sheets mirror** append. Return the fresh `Party`.

### UI behaviour (from `PLAN.md`)

- Banner when already answered: "We've got your RSVP from {date}. You can update it until {deadline}."
- Every control prefilled; CTA reads "Update our RSVP."
- Per-person attribution: "Answered by Maria on 3 March."
- Read-only after the deadline.
- After submit: **BACK TO HOME** returns to the intro panel.

> ⚠️ Known and accepted for now: anyone with the password who finds a name can change that household's RSVP. History makes every change recoverable. Per-party PINs are the fix if the couple asks.

---

## Google Sheets

Two directions, one service account.

**Sheet → DB (guest list).** The couple edits the `Guests` tab: `guest_id · first_name · last_name · nickname · party_id · party_label · side · notes_private`.

- An installable Apps Script trigger posts changed rows to `/api/sync` with `x-sync-secret`. The route upserts by `externalId`.
- `onEdit` does **not** fire on row deletion. Handle removals in the admin "Sync now" full pull: guests missing from the sheet get `archivedAt` set (never hard-deleted — their RSVP history must survive). An installable `onChange` trigger that calls the full pull is optional.
- Map columns by header name; reject with a specific error if a header is missing.
- 🔴 **Seed `guest_id` and `party_id` as pasted values, never live formulas.** Re-rolled ids orphan every RSVP. Bold this in the couple's instructions.

**DB → Sheet (RSVP mirror).** After each committed submission, append rows to `RSVP_Log` (`values.append`, `valueInputOption=RAW`, `insertDataOption=INSERT_ROWS`), with `PLAN.md`'s `safeCell` escape for CSV injection. Retry 429/5xx only, with backoff. If the mirror fails, log it; the DB is still correct and admin can rebuild the tab. `RSVP_Current` formulas are an optional convenience for the couple.

**GCP setup** follows `PLAN.md`: Sheets API only, service account with no IAM roles, share sheet as Editor, key as `GOOGLE_SA_KEY_B64`. Create it under a **personal Google account**, not a Workspace/work account.

---

## Env vars

```text
# Gate
SITE_PASSWORD_HASH=            # scrypt$..., command in PLAN.md
SESSION_SECRET=                # 32+ random bytes
SESSION_EPOCH=1
# Database
DATABASE_URL=                  # Supabase pooled
DIRECT_URL=                    # Supabase direct, migrations only
# Admin auth
NEXT_PUBLIC_SUPABASE_URL=
NEXT_PUBLIC_SUPABASE_ANON_KEY=
ADMIN_EMAILS=                  # allowlist; Supabase login alone isn't authorization
# Sheets
GOOGLE_SA_KEY_B64=
GOOGLE_SHEET_ID=
SYNC_WEBHOOK_SECRET=
# RSVP
RSVP_DEADLINE=                 # ISO, Asia/Manila-derived — couple to pick
IP_HASH_SALT=
# Email
RESEND_API_KEY=
COUPLE_NOTIFY_EMAIL=
# Optional
UPSTASH_REDIS_REST_URL=
UPSTASH_REDIS_REST_TOKEN=
TURNSTILE_SECRET_KEY=
```

Nothing except the two `NEXT_PUBLIC_SUPABASE_*` values may be `NEXT_PUBLIC_`. The service-role key isn't needed; leave it out.

---

## Phases

Each phase ends deployable to a **Vercel preview**. Keep the prototype live on its current URL until Phase 8.

### Phase 0 — Foundation
- New repo and new Vercel project. `create-next-app` (TS, App Router, Tailwind v4), shadcn/ui, `vercel.json` with `sin1`, `noindex` headers + `robots.txt`, `lib/env.ts`, ESLint + Prettier + Vitest with the npm scripts in `CLAUDE.md`, General Sans via `next/font/local` (Montserrat fallback). Lay out the repo as in "Repo layout" above: `CLAUDE.md` at the root, specs and PDFs in `docs/`, the prototype in `prototype/`. Security headers in `vercel.json` as `PLAN.md` specifies, including `Referrer-Policy: no-referrer`.
- **Done when:** a preview URL renders a placeholder, pushes auto-deploy, response headers show `X-Robots-Tag: noindex, nofollow`, and `lint`, `typecheck` and `test` all run clean.
- **Prompt:** *"Read docs/BUILD_PLAN.md and docs/PLAN.md. We're on Phase 0. First check the current Next.js and Prisma docs and tell me whether anything in the 'Verify versions' note changes the plan — stop and wait for my answer before scaffolding."*

### Phase 1 — Data layer
- Supabase project in Singapore. Prisma init, the schema above, extensions migration (`pg_trgm`, `fuzzystrmatch`), RLS lockdown migration, `seed.ts` from a CSV of ~20 test guests in ~6 households, including the misspelling cases.
- **Done when:** Prisma Studio shows seeded parties and guests, and an anon-key request to Supabase's REST API for guests returns nothing.
- **Prompt:** *"Phase 1. Implement the data model, extensions and RLS lockdown from BUILD_PLAN.md, plus a seed script for prisma/seed-data.csv. Explain the pooled vs direct connection as you go."*

### Phase 2 — Gate backend
- `password.ts` → `session.ts` → `/api/gate` → middleware → `requireGate()` → gated layout, exactly per `PLAN.md` "Password gate". Plain unstyled form for now.
- **Done when:** `PLAN.md` Verification 1–3 pass **on a Vercel preview**, including the `x-middleware-subrequest` curl returning 401.
- **Prompt:** *"Phase 2. Build the gate backend per the Password gate section of PLAN.md. Unstyled form only. Then give me the exact curl commands for Verification 1–3."*

### Phase 3 — RSVP core
- `/api/guests/search`, `/api/party`, `/api/rsvp` with the transaction, idempotency and 403/409 rules. `GuestSearch` → `PartyForm` (React Hook Form + zod, shadcn), prefill, banner, attribution, confirmation. Resend mirror. Sheets mirror can be stubbed until Phase 6.
- **Done when:**
  - The misspelling list resolves correctly.
  - Picking a guest shows their whole household.
  - Submit → re-enter name → **answers prefilled**; edit → history has two submissions, `GuestRsvp` has one row per guest.
  - Foreign `guestId` → 403 `outside_party`.
  - Same `clientSubmissionId` twice → `{ deduped: true }`, one submission row.
  - 5 concurrent submits for one household → 5 submissions, coherent `GuestRsvp`.
  - Past `RSVP_DEADLINE` → read-only form, API 409.
- **Prompt:** *"Phase 3. Implement the RSVP flow in BUILD_PLAN.md. Search uses raw SQL; explain why Prisma can't express it. Write a small script that fires 5 concurrent submissions so I can run the concurrency check."*

### Phase 4 — Frontend port
- Port `prototype/index.html` into `components/site/`, **not** a rebuild from prose. All copy into `content/`, all tokens into `globals.css`/the Tailwind theme. Order:
  1. `HorizontalTrack` + `lib/track/` maths, with `history.scrollRestoration = 'manual'` set before ScrollTrigger measures anything.
  2. Gate UI + `AudioProvider` together (no `<form>` on the gate; birds and ambience).
  3. Glass primitives, the `-webkit-` prefix and the `@supports not` fallback, then the top bar: bare wordmark, section pill with the capsule indicator, separate RSVP pill, audio disc.
  4. Intro + verse (verse bottom-right).
  5. Journey coverflow: chapter stepper, desktop driver, mobile scroll-snap, then drag/wheel gestures through the same `jumpTo()`.
  6. Wedding tabs: details and countdown, day timeline, motif groups (`<details>`), entourage (plain text), FAQ.
  7. RSVP overlay styling and the three chaodesign credits.
- Decide the mobile intro-video option before starting the intro panel.
- **Done when:** `PLAN.md` Verification 4–6 and 13–29 pass, including the **real iPhone** checks for audio and glass.
- **Prompt:** *"Phase 4, step 1. Port the prototype's HorizontalTrack, following docs/PLAN.md. Put the scroll maths in lib/track/ as pure functions with unit tests. Don't add any animation library besides GSAP. Show me how the single onUpdate feeds the coverflow, the chapter stepper and the top-bar capsule."*

### Phase 5 — Admin dashboard
- Supabase Auth login, `/admin` guarded by `require-admin` (session **and** email in `ADMIN_EMAILS`). Counts: invited, households, attending, not attending, pending. Guest table with status and "answered by". Per-household history view.
- **Done when:** a logged-out user and a logged-in non-allowlisted user both get nothing from `/admin` and its data routes.

### Phase 6 — Sheets sync
- Apps Script webhook → `/api/sync` upsert; "Sync now" full pull with archiving; RSVP mirror to `RSVP_Log`.
- **Done when:** editing a row in `Guests` updates the DB within seconds; deleting a row then "Sync now" archives the guest and keeps their history; a submission appears in `RSVP_Log`.

### Phase 7 — Hardening
- Error and empty states: DB unreachable, search no-results, offline submit. Optional Upstash rate limits with `PLAN.md`'s generous tiers; Turnstile on the gate only if abuse appears.
- **Done when:** killing `DATABASE_URL` on a preview shows a friendly error screen, not a stack trace.

### Phase 8 — Launch
- Domain on Cloudflare → Vercel, HTTPS. Real password hash, secrets rotated from dev values. Re-run the full Verification list on production. Then point guests at the new site.
- **Done when:** production passes every check and the prototype URL redirects or is retired.

---

## Open items before or during the build

- **Next.js and Prisma versions** — resolve in Phase 0.
- **RSVP deadline** — needed for Phase 3.
- **Mobile intro video** (poster-only recommended) — needed for Phase 4.
- **Where the song file lives** — `PLAN.md` says it must stay off public URLs, which rules out `public/`. Needed for Phase 4.
- **Music default** on or muted — needed for Phase 4.
- **Domain** — needed for Phase 8.
- Everything in `PLAN.md` "Open items for the couple" still applies, except the Sheets-architecture items superseded above.
