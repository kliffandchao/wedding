# Kliff & Chao — Private Wedding Website

> **Read this with `BUILD_PLAN.md`.** This file is the spec for **design, frontend and the password gate**; `prototype/index.html` is the spec for look-and-feel. **`BUILD_PLAN.md` is the spec for architecture**: Supabase Postgres (via Prisma) is the source of truth, Google Sheets is the guest-list input and an RSVP mirror, plus admin, sync, phases and env vars.
>
> Where they disagree: the prototype wins on visuals, this file wins on design and the password gate, `BUILD_PLAN.md` wins on data, RSVP, admin and sync. Sections below that are partly or fully superseded are marked **⚠️ Superseded**.

## Context

A private, password-gated wedding website for Klifford & Charlene, married **March 5, 2027 at Jpark Island Resort, Cebu**. Invited guests enter a shared password, then move through three sections: a video intro, a scroll-driven circular story timeline, and the wedding details. An RSVP flow is backed by Supabase Postgres (guest list maintained in a Google Sheet and synced in), with party-aware group RSVP (one guest can respond for their whole household).

A working static prototype is deployed at kliffandchao.vercel.app. The production build is a new Next.js app, built in the phases in `BUILD_PLAN.md`; the prototype stays live until it reaches parity.

**Source of truth for the design** is `website.pdf` (now at the project root). It has 7 frames on an **854.55 × 468.45** canvas (16:9). I decoded its vector layer, so all geometry below is measured from the file, not guessed. PDF Y is measured from the bottom; I note converted values where useful.

**Decisions already made with the client:**
- Deploy to **Vercel**
- **Supabase Postgres is the source of truth**; Google Sheets (via service account, Sheets API v4) is the guest-list input and an RSVP mirror — see `BUILD_PLAN.md`
- Guests find themselves by **shared password + name search**; no invitation codes
- RSVPs are **editable until the deadline**, prefilled with previous answers
- RSVP captures **attending / not attending per guest + one message per party** (no meal or contact fields)
- **All content is placeholder** for now, centralised so it can be swapped without touching components
- ✅ **Journey uses the circular timeline** (frame 3). Both designs were prototyped and compared; the horizontal/linear alternative from frame 4 was rejected. See "Frame 4" below.
- **The whole site scrolls horizontally** — intro → journey → wedding are panels in one track
- **Day-of timeline is vertical**, in its own nested scroll area with per-stop icons
- **Journey photos are a card stack**, advancing one card per chapter
- Gate shows a **0–100 loading counter** after a correct password
- The **"K & C" text monogram is dropped**; the real wordmark sits top-right, RSVP moves top-left
- Map is **embedded and interactive**, not a link out — Leaflet + OpenStreetMap tiles, no API key
- Intro carries a **click-to-cycle Bible verse** as its own layer over a text-free video

> **Serve the prototype with `prototype/serve.py`, not stock `http.server`.** Python's default handler sends `Last-Modified` and no `Cache-Control`, so browsers heuristically cache HTML and SVG. That produced two convincing phantom bugs during this build — a logo that "wouldn't take `currentColor`" and a map that "still didn't work" — both just stale cached files. The bundled server sends `no-store` and strips `Last-Modified`.

**Working prototype:** `prototype/index.html` — a single self-contained file (CDN Tailwind-free CSS, GSAP, Leaflet) covering all five screens with mock guest data. `prototype/index-timeline.html` is the rejected linear-timeline variant, kept only for comparison.

---

## Tech stack

| Concern | Choice | Why |
|---|---|---|
| Framework | **Next.js, App Router, TypeScript** (version decided in `BUILD_PLAN.md` Phase 0; minimum 15.5.x) | Server routes keep database and service-account credentials off the client; middleware handles gate redirects before any page renders. |
| Styling | **Tailwind CSS v4** | The design is a tight token system (2 fonts, 4 colors). CSS-first `@theme` config suits it. |
| Animation | **GSAP + ScrollTrigger** | The circular timeline is scroll-position-driven rotation — ScrollTrigger's `scrub` is purpose-built for it. Free since 2024. |
| Smooth scroll | **Lenis** | Makes the wheel rotation feel weighted. Integrates with ScrollTrigger via `scrollerProxy`. |
| Background audio | **Plain `<audio>` + React context** | One element in the root layout. No library needed, and nothing else survives route changes as cleanly. |
| Fonts | **General Sans via `next/font/local`**, Montserrat (`next/font/google`) as fallback | General Sans replaced the PDF's Montserrat after the farmminerals.com review — see Typography. Self-hosted, no layout shift. |
| Database | **Supabase Postgres + Prisma** | Source of truth for guests and RSVPs. Details in `BUILD_PLAN.md`. |
| Sheets | **`google-auth-library` + Sheets REST** | For the RSVP mirror and "Sync now" pull only. The `googleapis` monolith is a 100MB+ install covering every Google API and hurts cold starts. |
| Session | **`jose`** (JWT, HS256) | Built on Web Crypto, so it verifies on the Edge runtime where `node:crypto` is unavailable. |
| Password hash | **`node:crypto` scrypt** | Built into Node 24 — no `bcrypt` native build on Windows, nothing in the bundle. |
| Name matching | **Postgres `pg_trgm` + `fuzzystrmatch`** (fallback: `double-metaphone` + `fastest-levenshtein` at sync time) | Phonetic matching is essential here — see the RSVP section for why, `BUILD_PLAN.md` for how. |
| Validation | **`zod`** | Shared request/response schemas between route handlers and forms. |
| Email mirror | **`resend`** | Backup record of every RSVP outside the database. |
| Region | **`sin1`** (Singapore) in `vercel.json` | Default `iad1` costs ~200ms per request from Cebu. |

**One animation engine only.** Do not add Framer Motion/Motion alongside GSAP — two libraries competing for scroll and transform state on the same elements is the most common source of jank in this kind of build.

---

## Design tokens (measured from the PDF)

```
Accent / olive     #2A4300   CMYK(.7 .5 1 .5)  — RSVP pill, ENTER button, nav rule, monogram
Surface / input    #E5E5E5   CMYK(.1 .1 .1 0)  — password field fill
White              #FFFFFF                     — body text on media, the timeline arc
Scrim              rgba(0,0,0,0.40)            — gate background only
Muted              rgba(0,0,0,0.50)            — wedding tab track + inactive tabs
```

Opacities are decoded from the PDF's ExtGState, not estimated. Note that **frames 2 and 3 carry no scrim at all** — the intro video and the journey background are shown at full strength, and the white text sits directly on them. If the client's real video is bright, text legibility will need revisiting.

### Typography & motion — revised after farmminerals.com

The client chose that site as the style reference, which supersedes the PDF's type treatment.

**Typeface: General Sans** (Fontshare, free) as a stand-in for **Aeonik**, which Farm Minerals uses throughout and which is a paid CoType Foundry licence. Switzer or Schibsted Grotesk are alternatives.
> ⚠️ **Self-host it in production** via `next/font/local`. The prototype pulls from the Fontshare CDN; this site has to still work in March 2027 and a third-party font CDN is an avoidable dependency. Montserrat stays in the stack as a fallback.

**Tracking is now a three-token scale**, mirroring theirs — headings go *negative*, positive tracking is reserved for small-caps labels:
```
--ls-display : -.02em   big type: lockup, chapter titles, the date, countdown
--ls-head    : -.01em   mid headings
--ls-label   :  .14em   small caps: nav, tabs, captions, counters
--ls-label-wide: .18em  buttons
```
This is a deliberate break from the PDF, which was uniformly wide (`.2`–`.34em`). Farm Minerals measured `-.01em` (21×), `-.02em` (17×), `-.03em`, with `.08`–`.16em` on labels.

**Motion tokens**, from their CSS: `--dur: .3s` (their house default, 26 declarations) and `--ease-out: cubic-bezier(.16,1,.3,1)`, which they reserve for transforms.

**Lines and radii:** hairlines at 10% / 30% white on dark and `#e7e9e2` on light; radii em-based (`.31`/`.4`/`.63em`, `62.5em` pills) so corners scale with type.

**Warmer surfaces:** page cream `#fbfaf7` → **`#f4ede6`** (their base, 24 uses); photocard stock `#faf6ee`.

> 🔴 **Never bulk-edit this file with PowerShell `Get-Content`/`Set-Content`.** On PS 5.1 that round-trip re-encodes: it mangled 81 em-dashes, added a BOM, and corrupted the `̀-ͯ` escape in the RSVP matcher into literal combining characters — an invalid regex range that throws at *parse time* and silently killed the entire script. Use Python with explicit `encoding="utf-8"`, and keep non-ASCII in JS as `\uXXXX` escapes so no round-trip can reach it.

**Scale conversion.** The canvas is 468.45 units tall, so `1 unit = 0.21347vh`. Every measurement below is given in canvas units; convert with that factor (or `unit / 854.55 * 100` for vw). Build a `u()` helper in the Tailwind theme rather than hardcoding conversions.

---

## The circular timeline — exact geometry

**Confirmed as the journey design** after the client compared working prototypes of both this and the linear alternative.

#### The whole site scrolls horizontally

**All three sections** — intro, journey, wedding — sit side by side in a **300vw** flex track. Vertical scrolling drives the track sideways, pausing in the middle to turn the wheel. One pinned ScrollTrigger owns all three phases:

```
scroll budget = 1 [intro→journey] + (chapters-1) [wheel] + 1 [journey→wedding] = 6 screens
P1 = 1/6   P2 = 5/6   SEG = 100/3   (one panel of a 300vw track)

p ≤ P1      : panel = p/P1            intro slides out
P1 < p ≤ P2 : panel = 1               parked on journey, wheel turns
p > P2      : panel = 1+(p-P2)/(1-P2) wedding slides in
gsap.set('#htrack', { xPercent: -SEG * panel })
```

Verified at 1280px: trackX steps 0 → −1280 → (holds while chapters advance) → −2560.

#### Snap-lock and parallax

**Snap locks the two slide phases only.** `snapTo` is a function that returns a snapped value below `P1` and above `P2`, and returns its input unchanged in between — so you can never rest half-way between panels, but reading through the 19 stories stays free-scrolling. Snapping all 21 stops was considered and rejected: on a trackpad with momentum, every flick yanking to the next story feels like fighting the page.

**Parallax is applied to the FOREGROUND, not the backgrounds.** Each panel's content layer trails its panel by `0.18 × viewport width` during a slide, reaching 0 when the panel is centred.
> The obvious approach — drifting the backgrounds — doesn't work here. They fill their panels exactly, so shifting one exposes a bare edge, and to cover a 30% shift the background would need to be **250% wide**. Widening it would also change the intro video's crop, which is deliberately offset so the groom stays in frame. Moving the foreground faster reads identically and can't leak.

> ⚠️ **Never centre a parallaxed element with `transform: translateX(-50%)`.** GSAP writes `transform` on it, wiping the centring — `.jcontent` jumped to `left: 640px` and ran off the right edge, leaving the journey showing only its arc. Centre with `left:0; right:0; margin:0 auto` instead.

Disable both under `prefers-reduced-motion`: forced scroll positioning is a common accessibility complaint.

> ⚠️ **Pin one element, translate a different one.** Pinning `#htrack` *and* animating its `transform` makes ScrollTrigger's pin and the slide fight over the same property — the track overshot to −1920px instead of −1280px on a 1280px viewport. Wrap it: pin `#hpin`, translate `#htrack` inside it. Verified correct afterwards (0 → −640 → −1280).

Consequences to handle:
- **The nav can no longer use `offsetTop`** for scroll-spy or jumps — the panels are off-screen horizontally, not further down. Drive the active state from the trigger's `onUpdate`, and make nav clicks target scroll *positions* (`hST.start`, `hST.end`).
- ⚠️ **ScrollTrigger calls `onUpdate` during `create()`.** If that callback touches anything declared with `let`/`const` further down the file, you get `Cannot access 'X' before initialization`. Declare shared scroll-spy state with `var` above the trigger, or query the DOM inside the callback.
- **The wedding panel is locked to 100vh** inside the track, with `overflow-y:auto` as a safety. Fitting the DETAIL tab into one screen took real trimming: padding `15vh/16vh → 11vh/13vh`, panel top margin `9vh → 6vh`, countdown margins `4.4/5.4vh → 3.2/3.4vh`, and the map from `44vw @ 2:1` down to `34vw @ 5:2`. Without that the address and directions button sat underneath the fixed bottom nav. **Any new content on this tab has to be budgeted against 100vh.**
- **Mobile journey is its own design, one screen tall.** `#hpin{height:auto;overflow:visible}`, `#htrack{display:block;width:auto}`. Three parts:
  - **The wheel survives, re-proportioned.** A 188vh circle collapses to a vertical line at 375px; instead use a **much larger radius (840px diameter) showing only the top sliver**, with markers ~10° apart. Same arc language, readable on a narrow screen. Marker *labels* are hidden — "FAVOR CONFERENCE" is ~110px wide and the outer markers sit past the screen edge, so they clipped mid-word. The active chapter's title sits below the arc anyway.
  - **Chapters swipe horizontally, one per screen** — `scroll-snap-type: x mandatory` on an `overflow-x:auto` flex row. Native scroll-snap gives you the platform's own momentum and rubber-banding; no gesture code. The arc rotates to bring the active chapter's marker to the apex.
  - **Each chapter holds a tappable photocard stack** — tap to advance the story; copy, counter and dots follow.
  
  Scroll length went **7,502px → 2,777px → exactly one screen.**
- ⚠️ **Don't rAF-throttle the swipe handler.** A `ticking` flag reset inside `requestAnimationFrame` never clears if rAF is throttled (background tab), jamming the handler permanently. Compute the index directly in the scroll listener and early-return when unchanged — the DOM writes then happen once per chapter, not per event.
- **Load the first card of each chapter eagerly** (`fetchpriority`, no `loading="lazy"`). Otherwise swiping to a chapter lands on an empty grey frame while the image fetches.
- **The arc must be full-bleed.** It sat inside `.jcontent`'s 8vw padding and read as a floating curve in mid-air; `width:100vw; left:50%; transform:translateX(-50%)` runs it off both screen edges as intended.
- **Two hints are needed, not one** — "TAP THE PHOTO TO SEE MORE" and "SWIPE FOR THE NEXT CHAPTER". Neither gesture is discoverable on its own.
- **Every mobile section is exactly 100vh and snaps**: `html{scroll-snap-type:y mandatory}` with `scroll-snap-align:start; scroll-snap-stop:always` per section. Without it you could rest half-on-the-journey / half-on-the-wedding page. Sections scroll *internally* rather than growing taller than the viewport, which is what makes mandatory snap safe here — a section taller than the viewport would trap the scroll.
- ⚠️ **Keep the polaroid card styling unscoped (`.card`, not `.deck .card`).** Both the desktop fan and the mobile stack use it; scoping it to the deck left the mobile cards with no frame at all and every caption piled on the same spot.
- **Nav jumps must use `behavior:'auto'`, not `'smooth'`.** A smooth scroll from WEDDING back to INTRO scrubs the entire pinned timeline — you watch every chapter rewind on the way past.
- ⚠️ **Don't latch the mobile check at load.** `matchMedia('(max-width:768px)').matches` returns `true` when the viewport is 0px wide (hidden pane, some embedded webviews), and the mobile branch then permanently replaces the desktop markup — the deck simply vanishes. Guard with `window.innerWidth > 0 &&` and re-evaluate on the media query's `change` event.

This is the signature interaction and the part most likely to be built wrong, so here are the decoded numbers.

Frame 3 contains a single stroked white circle (`lw = 0.4`, 13 path points):

```
center  = (427.3, −64.1)      ← x is exactly page centre (854.55 / 2)
radius  = 441.7
```

The centre sits **below the bottom edge of the viewport**. Converted to CSS:

```
width = height   = 188.58vh        (diameter 883.4)
centre from top  = 113.68vh        (468.45 − (−64.1) = 532.55 units)
arc apex         = 19.39vh from top
left             = 50%,  transform: translate(-50%, -50%)
```

So: a circle nearly twice the viewport height, poking its crown into the top fifth of the screen. On a 16:9 viewport the arc exits the left/right edges at ~82vh down, giving a visible sweep of roughly **±70° around the apex**.

The frame also draws **one marker dot on the arc: `15.3` units across, at `(427.3, 377.5)` — exactly `0°`, dead on the apex.** That confirms the interaction: the active chapter's marker parks at the crown of the wheel, and scrolling rotates the next one up into that slot. Only the active marker is drawn in the mock; the others are either undrawn or rotated off-frame.

**Implementation.** One absolutely-positioned `<div>` with `border-radius: 50%` and a `1px` white border, rotated by GSAP. Chapter markers are absolutely positioned on the rim at `θ = (i − activeIndex) × STEP`, and each marker **counter-rotates by −θ** so its label stays upright. Start with `STEP = 18°` (5 chapters spread across ±36°, comfortably inside the visible sweep) and expose it as a constant to tune. Give the marker at `θ = 0` the filled `15.3`-unit treatment and render the rest smaller/dimmer.

Drive it with a single pinned ScrollTrigger:

```ts
ScrollTrigger.create({
  trigger: sectionRef.current,
  start: 'top top',
  end: () => `+=${(CHAPTERS.length - 1) * window.innerHeight}`,
  pin: true,
  scrub: 1,
  snap: { snapTo: 1 / (CHAPTERS.length - 1), duration: 0.4 },
  onUpdate: (self) => {
    const p = self.progress * (CHAPTERS.length - 1);
    gsap.set(wheelRef.current, { rotation: -p * STEP });
    setActive(Math.round(p));   // drives the heading / body / photo crossfade
  },
});
```

Rotating the **wheel** (not each marker) keeps it to one transform per frame. The `onUpdate` → `setActive` call crosses into React state; throttle it by only calling `setState` when `Math.round(p)` actually changes, or the scrub will re-render on every frame.

**Chapter content** comes from frame 4 (the alternative layout the client rejected — its *content* is what frame 3 should show):

| # | Chapter | Heading shown |
|---|---|---|
| 1 | How we met | `WHERE WE MET` |
| 2 | LDR Vibes | |
| 3 | Favor Conference | |
| 4 | Dates | |
| 5 | WE'RE ENGAGED! | |

Only chapter 1's heading is designed; the rest are placeholder.

**Content layout (revised):** the photo is **centred with the copy beneath it**, not side by side as the PDF frame showed.

#### Chapters contain stories

Each chapter holds **3–5 stories**; a story is one photo + one caption + one paragraph. Nineteen in the placeholder set. **One scroll step = one story = one photocard**, so the scroll budget is `1 + (stories-1) + 1 = 20 screens`.

> ⚠️ **Twenty screens is a long journey.** If it drags, either shorten the per-story scroll distance or cut stories — the constant is `WHEEL_SCREENS = STORIES.length - 1`.

The heading shows `CHAPTER 3 · 2 / 3` so guests know where they are inside a chapter.

**BACK / NEXT step a whole chapter, not a single photo.** Photos are already reachable by scrolling and by clicking cards in the fan, so per-photo arrows were redundant; guests read them as chapter navigation.

**Chapter markers are clickable** — clicking a marker (dot *or* label) jumps to that chapter's first story. They're `role="button"` with `tabindex="0"` and Enter/Space handling.
> The dot is 5px and the label text only ~10px tall. Both need enlarged hit areas — a 52px invisible `.hit` circle behind the dot, and `9px 12px` padding on the label (28px tall). Without these the targets are unusably small, especially on touch.

**The wheel can no longer be driven off raw scroll progress.** It must hold still while you read a chapter's stories, then ease to the next marker only when the story crosses a chapter boundary — so `render()` fires a `gsap.to(wheel, {rotation: -ci*STEP, duration:.75})` on change instead of `gsap.set()` every frame.

**Photocard fan.** Polaroid-style cards: cream `#f6f2e8` frame, a 4:3 photo inset and the caption beneath. Frame is tight — roughly 9px sides/top, 11px below the caption, leaving ~20% of the card as border.

> ⚠️ **Use px for the card padding, never `%`.** The card is absolutely positioned, so percentage padding resolves against **`.deck`'s width (720px)**, not the card's own ~210px. A `13%` bottom silently became **94px** of dead white space. Note the trap is specific to the card: `figcaption` is an in-flow child, so *its* percentages resolve against the card as expected — which is exactly why the bug was hard to spot.

Behaviour, per the client's sketch:

1. A chapter opens showing **one card** and its text.
2. Each scroll step **reveals the next card, sliding in from the left** into its slot — the fan grows left to right and accumulates.
3. **Every revealed card is clickable** (also `role="button"` + Enter/Space). Clicking shows that card's text and brings it forward at `scale(1.07)`, **without moving the scroll**.
4. Crossing into a new chapter **clears the whole fan**; the next chapter starts from one card again.

Slot geometry for card `j` in a chapter of `n`, with `mid = (n-1)/2`:
```
x = (j-mid) * SPREAD      SPREAD = 98px
y = |j-mid| * 5px         slight downward arc at the edges
rot = (j-mid) * 4.5deg  + a fixed per-card jitter
unrevealed: x-90px, scale(.9), opacity 0   ← gives the left-to-right entrance
```

> **`SPREAD` must exceed roughly half the card width.** At 64px against 239px-wide cards the fan was ~70% overlapped and read as two cards, not five. At 98px the widest chapter (5 stories) spans 645px inside a 720px deck.

Two layout traps:
- ⚠️ **Every card is absolutely positioned, so the deck has no intrinsic height.** Guessing an `aspect-ratio` left the box taller than the card and pushed the copy out of place. Use a **hidden in-flow duplicate card** (`.sizer`, `visibility:hidden`) to size the container exactly.
- Rotated cards overhang that sizer, so the deck needs `padding-bottom` or the bottom corners clip.

Guard `selectCard()` against clicks on cards that aren't part of the visible fan — they're still in the DOM at `opacity:0`, and without the check a hidden future card can hijack the copy.

**Original frame 3 geometry** (superseded by the above, kept for reference):
- Chapter heading — Montserrat Medium, uppercase, centred, baseline `y = 346.5` (just under the arc apex at 377.6)
- Photo — `204.2 × 136.1` (3:2) at `x = 236.4, y = 152`
- Body copy — uppercase Montserrat Regular, left-aligned at `x = 466.5`, 8 lines, `line-height = 14.4` units, first baseline `y = 214.7`
- The photo/text pair spans `x = 236.4 → ~690` with a `25.9` unit gutter

**Accessibility / fallback.** Under `prefers-reduced-motion`, skip the pin and rotation entirely and render the five chapters as a plain vertical stack. Below ~768px the ±70° sweep doesn't fit — drop the wheel and use a vertical timeline on mobile. Build the mobile layout as a genuinely separate branch, not a squashed desktop one.

---

## Page specs

### 1 — Password gate (`/`)

Full-bleed background photo (portrait, `736 × 985`, cropped to cover) under a **full-page black scrim at 40% opacity**. Centred stack, all elements `207.1` units wide (~24.2vw), horizontally centred on the page:

| Element | Geometry | Style |
|---|---|---|
| `PASSWORD` label | baseline `y = 266.2` | Montserrat SemiBold, white |
| Text input | `x 323.3→530.4`, `y 218.9→247.8` (h `28.9`) | fill `#E5E5E5`, no visible border |
| `ENTER` button | `x 323.3→530.4`, `y 179.0→207.9` (h `28.9`) | fill `#2A4300`, white SemiBold label |

Gaps: label→input `18.2`, input→button `11.0`.

The **ENTER click is also the audio gesture** — see the Background music section. It must call `audio.play()` synchronously and navigate with `router.push()`, not a hard redirect.

#### Revisions after client review

- **Background is the real garden photo** (`img/intro.jpg`), not the stock hillside placeholder that shipped in the PDF. A dedicated gate image would still be better — it currently shares a frame family with the intro video.
- **Wordmark sits at the top of the stack**, above the PASSWORD label.
- **ENTER carries a heavy drop shadow** (`0 10px 30px rgba(0,0,0,.45)`) plus a lift on hover, so it reads as the primary action against a busy photo.
- **Field and button are both rounded** (`--r-sm`), not square as the PDF had them.

#### The 0–100 loader

After a correct password, the input stack fades and a **0 → 100 counter with a progress bar** runs for ~2s before the site is revealed. Eased with `1-(1-t)^2.2` so it decelerates into 100 rather than climbing linearly.

> ⚠️ **Do not drive this with `requestAnimationFrame` alone.** rAF stops completely in a backgrounded tab, so a guest who switches apps mid-load returns to a loader frozen at 0 with no way forward. Keep rAF for smoothness but add a `setTimeout(finish, DUR+700)` guard — `setTimeout` is throttled in background tabs but still fires. Guard both paths with a `finished` flag so the reveal can't run twice.

In the real build, hold the counter at ~90 until the intro video has actually resolved, then release to 100 — otherwise it's pure theatre.

#### Ambient motion (shared with the journey panel)

The same three layers run on **both the gate and the journey section**, so build them as reusable helpers — `buildGrass(el)` and `makeMotes(canvas, density, tint)` returning `{start, stop}` — rather than two copies.

Two things to get right when reusing them:
- **z-index.** On the gate the layers sit at `z-index:2`, above the scrim. Inside the journey they must drop to **`z-index:0`**, or they paint over the timeline arc and the photocards.
- **Only animate canvases the user can see.** The gate's loop stops when the gate is dismissed, and a `visibilitychange` listener stops both when the tab is backgrounded. A canvas rAF loop left running for a whole session is a real battery cost on phones.



The gate is a still photo of a meadow, so it gets three cheap layers of life. Not in the PDF — an addition.

1. **Photo drift** — `gateDrift`, a 42s alternating Ken Burns (scale 1.05 → 1.13 with a slight offset). Pure CSS, GPU-composited.
2. **Swaying grass** — ~60 SVG blades generated in JS along a `0 0 1200 170` viewBox, each a tapered quadratic path with randomised height, lean, width, animation duration (3.4–6.4s) and a negative delay so they start out of phase. Each pivots at its own base via `transform-box: fill-box; transform-origin: 50% 100%` — far more reliable cross-browser than user-unit `transform-origin` on SVG.
3. **Drifting pollen** — a canvas of ≤55 motes rising slowly with a sine-wave horizontal sway. Particle count scales with viewport area; `devicePixelRatio` is **capped at 2**, since 3x on phones triples fill rate for no visible gain.

Three implementation notes:

- ⚠️ **`<canvas>` is a replaced element.** `position:absolute; inset:0` does *not* stretch it — `width:auto` resolves to its intrinsic 300×150 and the `right` inset is dropped. **Explicit `width:100%; height:100%` is required.** A global `img,video{width:100%}` rule won't cover it. This bit during the build: the canvas silently stayed 300×150 inside a 1100×700 gate, so all the pollen clustered in one corner.
- **Cancel the rAF loop when the gate closes.** Otherwise it keeps burning frames behind every other page for the rest of the session.
- **Skip all three entirely under `prefers-reduced-motion`** — checked in JS, not just CSS, so the canvas loop never starts.

### 2 — Intro (`/intro`)

Full-bleed **background video** (`854.5 × 481.7`, cover). Needs `autoplay muted loop playsInline` — `muted` is non-negotiable or mobile Safari refuses to autoplay. Supply a `poster` frame so the first paint isn't black.

Nav sits at the **top** on this page (see below). A script monogram in white sits centred just under it (`x ≈ 394→440`, `y ≈ 410→425`).

#### Layout: lockup bottom-left, verse bottom-right

Per the client's supplied still (`prototype/img/intro-src.webp`), the intro is a bottom-aligned row — **script lockup at bottom-left, verse right-aligned at bottom-right** — not the centred stack the earlier frame implied. Measured from that still (1212 × 679):

```
lockup   x 41–166    y 460–566      (~3.4% from left,  ~17% up from bottom)
verse    x 767–1195  y 541–610      (~1.4% from right, ~10% up from bottom)
```

The verse sits slightly lower than the lockup. On mobile the row collapses to a left-aligned column.

#### The verse is its own layer

The verse is **clickable and cycles to another verse on each tap**.

> ✅ **Resolved.** The supplied *still* had the lockup and verse burned into the raster, which would have ghosted the old verse behind each new one. The **video master is text-free**, so this is no longer an issue. The painted-out still (`prototype/img/intro.jpg`) survives only as a fallback — produced with Pillow by sampling clean pixels above each text box, pasting over, and feathering the seams.

Three layers over the plate:

1. **Video** — text-free, `muted loop playsInline`
2. **Lockup** — the brush-script wordmark, bottom-left. Ship as **SVG**, not a webfont; it's custom lettering. The prototype substitutes Google's *Pacifico* as the closest available stand-in — it is noticeably rounder than the real dry-brush mark.
3. **Verse** — bottom-right, right-aligned. A real `<button>` (not a `div`) so it's keyboard-reachable and announced. `aria-live="polite"` so the new verse is read out on change.

Both text layers need a soft `text-shadow` plus a gentle bottom gradient on the plate — white text over bright garden foliage is otherwise unreadable.

#### Encoding the background video

**Current source: `intro2.mp4`** — an edit export, not a camera master: **3840×2160, 59.94 fps, H.264 at 105 Mbps, 2:42 — 2.05 GB.** Already colour-graded and text-free, but unusable as delivered:

- **Size.** 2.05 GB. No guest on mobile data will ever load it.
- **Frame rate.** 59.94 fps roughly doubles the bitrate a background loop needs, for no perceivable benefit.
- 🔴 **The last ~54 seconds are pure black.** Content runs 0 → **109.6s**, then hard-cuts to black through to the 162s end. Looping the untrimmed file would leave the hero section black for a third of every cycle. Verified by sampling luminance across the timeline.

Transcode used for the prototype — **2051 MB → 11.77 MB** (1080p30, 109s, ~900 kb/s):

```bash
ffmpeg -i intro2.mp4 \
  -t 109 -an -sn -dn -map_metadata -1 \
  -vf "scale=1920:-2,fps=30" \
  -c:v libx264 -preset medium -crf 28 -profile:v high -level 4.1 -pix_fmt yuv420p \
  -movflags +faststart intro-web.mp4
```

Why each part matters:
- **`-t 109`** cuts before the black tail. Re-check this if the source is ever re-exported.
- **`-an`** strips audio. The video must be silent anyway — the song plays over it.
- **`-map_metadata -1`** drops metadata, including any GPS coordinates. Worth doing on anything published.
- **`+faststart`** moves the `moov` atom to the front so playback begins before the download finishes. Without it the video looks broken on slow connections.
- **`yuv420p`** — other pixel formats silently fail to decode in some browsers.
- **No `eq` filter this time.** Unlike the earlier camera master, this export is already graded.

Also generate a **poster frame** (`img/intro-poster.jpg`, ~28 KB) so the first paint isn't black while the video buffers.

> **11.77 MB is still on the heavy side for mobile.** It streams progressively thanks to `+faststart`, so playback starts fast, but a looping guest eventually pulls the whole file. If that matters, trimming to a 40–60s loop would roughly halve it — a content decision, not a technical one.

> Keep the 2 GB source out of the deploy. Add `prototype/video/intro2.mp4` to `.gitignore` — Vercel's deploy limits and your git history will both thank you.

```tsx
const [i, setI] = useState(0);
<button className="verse" aria-live="polite" onClick={() => setI(n => (n + 1) % VERSES.length)}>
  {VERSES[i].text}<span className="ref">{VERSES[i].ref}</span>
</button>
```

Verses live in `content/verses.ts` as `{text, ref}[]` so the couple can edit the list without touching components. Crossfade ~340ms on change and **guard against click-mashing mid-fade**, or the text swaps while opacity is still animating and flickers.

Give it a discoverable affordance — the verse doesn't look tappable otherwise. The prototype fades in a one-time `TAP THE VERSE FOR ANOTHER` hint a beat after entry, then dismisses it permanently on first tap.

**Verse list, confirmed by the client:** Jeremiah 29:11, Luke 1:37, Genesis 2:18, Ecclesiastes 4:12, Colossians 3:14.

**Placement:** right-aligned bottom-right on desktop. **On mobile it centres and steps up a size** — left-hugging small text read as an afterthought on a phone.

### 3 — Journey (`/journey`)

The circular timeline described above, plus the olive monogram top-left (`x ≈ 26→55`, `y ≈ 425→444`), the RSVP pill top-right, and the section nav at the bottom.

There's also a **small glyph cluster centred at `x ≈ 424, y ≈ 27`** — below the section nav, three groups at `x ≈ 390–400`, `419–428`, `449–452`. Almost certainly prev/next chapter controls flanking a decorative mark (the storia reference has equivalent "Indietro / Avanti" buttons). Too small to identify confidently from the vector data — **open the PDF and look at this region before building it.**

### 4 — Linear timeline: prototyped, then rejected

Frame 4 is the horizontal-timeline alternative. It was **built as a full working variant** (`prototype/index-timeline.html`) so the two could be compared side by side, then **rejected in favour of the circular wheel**. Its chapter titles remain the source for the wheel's content.

What that variant contained, in case it's ever revisited:
- A light (white) journey section, in contrast to the dark wheel
- Chapter labels above a horizontal olive axis with five nodes
- A **draggable thumbnail scrubber** that changed the chapter live as it moved and snapped to the nearest node on release
- Photo and copy in a left column, circular olive prev/next centred, and a three-icon row (sound, brightness, gallery) under the section nav

> **The wheel is the harder build.** The linear version needed no pinning, no scroll hijacking, and no separate mobile code path, and it dropped GSAP entirely. The circular one is the more distinctive design and is what the client chose — but budget accordingly, and keep the `prefers-reduced-motion` and sub-768px fallbacks non-negotiable, because on those paths the wheel degrades to roughly the linear layout anyway.

The variant file can be deleted once the decision is settled; nothing in the production build should reference it.

### 5–7 — Wedding (`/wedding`)

Shared chrome for all three: olive monogram **top-left** (`x ≈ 54→76`, `y ≈ 426→450`), RSVP pill top-right, section nav bottom.

#### Panel chrome: header pinned, content scrolls

The wedding section is `display:flex; flex-direction:column; overflow:hidden`. The tab bar is `flex:none`; the **active panel** takes the remaining height and scrolls internally (`overflow-y:auto; overscroll-behavior:contain`).

Why it matters: with the section scrolling instead, a long tab (FAQ) scrolled the tab bar off the top, and the gap between the logo/RSVP and the tab bar **jumped between tabs**. Pinned, the bar sits at a constant 88px on desktop / 97px on mobile on *every* tab. Verified across all five.

- **Timeline and motif do not scroll on desktop** — there's room for all of it, and a nested scrollbar in a half-empty panel is friction for nothing. The timeline's scroll area is mobile-only.
- **Motif is a 3-column grid on desktop**, single column on mobile.
- **FAQ carries 11 questions** so the scroll behaviour is exercised; it's the only tab that scrolls at 1280×800.
- ⚠️ **This panel has no vertical slack.** Anything added has to be budgeted against 100vh or it will collide with the fixed bottom nav.

A **sub-tab bar** at `y = 357`: `DETAIL · TIMELINE · MOTTIF · ENTOURAGE · FAQ` at `x = 276.2, 341, 415, 479, 561.7`. Beneath it a hairline track at **50% black** (`x 241.4→622.4`, `y = 345.6`, `lw 0.4`) and a **sliding active underline** at full black — `46.1` wide, `lw 1.1`, measured at `x = 267.5` / `336.1` / `408.2` for the first three tabs. Inactive tab labels also sit at 50%. Animate the underline's `x` and `width` between tabs; that sliding indicator is the detail that sells the design.

Render tabs as client-side state, not routes, so the underline can animate.

**DETAIL** — `MARCH 5, 2027` (SemiBold, `y = 310.3`), a **countdown** (`y = 276.6`), `at Jpark Island Resort, Cebu` (`y = 211.5`), and a map block `237.6 × 96.2` at `x = 310.8, y = 99.4`.
> The countdown must compute on the **client after mount**. Rendering a live timer on the server guarantees a hydration mismatch.

The countdown shows **months · days · hours · minutes · seconds**.
> **Count months by calendar, not by dividing days.** `days/30` drifts against the wall calendar and will disagree with what guests see on their phones. Step a `Date` forward month-by-month from now toward the target, back off one if you overshoot, then take the remainder in days/hours/minutes/seconds.

#### The map is embedded, not a link out

The PDF's block is a flat `maps` label — a link. **Replaced with a live, pannable map embedded in the page**, with the link-out kept as a secondary action.

**Decision: Leaflet + plain OpenStreetMap tiles.** No API key, no Google Cloud project, no billing account.

Venue marker at **10.282000, 123.996444** (Jpark Island Resort & Waterpark, per Wikipedia).

```js
const m = L.map(el, { scrollWheelZoom: false }).setView([10.282000,123.996444], 15);
L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
  attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
  maxZoom: 19, crossOrigin: 'anonymous'
}).addTo(m);
```

OSM's default style is colourful, so desaturate it — but **only the tile pane**, or you grey out the attribution too:

```css
.mapwrap .leaflet-tile-pane { filter: grayscale(.85) contrast(.92) brightness(1.04); }
```

Unlike Google, OSM's licence permits restyling; the requirement is that attribution stays present and legible.

> ⚠️ **Two dead ends, both worth not repeating.**
>
> **Google Maps Embed** — the keyless `maps.google.com/maps?q=…&output=embed` form rendered as a blank grey box. The `load` event fired and no console error appeared, but nothing painted. The documented Embed API would likely work, but needs a key on a **billing-enabled** project — disproportionate for one static pin.
>
> **CARTO Positron** (`{s}.basemaps.cartocdn.com/light_all/…`) — now returns an **"API KEY REQUIRED" watermark image** instead of map data. Critically, those tiles still return **HTTP 200 with a valid PNG**, so every naive check passes: the request succeeds, `img.complete` is true, `naturalWidth > 0`. It looks healthy and is completely broken.
>
> **Lesson for verifying any tile source:** "the image loaded" proves nothing. Draw a tile to a canvas (`crossOrigin: 'anonymous'`) and measure pixel variance. A real map tile at zoom 15 has hundreds of distinct colours and a standard deviation around 20; a watermark tile is near-uniform white with a handful of colours.

Sizing: the PDF's `237.6 × 96.2` is **~2.47:1**, too letterboxed to use as a map. Widened to **2:1 on desktop, 4:3 on mobile**. A deliberate deviation from the mock — flag it.

Three things that matter in implementation:

- **`scrollWheelZoom: false`.** Without it, scrolling the page over the map zooms the map instead and traps the user. Dragging still works.
- **Initialise lazily.** Build the map only when the DETAIL tab is first shown, and call `invalidateSize()` after — Leaflet mis-measures a container that was hidden at init and renders a quarter-map.
- **Keep a "Get directions" button.** Guests navigate from their phones, and `https://www.google.com/maps/dir/?api=1&destination=…` opens the native Google/Apple Maps app rather than a cramped in-page frame. The embed is for orientation; the button is for actually getting there.

Use a `divIcon` for the marker rather than Leaflet's default PNG pin — it takes the olive palette directly and avoids the classic broken-icon-path problem when Leaflet's asset URLs don't resolve.

**TIMELINE** — **redesigned as a vertical list**, following `wedding.jongjeonglee.com`. Replaces the PDF's horizontal axis.

- A vertical spine with an **olive circular node per stop, each carrying its own icon** (door, rings, glass, music, plate, wave) — the reference pairs an icon with every entry.
- The list lives in **its own scroll area** (`height: min(46vh,340px); overflow-y:auto`), with a top/bottom `mask-image` fade so entries dissolve at the edges rather than clipping.
- ⚠️ **`overscroll-behavior: contain` is essential.** Without it, reaching the end of the list chains the scroll straight into the pinned horizontal track and throws the guest sideways into another section.
- A **scroll cue** (animated mouse glyph) fades in on `:hover` over the list, since a nested scroll area is otherwise invisible.

Original PDF geometry, superseded: intro copy at `y = 269.1 / 259.7`, six stops on an axis (`x 188.6→687`, `y = 190.2`, `lw 0.7`), times at `y = 216`, labels at `y = 207.6`, `x ≈ 180, 277, 384, 482, 584, 675`:

`3:30 Doors Open · 4:00 Ceremony · 5:30 Cocktail Hour · 6:30 Reception · 7:00 Dinner · 9:00 Send off`

> ✅ The PDF labelled both 6:30 and 7:00 "Reception". Client confirmed 7:00 is **Dinner**.

**MOTTIF** — the PDF had only a `FOR THE LADIES` heading. Expanded to **five entourage groups**, each with its own palette and an attire note: Principal Sponsors, Secondary Sponsors, Bearers & Flower Girls, For the Ladies, For the Gentlemen. Five groups don't fit a 100vh panel, so this gets **its own nested scroll area** with edge fades and `overscroll-behavior:contain`, the same pattern as the day-of timeline.

**ENTOURAGE** and **FAQ** — tab labels exist but **no content was designed**. Scaffold: entourage as a role-grouped name list, FAQ as an accordion.

### Persistent chrome — revised

The PDF's small "K & C" text monogram is **dropped**. Replaced by the client's real wordmark:

- **Logo top-right** (`img/kliffandchao-logo.svg`, viewBox 2919.83 × 2508.83). One file must serve both the dark sections (white) and the light wedding panel (olive). **Inline the SVG and let its paths inherit `currentColor`** — in Next.js, import it as a component (SVGR) rather than an `<img>`.

  Two traps, both hit during the build:
  - **A CSS `mask` over `background-color:currentColor` also works, but is fragile** — it silently renders nothing if either `mask-image` or `aspect-ratio` fails to resolve, and debugging an invisible element is unpleasant. Inlining is more robust.
  - ⚠️ **A `<style>` block inside inline SVG is document-scoped, not shadowed.** This logo ships with `.cls-1{fill:#fff}` inside it, which leaks into the whole page as a global rule *and* pins the fill so `currentColor` never applies. **Strip `<style>` and any hard-coded `fill` attributes on injection**, then set `fill:currentColor` on the `<svg>` from your own stylesheet — `fill` is an inherited SVG property, so the paths pick it up.
- **Logo top-left, RSVP pill top-right.** The logo colour is **dynamic**: white over the dark intro and journey, near-black `#14180d` on the cream wedding panel (matching that page's body text). Driven from `setSec()`; the inline SVG inherits it via `fill:currentColor`. The drop-shadow only helps over photos, so `body.on-light .brand{filter:none}` removes it on the light panel.
- **Audio toggle stays bottom-left**, colour-switching with the section like the nav. It carries **both a speaker glyph and the equaliser bars** — waves when playing, struck through when muted, bars frozen and dimmed.
- **The wordmark is the home button.** Clicking (or Enter/Space on it) returns to the intro panel. `role="button"`, `tabindex="0"`. The pill is **substantially larger** than the PDF's `57.6 × 19.9` — roughly `92 × 36` at 1280px, with a drop shadow. The mock's pill was too small to read as a primary action.
- On the **gate**, the logo is not part of the input stack: it's absolutely positioned **centre-top** and pinned to white (`color:#fff !important` plus `fill:#fff` on the svg) so the section colour-switching can never darken it against the photo.

### Section nav (shared component)

Labels `INTRO · JOURNEY · WEDDING`, with a hairline olive rule beneath (length `249.9`) and **three dots on the rule — one per section, sitting at each label's centre** (`x = 300.2, 423.9, 545.8`, diameter `4.3`). It's a stepper, not a plain underline. Active item is SemiBold, inactive Regular.

> ⚠️ **Build each item as one column containing *both* its label and its dot.** The first attempt laid labels out with flex `gap` and positioned dots separately at fixed percentages — they drifted visibly out of alignment, which the client spotted immediately. With one flex cell per item and the dot inside it, alignment is structural rather than arithmetic (measured: 0.01px). The rule then spans `left:16.667%` to `right:16.667%` — dot-centre to dot-centre across three equal cells.

Position differs by page in the PDF — **top** on the intro frame (labels `y = 441.7`, rule `y = 435.2`), **bottom** on all content frames (labels `y = 51`, rule `y = 44.5`). Build one component with a `position: 'top' | 'bottom'` prop rather than two components.

> The PDF marks `JOURNEY` as active on frames 2 *and* 3, and marks nothing active on frames 5–7. That's mock inconsistency, not intent — wire active state to the current route.

---

## Background music

Track: **"The Blessing (Cinematic Version)" — Kari Jobe & Cody Carnes.** The PDF has no audio control, so this section is an addition to the design rather than a decode of it.

### The autoplay problem — which the gate happens to solve

Every modern browser blocks audio that starts without a user gesture. A site cannot just play a song on load.

This site gets the gesture for free: **the guest has to click ENTER.** The song starts on a successful unlock, and no guest ever hits a silently-blocked player.

Two constraints follow, and both are easy to get wrong:

**1. iOS invalidates the gesture token fast.** If you `await fetch('/api/gate')` and *then* call `play()`, Safari has often already dropped the gesture and playback fails. Start playback **synchronously inside the click handler, muted** — muted playback is always permitted — then unmute once auth resolves, which needs no gesture:

```ts
async function onEnter() {
  audio.muted = true;
  void audio.play();                        // synchronous, inside the gesture
  const res = await fetch('/api/gate', { method: 'POST', body: … });
  if (res.ok) {
    audio.muted = false;
    fadeIn(audio, 1500);
    router.push('/intro');                  // client-side — see below
  } else {
    audio.pause();
  }
}
```

**2. Navigation after the gate must be client-side.** The `<audio>` element lives in the root layout so it survives route changes — but only for *client-side* transitions. A hard `window.location` redirect reloads the document, destroys the element, and drops you back behind the autoplay block with no gesture left. Use `router.push()`.

### Component shape

One `<audio loop preload="none">` rendered **once** in the root layout, wrapped in a client `AudioProvider` exposing `{ isPlaying, isMuted, toggle }` through context. Rendering it per-page restarts the song on every navigation.

`preload="none"` matters: a 5MB file shouldn't download before the guest has even entered.

### The toggle

No slot for this exists in the PDF. Put it **bottom-left**, mirroring the monogram's top-left position — it clears the section nav (bottom-centre) and the RSVP pill (top-right), and stays put on every page.

Small animated equaliser bars while playing, collapsing to a crossed-out speaker when muted. Inherits the page's foreground colour (white over media, olive on light pages). Persist the choice to `localStorage` so a guest who mutes stays muted across pages and reloads.

### Default state — worth a decision

**Recommendation: default ON**, with volume faded in over ~1.5s rather than slamming to full, and the toggle visible from the intro's first frame alongside a brief self-dismissing hint (*"♪ The Blessing — tap to mute"*).

The counter-argument is real — someone opening this at work gets startled. Flipping to default-muted (with the toggle pulsing to invite a tap) is a one-line change. Flagged in the open items.

### The audio file

✅ **Supplied:** `audio/The Blessing - Cinematic Version.mp3` — **5.82 MB, 402s (6:42)**. Loads and plays correctly.

- ⚠️ **The filename contains spaces.** They must be percent-encoded in the `src` (`The%20Blessing%20-%20Cinematic%20Version.mp3`) or the request 404s. **Rename it to `the-blessing.mp3` before production** — spaces in URLs are a recurring source of breakage across CDNs and servers, and there's no upside.
- 5.82 MB is acceptable but on the high side for mobile. Re-encoding at **96–128 kbps** would roughly halve it with no audible loss as background music.
- MP3 alone is fine; every current browser handles it.
- **iOS respects the hardware silent switch** for HTML5 audio. Nothing to be done about it — just don't lose an hour debugging it.

> The intro video is `muted` for its own autoplay reasons, so there's no clash: the song plays over silent footage.

> The track is commercially licensed. For a private, password-gated family site that's unremarkable, but keep the file behind the gate and off any public URL, and don't attach ads or monetisation.

---

## Project structure

> ⚠️ **The three sections are panels on ONE page, not three routes.** Intro, journey and wedding live side by side in a pinned horizontal track, so they cannot be separate `page.tsx` files — a route change would unmount the track and kill the scroll timeline. `/rsvp` stays a real route (it's a full-screen overlay).

> ⚠️ **Superseded:** the folder tree now lives in `BUILD_PLAN.md` (it adds `admin/`, Prisma, Supabase helpers and `components/site/`, and drops the Sheets read path). The warning above still applies.

Keeping every string in `content/` is what makes "swap the placeholders later" a five-minute job instead of a hunt through JSX.

---

## Password gate

Shared secret `kliffandchao`, same for every guest.

**Store a hash, not the password.** Node 24 ships `scrypt`, so this costs zero dependencies and no native build pain on Windows. Generate once, put the result in `SITE_PASSWORD_HASH`:

```bash
node -e "const c=require('node:crypto');const s=c.randomBytes(16);console.log('scrypt$16384$8$1$'+s.toString('base64url')+'$'+c.scryptSync('kliffandchao',s,64,{N:16384,r:8,p:1}).toString('base64url'))"
```

Verify with `timingSafeEqual`. The ~80ms scrypt cost doubles as free brute-force friction.

**Normalize input before comparing** — `.normalize('NFKC').trim().toLowerCase()`, and set `autocapitalize="none" autocorrect="off" spellcheck="false"` on the field. Mobile keyboards autocapitalize; without this a chunk of guests will fail on a correct password and text the couple instead.

**Session:** `jose` HS256 JWT in an httpOnly cookie. Pin `algorithms: ['HS256']` on verify (otherwise you're open to `alg` confusion). Include an `epoch` claim read from env — bumping `SESSION_EPOCH` invalidates every live session at once if the password leaks.

Cookie: `httpOnly, secure, sameSite: 'lax', path: '/', maxAge: 180d`.
> `sameSite` must be **`lax`, not `strict`** — guests arrive from Messenger/Viber/WhatsApp links, and a `Strict` cookie isn't sent on cross-site navigation, so every guest would be re-gated on every arrival from chat.

**Enforce in two places, not one:**

1. `middleware.ts` — redirect UX only. Runs on Edge, where `node:crypto` is unavailable; `jose` works because it's built on Web Crypto. (Password *verification* needs `scrypt`, so it lives in `/api/gate`, a Node-runtime handler — not in middleware.)
2. `requireGate()` — called independently by every gated layout and every API route.

> ⚠️ The second check is not belt-and-braces. **CVE-2025-29927** (March 2025, CVSS 9.1) let an attacker bypass Next.js middleware entirely with a crafted `x-middleware-subrequest` header. Apps whose only auth check lived in middleware were fully open. **Pin Next.js ≥ 15.5.x** and never make middleware the sole gate.

Also ship `X-Robots-Tag: noindex, nofollow` and a `robots.txt` with `Disallow: /`. A "private" site indexed by Google is the most likely way this leaks.

Validate the `?next=` deep-link param (`startsWith('/') && !startsWith('//')`) or it's an open redirect.

**Be straight with the client:** `kliffandchao` is twelve guessable characters and will end up in group chats. Its protection is obscurity plus rate limiting, not cryptography. Treat the site as semi-public — no home address, no bank/GCash details.

---

## RSVP + Google Sheets

> ⚠️ **Partly superseded.** Postgres is now the write-of-record, so the Sheets-as-database design below no longer applies. Status of each subsection:
>
> - **Superseded by `BUILD_PLAN.md`:** The core move (append-only log) · Reading + caching · Types · API surface · Validation (same rules, now inside a DB transaction) · Env vars · Scale note.
> - **Still valid:** the `safeCell` escape (used by the RSVP mirror) · Name matching — the reasoning, the misspelling examples, the scoring ladder, the nickname column and the `{ id, displayName }` rule · Already-RSVP'd behaviour · Sheet layout for the `Guests` tab and the paste-as-values warning (`RSVP_Log` is now a mirror; `RSVP_Current` is optional) · Google Cloud setup · Email mirror · Rate limiting.

### The core move: append-only log

This is what makes the whole thing safe without transactions, which Sheets doesn't have.

**Three tabs with strict ownership:**

| Tab | Written by | Purpose |
|---|---|---|
| `Guests` | **The couple, by hand. The app never writes.** | Invite list + party structure |
| `RSVP_Log` | **The app only, append-only. The couple never edits.** | Immutable record of every submission |
| `RSVP_Current` | Nobody — pure formulas | Human-readable "where do we stand" |

The app's only write is `spreadsheets.values.append`, which is **atomic server-side** — Google allocates the row. The app never reads a row index in order to write it, so there's no read-modify-write race at all. This kills every concurrency failure mode at once:

- Two cousins submitting simultaneously → two rows, both kept.
- A guest editing their answer → a third row; latest timestamp wins, history preserved.
- **The couple editing the sheet while guests submit** → they're in a different tab the app never touches. This is the one that matters most: they'll be in that sheet constantly for 17 months.
- Someone sorting the `Guests` tab → harmless; rows are keyed by `guest_id`, not position.

```ts
await sheetsFetch(`/values/RSVP_Log!A:H:append`, {
  method: 'POST',
  body: JSON.stringify({ values: rows }),
  // valueInputOption=RAW  &  insertDataOption=INSERT_ROWS as query params
});
```

Both options are load-bearing. `USER_ENTERED` would *parse* your strings (a message of `=1+1` becomes a formula). The default `OVERWRITE` will clobber cells if Google's table detection guesses the boundary wrong.

**Escape free text anyway** — `RAW` protects the Sheet, but the moment the couple does File → Download → CSV and opens it in Excel, a cell starting with `= + - @` executes:

```ts
const safeCell = (v: string) =>
  (/^[=+\-@\t\r]/.test(v) ? `'${v}` : v).replace(/[\u0000-\u001F]/g, '').slice(0, 500);
```

### Reading + caching

Sheets API allows **60 reads/min per service account** — and since there's one account, every Vercel instance shares that bucket. A typeahead hitting Sheets per keystroke would exhaust it with three concurrent guests. **Caching is a correctness requirement here, not an optimization.**

Two layers: a module-scope memo (60s, ~5ms warm) in front of `unstable_cache` (300s, tagged `guests`, shared across instances). One `values.batchGet` pulls both tabs in a single call. Call `revalidateTag('guests')` after each write, and expose a secret-guarded `POST /api/admin/revalidate` so the couple can force a refresh after bulk-editing.

Steady-state: ~12 Sheets reads/hour against a 3,600/hour budget.

Wrap calls in exponential backoff with jitter, 3 attempts, retrying **only** 429/500/502/503. Never retry other 4xx — a 400 means a malformed range, and retrying just burns quota.

**Map columns by header name at read time, never by fixed index.** Validate the header row on load and throw a specific error (`"Guests tab is missing column 'party_id'"`). The couple will reorder columns.

### Name matching — run it server-side

Two options: preload the list to the client (instant, but ships all ~200 names to anyone with the password) or search server-side (~35ms warm from `sin1`, returns max 8 results).

**Go server-side.** Shipping the full guest list as a JSON blob quietly undoes the point of the gate — guest lists are socially loaded, and people find out who *wasn't* invited. 35ms is under the perceptual-instant threshold anyway. Debounce 150ms, `AbortController` per keystroke, min query length 2, cap 8 results, rate-limit the endpoint.

**Use phonetic matching, not just edit distance:** `double-metaphone` (~3kB) + `fastest-levenshtein` (~1.5kB).

> This matters concretely for a Cebu wedding. Guests will type `Co` for `Kho`, `Chow` for `Chao`, `See` for `Sy`, `Wy` for `Uy`, `Dee` for `Dy`, `Ong` for `Ang`. Edit distance can't help — `Co`→`Kho` is distance 2 on a 3-letter word, so any threshold loose enough to catch it matches everything. Double metaphone encodes both to `K` and nails it. Fuse.js misses these too.

Scoring ladder: exact 100 → prefix 90 → substring 70 → within edit distance 65 → phonetic match 55. Threshold at 50, take top 8. Precompute normalized forms and metaphone codes **once at cache-build time**, not per query.

Search across first name, last name, both name orders, **and a `nickname` column** — Filipino guests overwhelmingly go by nicknames ("Bing", "Dodong"). That column will earn its keep.

Return `{ id, displayName }` only — never `partyLabel`, which would reveal family structure to a stranger.

### Types

Trimmed to your chosen scope: status per guest, one message per party.

```ts
export type AttendanceStatus = 'attending' | 'not_attending';

export interface GuestRecord {
  id: GuestId;                  // "g_7fK2mQ" — opaque, random, stable
  firstName: string; lastName: string; nickname: string | null;
  partyId: PartyId; partyLabel: string;
  side: 'kliff' | 'chao' | 'both';
}

export interface GuestRsvpState {
  status: AttendanceStatus | null;      // null = no response yet
  respondedAt: string | null;           // ISO UTC
  respondedByGuestId: GuestId | null;   // who in the party submitted
}

export interface Party {
  id: PartyId; label: string; members: Guest[];
  hasSubmission: boolean; lastRespondedAt: string | null;
  editable: boolean; deadlineIso: string;
}

export interface RsvpSubmission {
  submittedByGuestId: GuestId;          // server derives the party from THIS
  responses: { guestId: GuestId; status: AttendanceStatus }[];
  message?: string;                     // one per party, max 500
  clientSubmissionId: string;           // uuid per form mount — idempotency key
}
```

Note what's absent: **`RsvpSubmission` carries no `partyId`.** The server derives it from `submittedByGuestId`. Accepting a client-supplied party id would let anyone RSVP for any party.

### API surface

| Method | Path | Notes |
|---|---|---|
| `POST` | `/api/gate` | `{password}` → cookie · 401 invalid · 429 |
| `GET` | `/api/guests/search?q=` | 400 if `q.length < 2`; returns ≤8 |
| `GET` | `/api/party?guestId=` | Reachable only via a `guestId` you already matched |
| `POST` | `/api/rsvp` | Returns the fresh `Party` so the client renders server truth |
| `POST` | `/api/admin/revalidate` | `x-admin-secret` header |
| `GET` | `/api/health` | Sheet reachable? cache age? |

All handlers: `runtime = 'nodejs'`, `dynamic = 'force-dynamic'`. There is deliberately no `GET /api/parties/:id` — that would allow bulk enumeration.

### Validation on `POST /api/rsvp`

In order: `requireGate()` → rate limit → `zod` parse → deadline check (409) → resolve submitter → **build the allowed set from the submitter's party and reject any `guestId` outside it (403)** → reject duplicate guest ids → idempotency check against `clientSubmissionId` → append → `revalidateTag` → fire-and-forget email mirror.

The idempotency key matters on Philippine mobile data, where a request can succeed server-side while the client sees a timeout and retries.

### Already-RSVP'd behaviour

**Allow edits until a deadline; don't hard-lock on first submission.** Over a 17-month window people's plans change, and a hard lock just generates the DMs to the couple that this site exists to prevent.

- Banner: *"We've got your RSVP from 3 March 2026. You can update it until 5 January 2027."*
- **Prefill every control with the previous answer.** Showing a blank form to someone who already responded makes them think it was lost, and they re-submit in a panic.
- CTA flips to "Update our RSVP."
- Per-person attribution — *"Answered by Maria on 3 March"* — so a party of six trickling in over weeks doesn't confuse itself.
- After the deadline, render read-only. Enforce server-side with a 409; never trust the client flag.

**After submitting**, show a **BACK TO HOME** button that closes the overlay and returns to the intro panel. Without it the confirmation is a dead end — the only way out was the small CLOSE in the corner.

> ⚠️ **Raise with the couple:** anyone with the password who can find a guest's name can change that guest's RSVP. That's inherent to one-shared-password + RSVP-for-your-party — there's no per-guest identity to check. In practice harmless, and the append-only log makes every change recoverable with attribution. If they're uncomfortable, the fix is a per-party PIN printed on the physical invitation. That's a real feature; only build it if asked.

### Sheet layout

**`Guests`** (couple owns): `guest_id · first_name · last_name · nickname · party_id · party_label · side · notes_private`

**`RSVP_Log`** (app owns, append-only): `timestamp_iso · submission_id · submitted_by_guest_id · party_id · guest_id · status · message · ip_hash`

**`RSVP_Current`** (formulas only): per guest, `XLOOKUP` with `search_mode = -1` scans the log last-to-first, so it naturally returns the most recent entry:

```
=IF($A2="","",IFERROR(XLOOKUP($A2,RSVP_Log!$E$2:$E,RSVP_Log!$F$2:$F,"",0,-1),""))
```

Fill down ~300 rows (`XLOOKUP` doesn't broadcast under `ARRAYFORMULA`). Conditional-format green/grey/amber. The app computes the same reduction independently in TypeScript, so deleting a formula breaks nothing.

Protect the `RSVP_Log` range and label row 1 in red: *"Automatic. Do not edit or sort."*

> 🔴 **Seeding `guest_id` is the one genuinely destructive step.** Generate the ids, then **Copy → Paste special → Values only**. If they're left as live formulas, every recalculation re-rolls the ids and orphans every logged RSVP. Put this in bold in the runbook.

### Google Cloud setup

1. New GCP project → enable **Google Sheets API** only (no Drive scope).
2. Create service account `wedding-site@…` — no IAM roles needed; authorization comes from sheet sharing.
3. Keys → Add key → JSON → download.
4. Share the spreadsheet with the service account email as **Editor**, uncheck "Notify people."
5. Scope: `https://www.googleapis.com/auth/spreadsheets` (read-write; `.readonly` can't append).

Store the key as **one base64 env var**, `GOOGLE_SA_KEY_B64`:
```ts
const sa = JSON.parse(Buffer.from(process.env.GOOGLE_SA_KEY_B64!, 'base64').toString('utf8'));
```
> Storing `GOOGLE_PRIVATE_KEY` raw means fighting `\n` escaping, which breaks differently in `.env.local`, in PowerShell, and in Vercel's dashboard — and Windows CRLF makes it worse. Base64 sidesteps all of it. Never prefix any of these `NEXT_PUBLIC_`.

> ⚠️ **Check this on day one:** many Google Workspace orgs enforce `iam.disableServiceAccountKeyCreation`, which makes step 3 fail outright. If the couple's Google account is a corporate Workspace account (note: you're signed in here with an Accenture address), create the project and sheet under a **personal gmail.com account** instead.

Use `google-auth-library` + `fetch`, or the scoped `@googleapis/sheets`. **Not the `googleapis` monolith** — it's a 100MB+ install covering every Google API and measurably hurts cold starts.

Set region **`sin1`** (Singapore) in `vercel.json`. The default `iad1` costs ~200ms per request from Cebu.

### Email mirror

Send every submission to the couple via Resend, fire-and-forget. ~15 lines, and it means losing the spreadsheet still leaves a complete record in their inbox. For a once-in-a-lifetime event with no other backup, this is the highest value-per-line code in the project.

### Env vars

```
SITE_PASSWORD_HASH=scrypt$16384$8$1$...$...
SESSION_SECRET=<32+ random bytes>
SESSION_EPOCH=1
GOOGLE_SA_KEY_B64=<base64 of service-account JSON>
GOOGLE_SHEET_ID=...
RSVP_DEADLINE=<ISO, Asia/Manila-derived>   ← the couple needs to pick this
ADMIN_SECRET=<random>
IP_HASH_SALT=<random>
RESEND_API_KEY= / COUPLE_NOTIFY_EMAIL=
UPSTASH_REDIS_REST_URL= / UPSTASH_REDIS_REST_TOKEN=   (optional, see below)
```

Validate all of these with a `zod` schema in `lib/env.ts` at module load, so a missing var fails the build rather than a guest's RSVP.

### Rate limiting *(optional — defer to post-launch if you want fewer moving parts)*

In-memory counters are useless on Vercel (attempts spread across ephemeral instances). Proper limiting needs `@upstash/ratelimit` + Upstash Redis — free tier, ~5 min setup. Tiers: 8/10min per IP, 40/day per IP, 300/hour global.

> Keep limits **generous**. Philippine carriers (Globe/Smart CGNAT), offices, and hotels share egress IPs, so a whole building can look like one attacker. If real abuse appears, the right answer is Cloudflare Turnstile on the gate form, not tighter numbers.

Given scrypt already costs ~80ms per attempt, launching without this is defensible. Add it if the site gets shared beyond the guest list.

### Scale note

> ⚠️ **Superseded:** the "flip the model" step below has already been taken — Postgres is the write-of-record.

This architecture is right for ~200 guests and a few hundred writes. **Past roughly 800 guests with seat assignments and caterer-contract meal counts, flip the model**: a real database as write-of-record with the sheet as a push-only mirror. Worth telling the couple now so they know the threshold.

---

## Build order

> ⚠️ **Superseded:** follow the phases in `BUILD_PLAN.md`. The frontend guidance below still applies to its Phase 4.

**Frontend — port `prototype/index.html`, don't rebuild from this document.** The prototype is working, client-approved code and is the more accurate spec for anything visual. Order: `HorizontalTrack` (the scroll timeline is what everything else hangs off) → gate + `AudioProvider` → intro/verse → journey (wheel + photo fan) → wedding tabs → RSVP UI.

Wire the audio in with the gate screen, not as a late add-on — the muted-play-then-unmute handshake is entangled with how the gate submits and navigates, and retrofitting it means rewriting that handler.

The `HorizontalTrack` is the highest-risk piece; get it right first, since the wheel, the photo fan and the section nav all read their state from its single `onUpdate`.

**Where sources disagree:** the prototype wins on look-and-feel, this document wins on design and the password gate, `BUILD_PLAN.md` wins on data, RSVP, admin and sync.

## Verification

1. `npm run dev` — gate rejects a wrong password, accepts `kliffandchao`, and also accepts `" KliffAndChao "` (normalization).
2. Fresh private window → hit `/journey` directly → must redirect to `/`.
3. `curl -H "x-middleware-subrequest: 1" .../api/party?guestId=...` → must still 401. This is the CVE-2025-29927 regression test; it's the reason `requireGate()` exists.
4. Scroll `/journey` end to end: the wheel rotates, the active marker parks at the apex, exactly one chapter is active per snap point, labels stay upright. Check the React DevTools Profiler for a re-render storm during scrub.
5. Toggle OS "reduce motion", reload `/journey` → plain vertical stack, no pinning.
6. Resize to 375px on every page; confirm the mobile timeline branch renders.
7. Against a real test sheet: type a partial last name → suggestions; pick a guest → their whole party lists; submit → a new `RsvpSubmission` exists, `GuestRsvp` has one row per guest, and the `RSVP_Log` mirror gets a row; reload and re-enter the name → **previous answers are prefilled**.
8. Submit a payload with a `guestId` from another party → expect `403 outside_party`.
9. Re-POST the same `clientSubmissionId` → expect `200 {deduped: true}` and **no second submission row**.
10. Fire 5 concurrent submissions for the same party → 5 distinct submission rows, one coherent `GuestRsvp` state, nothing lost.
11. Set `RSVP_DEADLINE` to the past → form renders read-only and the API returns 409.
12. `npm run build` clean, then re-run 2, 3, and 7 on a **Vercel preview deployment** — middleware and Edge behaviour genuinely differ from `dev`.

Intro verse:

13. Tap the verse repeatedly → it cycles every verse in `content/verses.ts` and wraps back to the first; mashing mid-fade never leaves half-swapped text.
14. Tab to the verse and press Enter → same behaviour (it's a `<button>`, not a `div`).
15. Confirm no text is visible in the background plate itself — if the lockup or verse appears twice, the video still has it baked in.

Audio specifically:

16. Enter the correct password → the song starts and fades in. Enter a *wrong* one → no audio, and the element is paused (not left playing muted).
17. Navigate intro → journey → wedding → rsvp → **the song keeps playing without restarting**. This is the regression test for a hard redirect sneaking back in.
18. Mute, then reload and re-enter → still muted (`localStorage`).
19. **On a real iPhone**, not the simulator: confirm playback survives the `await` in the gate handler. This is the single most likely thing to break, and desktop Safari won't reproduce it.
20. Throttle to Slow 3G and load `/` → confirm the MP3 is *not* fetched until ENTER (`preload="none"`).

## What this document does NOT cover

Honest gaps, so nobody discovers them mid-build:

- **All copy is placeholder.** 19 story paragraphs and captions, FAQ answers, entourage names, motif palette. The structure is right; none of the words are.
- **Photos are four recycled placeholders.** `p2_Im0.jpg` still has the old lockup and verse baked into it and looks wrong as a photocard.
- **No mobile design for the journey beyond "stack it vertically."** The wheel and the photo fan are both desktop-only; the phone fallback is functional, not designed. Most guests will be on phones.
- **ENTOURAGE and FAQ have no content and no real design** — structure only.
- **No error/empty states** for the RSVP beyond the listed status codes: no "database unreachable" screen, no offline handling. (Now scheduled in `BUILD_PLAN.md` Phase 7.)
- **No analytics, no cookie notice.** Probably fine for a private site; decide deliberately.
- ~~Nothing is written about domain, DNS or the Vercel project setup.~~ Now covered in `BUILD_PLAN.md` Phases 0 and 8.
- ~~No test suite.~~ Unit tests for the pure logic and database integration tests for search and RSVP concurrency are now required — see `CLAUDE.md`. Visuals, animation and audio stay on the manual Verification checklist.

## Open items for the couple

- 🔴 **Decide how the intro video behaves on phones.** A 16:9 video in a 9:19.5 viewport leaves only **~26% of the frame width visible** under `object-fit: cover`, and the couple sits anywhere from 2% to 80% across depending on the shot — so they frequently fall outside it entirely. `object-position` can't fix a window that narrow. Three options: (a) a separate 9:16 crop swapped in via `<source media>`, (b) letterbox the video into a 4:5 block with the lockup and verse below, or (c) **poster image on mobile, video on desktop only** — recommended, and it also spares phone users an 11.8 MB download.
- **Define the brightness and gallery icons** from frame 4's icon row, or drop them. Sound is wired; the other two are placeholders.
- **Pick an RSVP deadline** (`RSVP_DEADLINE`, Manila time).
- ✅ ~~Timeline lists "Reception" twice~~ — 7:00 is Dinner.
- ✅ ~~Confirm the verse list~~ — Jer 29:11, Luke 1:37, Gen 2:18, Ecc 4:12, Col 3:14.
- ✅ ~~Supply the wordmark~~ — `kliffandchao-logo.svg` delivered and in use.
- **Supply a dedicated gate background.** It currently reuses the intro garden still.
- **ENTOURAGE and FAQ tabs have no designed content**; MOTTIF has only a "FOR THE LADIES" heading.
- **Verify service-account key creation isn't blocked** by a Workspace org policy — use a personal Google account for the project and sheet if it is.
- ✅ ~~Supply the MP3~~ — delivered. Still need to **decide whether music defaults on or muted** (recommendation: on, faded in).
- ✅ ~~Re-export the intro video with no text baked in~~ — the delivered master is already text-free.
- **Rename the MP3 to remove spaces** (`the-blessing.mp3`), and optionally re-encode to ~3 MB.
- ✅ ~~Supply a colour-graded video export~~ — `intro2.mp4` is graded; no correction filter needed.
- **Confirm the 109s trim point**, and decide whether to cut a shorter 40–60s loop to halve the file weight.
- **Supply the brush-script lockup as an SVG**, and confirm the verse list.
- ✅ ~~Create a Google Maps Embed API key~~ — not needed; using Leaflet + OpenStreetMap, which requires no key or billing account. (Note OSM's tile usage policy: fine at wedding-site volumes, but if traffic ever grows, move to a hosted provider.)
- Real photos, story copy, and the entourage list.
- Decide whether anyone-can-edit-anyone's-RSVP is acceptable, or whether they want per-party PINs.
