# CLAUDE.md

Private, password-gated wedding website for Kliff & Chao (5 March 2027, Cebu). It is also a learning project and a reusable boilerplate, so code quality and clear explanations matter as much as shipping.

## Where the specs live

| File | Spec for | Wins on |
|---|---|---|
| `docs/BUILD_PLAN.md` | Architecture, data model, repo layout, phases, env vars | Data, RSVP, admin, sync |
| `docs/PLAN.md` | Design, frontend, password gate | Design and the gate |
| `prototype/index.html` | Look-and-feel | Visuals |
| `docs/design/website2.0.pdf` | Current client direction (glass) | Behind the prototype; read it when the prototype is ambiguous |

Work one phase of `docs/BUILD_PLAN.md` at a time. Put new files where its "Repo layout" and "App source" sections say; if something doesn't fit, ask before inventing a folder. If the specs conflict or are silent on something that matters, **stop and ask**. Don't pick one.

## Commands

Set these up in Phase 0 and keep them working:

```bash
npm run dev          # local dev server
npm run build        # production build
npm run lint         # ESLint
npm run typecheck    # tsc --noEmit
npm run test         # Vitest, unit tests
npm run test:db      # Vitest, database integration tests (needs test DB)
npm run format       # Prettier
```

Before saying a task is done, run `lint`, `typecheck` and `test`, and report the results.

## Architecture rules

- **Layering.** Route handlers are thin: check access, validate with zod, call one `lib/` function, map the result to a response. Business logic lives in `lib/`, never in `app/` or components.
- **Components never touch the database.** Only `lib/` imports Prisma. Every module that uses Prisma, secrets or `node:crypto` starts with `import 'server-only'`.
- **Reusability split.** Project-specific things live only in `config/site.ts`, `content/` and `components/site/`. `lib/`, `app/api/`, `app/admin/` and `prisma/` must stay free of wedding-specific names and copy.
- **Pure core, thin edges.** Put decisions (validation rules, matching scores, normalization, party checks, deadline checks) in pure functions that take plain data and return plain data. Keep I/O (Prisma, fetch, cookies) in a thin wrapper that calls them. This is what makes the logic testable.
- **Functions and modules, not classes.** Use React function components and hooks; no class components. In `lib/`, export named functions grouped by domain folder. Use a class only when something genuinely owns long-lived state and a lifecycle, and explain why when you do.
- **One animation engine.** GSAP + ScrollTrigger + Lenis only. Never add Framer Motion/Motion.

## TypeScript

- `strict: true`. No `any`, no `@ts-ignore`, no non-null `!` without a comment saying why it's safe.
- Request and response types are inferred from the zod schemas in `lib/validation.ts` (`z.infer`). Don't hand-write a duplicate type.
- All env access goes through `lib/env.ts`, never `process.env` directly.
- Prefer union types and discriminated unions over boolean flags and optional soup.

## Style

- **Names say what things are.** Functions are verbs (`buildParty`, `verifyPassword`), booleans read as questions (`isEditable`, `hasSubmission`). No abbreviations beyond common ones (`id`, `url`).
- **Small functions, one job each.** If a function needs a comment to explain its sections, split it.
- **No magic values.** Colours, spacing and motion live in the Tailwind theme; copy lives in `content/`; settings in `config/site.ts`; limits and thresholds as named constants.
- **Comments explain why, not what.** Link to the relevant `PLAN.md` section for non-obvious decisions (for example the `sameSite: 'lax'` cookie).
- **Errors are never swallowed.** Return the specific status codes the plans define (`401`, `403 outside_party`, `409`, `429`). Log server errors with context; never send stack traces or internals to the client.
- Match the existing code before inventing a new pattern.

## Security invariants

These are the rules most likely to be broken by accident. Treat any violation as a bug.

- Every gated page layout and every guest API route calls `requireGate()`. Middleware is redirect UX only.
- Every admin route calls `requireAdmin()` (Supabase session **and** email in `ADMIN_EMAILS`).
- The server derives the party from `submittedByGuestId`. Never accept a `partyId` from the client.
- Guest search returns `{ id, displayName }` only. Never party labels, other members or notes.
- Nothing is `NEXT_PUBLIC_` except `NEXT_PUBLIC_SUPABASE_URL` and `NEXT_PUBLIC_SUPABASE_ANON_KEY`.
- Every new table gets RLS enabled in its migration.
- Free text written to Sheets goes through `safeCell`.

## Testing

**Unit tests (Vitest, `npm run test`).** Required for the pure logic, written alongside the code in the same phase, not afterwards. Name them `*.test.ts` next to the file they test. At minimum:

- Password: normalization (`" KliffAndChao "` passes, wrong password fails), hash verification.
- Session: sign/verify round trip, wrong algorithm rejected, bumped `SESSION_EPOCH` rejected.
- `?next=` redirect validation (`/rsvp` allowed; `//evil.com` and `https://…` rejected).
- RSVP rules: guest outside the party → `outside_party`; duplicate guest ids rejected; past deadline → not editable; message over 500 chars rejected.
- Building the `Party` view from current answers and the latest submission.
- `safeCell`: leading `= + - @` escaped, control characters stripped, 500-char cap.
- Scroll maths in `lib/track/`: progress → panel and story index at the phase boundaries (`P1`, `P2`), capsule position, and the coverflow transform/scale/opacity for offsets 0, ±1, ±3 and beyond ±3.
- Search scoring ladder, if any scoring happens in TypeScript.

**Integration tests (`npm run test:db`).** For things that only exist in Postgres, run against a separate test database, never the production one:

- Name search against the misspelling list in `PLAN.md` (`Co`/`Kho`, `Chow`/`Chao`, `See`/`Sy`, `Wy`/`Uy`, `Dee`/`Dy`, `Ong`/`Ang`) and nicknames.
- Idempotency: same `clientSubmissionId` twice → one submission.
- Five concurrent submissions for one household → five submissions, one coherent `GuestRsvp` state.

**Not unit tested:** visuals, animation and audio. Those stay on the manual Verification checklist in `PLAN.md`.

Test behaviour, not implementation. Don't mock the function under test; mock only the edge (database, network).

## Working style

- **Explain as you go.** This is a learning project: say why you chose an approach, and name the concept (for example "server/client boundary", "idempotency key").
- **Ask before adding a dependency.** Say what it's for and what it costs.
- **Stop at the end of each phase.** Report what was built, the checks run and their results, and anything left open. Don't start the next phase unasked.
- **Don't edit `prototype/`.** It's the reference; port from it.
- **Edit files as UTF-8.** Never round-trip files through PowerShell `Get-Content`/`Set-Content` (see `PLAN.md`); keep non-ASCII in JS source as `\uXXXX` escapes.
- **Small commits,** one logical change each, with a message that says what and why.
