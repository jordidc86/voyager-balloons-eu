# Conversion Audit: Voyager Balloons Segovia

Scope: static tourism booking website for hot air balloon flights in Segovia, targeting Madrid visitors, gift buyers, couples, families, and private group buyers.

Goal: prioritize changes likely to increase direct bookings within 30 days.

## Executive Priorities

1. Replace generic outbound CTAs with a direct booking path that shows availability, gift purchase, WhatsApp help, and phone support from the first viewport.
2. Add trust above the fold: real rating count, safety/operator credentials, weather-reschedule promise, Madrid access, and “from 120 EUR” price clarity.
3. Turn the package cards into conversion cards: who each option is for, what is included, next available dates, gift suitability, and clear primary CTA per intent.
4. Fix mobile conversion blockers: sticky bottom CTA, shorter hero, visible phone/WhatsApp, compact FAQs, and less below-fold dependency.
5. Add tracking for every meaningful step: CTA clicks, add-to-cart outbound clicks, WhatsApp clicks, phone clicks, gift clicks, review consent, scroll depth, and article-to-booking clicks.

## 1. Friction Points In The Booking Flow

### P0: Booking sends users to an external staging-looking domain

Current state:
- Main CTAs point to `shop.voyagerballoons.eu`.
- Users leave the branded domain before seeing product detail, calendar, payment, or reassurance.
- `/shop` redirects to the same external store.

Why it matters:
- “shop.voyagerballoons.eu” creates trust loss at the exact booking step.
- Visitors from Madrid and gift buyers are likely comparing providers. Any uncertainty at checkout will reduce direct bookings.

Recommended 30-day fix:
- Keep the current WordPress store if needed, but use a branded subdomain such as `shop.voyagerballoons.eu` or `/shop` once technically ready.
- Until then, add microcopy under CTAs: “Reserva segura en nuestra tienda oficial” and make the target expectation explicit.
- Add UTM/source parameters to outbound booking links so performance is measurable.

Impact: Very high.

### P0: No visible availability or calendar preview before leaving the page

Current state:
- The homepage has “Ver Disponibilidad”, “Reservar Classic”, and “Ir a la Tienda”, but no availability signal on the page.

Why it matters:
- Tourism users want to know whether the experience fits their trip dates before committing.
- Gift buyers want reassurance that the recipient can choose later.

Recommended 30-day fix:
- Add a compact booking module above or immediately below packages:
  - “Próximas fechas disponibles”
  - “Billete regalo sin caducidad”
  - “Vuelo al amanecer”
  - primary CTA: “Consultar fechas”
  - secondary CTA: “Comprar billete regalo”
- If live availability is not ready, use a simple manual weekly availability block updated in the HTML or WordPress.

Impact: Very high.

### P0: Gift and booking intents are mixed

Current state:
- The Classic card has both “Regalar Ahora” and “Reservar Classic”, but both point to the same `add-to-cart` URL.
- Gift buyers have different objections than travelers booking for themselves.

Why it matters:
- Gift buyers need to know validity, no expiry, delivery format, recipient flexibility, and refund rules.
- Madrid visitors need logistics, timing, meeting point, and weather plan.

Recommended 30-day fix:
- Split CTA paths:
  - “Comprar billete regalo” with copy: “Sin caducidad. Fecha flexible. Envío por email.”
  - “Reservar una fecha” with copy: “Elige día disponible para volar al amanecer.”
- If both must use the same WooCommerce product, use separate tracking parameters and landing copy.

Impact: Very high.

### P1: Private Suite CTA is weak and under-specified

Current state:
- “Consultar Suite” points to the store homepage.
- The product is 1200 EUR+, but the CTA does not route to WhatsApp or a lead form.

Why it matters:
- High-ticket private flights are consultation-driven. Users need fast human reassurance.

Recommended 30-day fix:
- Change the private CTA path to WhatsApp or a short form with prefilled message:
  - “Quiero consultar un vuelo privado en globo para [número] personas.”
- Add expected response time: “Respuesta por WhatsApp en horario de oficina.”
- Add use cases: pedidas, aniversarios, familias, empresas.

Impact: High.

### P1: The final booking section duplicates earlier CTAs without reducing doubt

Current state:
- Bottom section says “Ir a la Tienda” and “Consultar por WhatsApp”.
- It does not summarize price, weather guarantee, gift validity, or what happens next.

Recommended 30-day fix:
- Replace with a decision block:
  - “Reserva online desde 120 EUR”
  - “Compra un billete regalo sin caducidad”
  - “Consulta un vuelo privado por WhatsApp”
  - “Si el piloto cancela por meteorología, reprogramas o recibes reembolso.”

Impact: High.

## 2. Missing Trust Elements

### P0: Trust proof is mostly placeholder or hidden behind cookie consent

Current state:
- The page claims “Google 5.0” and “TripAdvisor Excellence” as plain badges.
- Reviews are loaded through Elfsight only after cookie consent.

Why it matters:
- Trust is critical for activity bookings involving weather, safety, early hours, and prepayment.
- If a visitor rejects cookies, they may never see real social proof.

Recommended 30-day fix:
- Add static trust proof independent of third-party widgets:
  - rating average and review count
  - 2-3 short real review snippets
  - direct links to Google/TripAdvisor profiles
  - “Más de 25 años volando”
- Keep Elfsight as enhancement, not the only proof.

Impact: Very high.

### P0: Safety credentials are missing

Current state:
- The page mentions pilot/weather safety but does not show operator credentials, insurance, licensed pilots, or aviation compliance.

Recommended 30-day fix:
- Add a trust strip near hero/packages:
  - “Pilotos titulados”
  - “Actividad asegurada”
  - “Vuelos sujetos a condiciones meteorológicas”
  - “Reprogramación si cancela el piloto”
- Add a short “Seguridad y meteorología” section before pricing or FAQ.

Impact: Very high.

### P1: No clear “what happens after booking”

Current state:
- FAQs explain meeting point and time, but the purchase process is not described.

Recommended 30-day fix:
- Add a 3-step process:
  1. Compra o reserva tu billete.
  2. Confirmamos hora y punto de encuentro por WhatsApp 24h antes.
  3. Vuelas al amanecer y brindas con cava al aterrizar.

Impact: High.

### P1: Madrid visitor logistics are underdeveloped

Current state:
- Article mentions 30 minutes by AVE and 50 minutes by car, but homepage does not target Madrid visitors directly.

Recommended 30-day fix:
- Add homepage copy:
  - “A menos de 1 hora de Madrid”
  - “Ideal para escapadas de fin de semana y regalos”
  - “Vuelo al amanecer en Segovia”
- Add FAQ: “¿Puedo venir desde Madrid el mismo día?”

Impact: High.

## 3. Weak CTAs

### P0: Hero CTA lacks price and booking intent clarity

Current state:
- “Ver Disponibilidad” is clear but generic.

Recommended 30-day fix:
- Use stronger CTA + support text:
  - Button: “Reservar vuelo desde 120 EUR”
  - Secondary: “Comprar billete regalo”
  - Support text: “Fecha flexible para regalos. Reprogramación por meteorología.”

Impact: Very high.

### P1: Package card CTAs compete with each other

Current state:
- “Regalar Ahora” and “Reservar Classic” have equal visual weight or similar placement.

Recommended 30-day fix:
- Use one primary CTA per card and a smaller secondary link:
  - Primary: “Reservar Classic”
  - Secondary link: “Comprar como regalo”
- Or split into two cards: “Vuelo Classic” and “Billete Regalo”.

Impact: High.

### P1: WhatsApp is available but not contextual

Current state:
- Floating WhatsApp and bottom CTA exist, but messages are not consistently prefilled for booking intent.

Recommended 30-day fix:
- Use prefilled WhatsApp messages by context:
  - private flight
  - Madrid visitor date query
  - gift buyer
  - weather/date doubt
- Track each WhatsApp click separately.

Impact: High.

### P2: Footer CTAs are post-flight service links, not booking links

Current state:
- Footer links focus on photos and certificate.

Recommended 30-day fix:
- Add footer booking links:
  - “Reservar vuelo”
  - “Comprar regalo”
  - “Consultar vuelo privado”

Impact: Medium.

## 4. Mobile UX Problems

### P0: No sticky mobile booking CTA

Current state:
- Mobile menu exists, but once users scroll, the strongest conversion CTA is not persistently available except WhatsApp.

Recommended 30-day fix:
- Add a sticky mobile bottom bar:
  - “Reservar”
  - “Regalar”
  - WhatsApp icon/button
- Hide or reposition the floating WhatsApp button to avoid overlap.

Impact: Very high.

### P1: Hero is likely too tall on mobile

Current state:
- Hero uses `height: 100vh`.

Why it matters:
- Users may not see price, trust, or packages without scrolling.

Recommended 30-day fix:
- On mobile, reduce hero height or add first-viewport hints:
  - price from 120 EUR
  - rating
  - CTA pair
  - next content visible.

Impact: High.

### P1: Cookie banner can cover primary CTA area on mobile

Current state:
- Cookie banner is fixed at the bottom and contains two buttons.
- WhatsApp button is also fixed at bottom-right.

Recommended 30-day fix:
- On mobile, make banner compact and ensure it does not cover sticky booking CTAs.
- Consider placing cookie banner above sticky CTA or delaying review widget load prompt until reviews section.

Impact: High.

### P1: Package comparison is not optimized for quick scanning

Current state:
- Package cards stack on mobile; users must scroll through long feature lists.

Recommended 30-day fix:
- Add compact summary above cards:
  - “Classic: 120 EUR/persona”
  - “Privado: desde 1200 EUR/grupo”
  - “Regalo: sin caducidad”
- Keep package cards, but add quick jump CTAs.

Impact: Medium-high.

### P2: Mobile nav lacks direct phone call CTA

Current state:
- Mobile nav has booking CTA but no `tel:` call link.

Recommended 30-day fix:
- Add `Llamar` and `WhatsApp` in mobile menu or sticky bottom bar.

Impact: Medium.

## 5. SEO Gaps

### P0: Homepage does not directly target Madrid day-trip and gift search intent

Current state:
- Title targets “Vuelos en Globo en Segovia”.
- Copy strongly targets Segovia, but not Madrid visitors or gift buyers.

Recommended 30-day fix:
- Add homepage sections and terms:
  - “Vuelo en globo cerca de Madrid”
  - “Regalar vuelo en globo en Segovia”
  - “Escapada desde Madrid”
  - “Billete regalo sin caducidad”
- Add internal links from blog articles to package booking CTAs.

Impact: High.

### P1: Structured data is incomplete for booking/product intent

Current state:
- JSON-LD uses `LocalBusiness`.
- No `Product`, `Offer`, `TouristTrip`, `FAQPage`, or review/rating markup.

Recommended 30-day fix:
- Add structured data for:
  - `Product`/`Offer` for Classic Adventure at 120 EUR
  - `FAQPage` for homepage FAQs
  - `LocalBusiness` with telephone and service area
  - possibly `TouristAttraction`/`TouristTrip` depending final schema strategy

Impact: High.

### P1: Blog articles are useful but not yet conversion-oriented enough

Current state:
- Articles exist for Segovia, first flight, gift, and balloon navigation.
- CTAs route to the store, but articles should include more internal links and intent-specific conversion blocks.

Recommended 30-day fix:
- Add mid-article CTA blocks:
  - first flight article: “Reservar mi primer vuelo”
  - gift article: “Comprar billete regalo”
  - Madrid/Segovia article: “Ver fechas para escapada desde Madrid”
- Add related articles and package links.

Impact: Medium-high.

### P1: Missing dedicated landing pages for high-intent queries

Recommended 30-day fix:
- Create or adapt pages for:
  - `/vuelo-globo-segovia`
  - `/regalar-vuelo-globo`
  - `/vuelo-globo-madrid-segovia`
  - `/vuelo-globo-privado`
- Each should have direct CTAs and targeted FAQs.

Impact: Medium-high.

### P2: Legal page is `noindex`, but cancellation policy content may reduce buyer doubts

Current state:
- Legal details are noindex and buried in footer.

Recommended 30-day fix:
- Keep legal noindex, but surface buyer-friendly policy snippets on sales pages:
  - “Si cancelamos por meteorología, reprogramas o recibes reembolso.”
  - “Billetes regalo sin caducidad, no reembolsables.”

Impact: Medium.

## 6. Performance Issues

### P0: Third-party reviews are gated, but current fallback wastes review section space

Current state:
- Elfsight only loads after cookie acceptance.
- The reviews area has a large minimum height.

Recommended 30-day fix:
- Add static review cards so the area is valuable before consent.
- Load the widget only after consent or user interaction.

Impact: High.

### P1: CSS and inline styles are not production-optimized

Current state:
- One global CSS file is acceptable for size, but there is duplicated inline page-specific styling across article pages.

Recommended 30-day fix:
- Move repeated article styles into `style.css`.
- Keep only unique background image rules inline or use modifier classes.

Impact: Medium.

### P1: Images have no responsive `srcset`, explicit dimensions, or modern variants

Current state:
- JPEGs are moderate in size, but there are no explicit width/height attributes, `srcset`, WebP/AVIF variants, or fetch priority.

Recommended 30-day fix:
- Add explicit image dimensions to reduce layout shift.
- Add optimized WebP versions and use `<picture>` for hero/blog cards.
- Preload or `fetchpriority="high"` the hero image.
- Lazy-load below-fold images.

Impact: Medium-high.

### P2: Google Fonts are render-blocking external assets

Current state:
- Fonts are loaded from Google Fonts on every page.

Recommended 30-day fix:
- Self-host fonts or reduce weights.
- Keep only weights used in UI.

Impact: Medium.

### P2: Animations may delay perceived content

Current state:
- Many sections start as `opacity: 0` until IntersectionObserver runs.

Recommended 30-day fix:
- Ensure no critical conversion content depends on JS to become visible.
- Respect `prefers-reduced-motion`.

Impact: Medium.

## 7. Analytics And Conversion Tracking Gaps

### P0: No visible analytics or conversion tracking

Current state:
- No GA4, Google Ads, Meta Pixel, server-side events, or custom event tracking is visible in the code.

Recommended 30-day fix:
- Implement a consent-aware analytics setup.
- Track at minimum:
  - `cta_click_booking_hero`
  - `cta_click_gift`
  - `cta_click_classic_add_to_cart`
  - `cta_click_private_whatsapp`
  - `whatsapp_click_floating`
  - `phone_click`
  - `outbound_store_click`
  - `review_widget_accept`
  - `faq_open`
  - `blog_to_booking_click`

Impact: Very high.

### P0: No booking funnel visibility after outbound click

Current state:
- Booking happens on WordPress/WooCommerce outside this static site.

Recommended 30-day fix:
- Add consistent UTM parameters to every outbound store link:
  - `utm_source=voyager_site`
  - `utm_medium=cta`
  - `utm_campaign=direct_booking`
  - `utm_content=hero|classic_card|gift_card|footer|blog`
- Configure WooCommerce/GA4 to read those sessions and purchase events.

Impact: Very high.

### P1: WhatsApp leads are not measured by intent

Current state:
- WhatsApp links exist but are mostly generic.

Recommended 30-day fix:
- Use context-specific WhatsApp URLs and track click events:
  - gift inquiry
  - private flight
  - date availability
  - post-flight photos/certificate
- Optionally add a short lead form for private flights to capture email before WhatsApp.

Impact: High.

### P1: No A/B testing plan for fastest wins

Recommended 30-day fix:
- Test simple copy/CTA variants manually for 2 weeks each:
  - Hero CTA: “Reservar desde 120 EUR” vs “Ver fechas disponibles”
  - Gift CTA: “Comprar billete regalo sin caducidad” vs “Regalar Ahora”
  - Trust strip placement above vs below hero CTA

Impact: Medium-high.

## 30-Day Implementation Order

### Week 1: Fix conversion-critical messaging and trust

1. Add above-fold trust strip: price from 120 EUR, Google rating/review count, weather reprogramming, pilots/insurance.
2. Split hero CTAs into booking and gift intents.
3. Add static review snippets independent of Elfsight.
4. Add “what happens after booking” three-step section.
5. Add UTM parameters to every outbound store CTA.

### Week 2: Improve package and mobile conversion

1. Rewrite package cards for intent clarity.
2. Add mobile sticky bottom CTA: Reservar, Regalar, WhatsApp.
3. Add contextual WhatsApp links for private and gift inquiries.
4. Reduce mobile hero height and surface price/trust earlier.

### Week 3: SEO and landing page upgrades

1. Add structured data for Product/Offer and FAQPage.
2. Create targeted landing pages for gift, Madrid visitors, and private flights.
3. Add internal CTA blocks inside all blog articles.
4. Add Madrid-specific FAQ and homepage copy.

### Week 4: Tracking and performance

1. Implement consent-aware analytics.
2. Track all CTA, WhatsApp, phone, FAQ, outbound store, and blog conversion events.
3. Add image dimensions, lazy loading, and optimized WebP variants.
4. Move repeated article CSS into shared stylesheet.

## Highest-Impact Changes To Do First

1. Hero: “Reservar vuelo en globo desde 120 EUR” + “Comprar billete regalo sin caducidad.”
2. Trust strip above fold with real ratings, safety, weather guarantee, and 25 years flying.
3. Static reviews visible without cookie consent.
4. Branded booking transition or clear “tienda oficial” reassurance before outbound store click.
5. Mobile sticky CTA bar.
6. UTM and event tracking for all booking/gift/WhatsApp clicks.
7. Package cards split by intent: traveler, gift buyer, private group.

