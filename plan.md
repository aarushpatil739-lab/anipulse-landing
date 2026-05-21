# plan.md

## 1. Objectives
- Deliver a frontend-only landing page for **CyberEdit** (Next.js 15 + TS + Tailwind + Framer Motion) with a **dark anime cyberpunk** aesthetic.
- Implement the required sections (Hero, Features, How It Works, Demo, CTA, Footer) with **responsive layout**, **premium glassmorphism**, and **neon glow** UI.
- Keep code modular and scalable (App Router, reusable components) and optimized for performance.

## 2. Implementation Steps

### Phase 1: Core POC (skip — not required)
- No external integrations, auth, uploads, or APIs. Build directly.

### Phase 2: V1 App Development (Landing Page)
**User stories**
1. As a creator, I want to instantly understand what CyberEdit does from the hero headline and visuals.
2. As a mobile user, I want the entire page to be readable and fast without horizontal scrolling.
3. As a user, I want smooth animations that feel premium but don’t distract from the CTA.
4. As a creator, I want to scan features quickly and know if it supports TikTok/Reels export.
5. As a user, I want to see believable demo previews that communicate “anime edit output”.

**Build steps**
- Scaffold app
  - Next.js 15 App Router, TypeScript, TailwindCSS, Framer Motion.
  - Set up `tailwind.config` theme tokens (purple/cyan/pink, background, glow shadows).
- Project structure (prepared for future API)
  - `app/(marketing)/page.tsx` (landing)
  - `components/marketing/*` (Hero, Features, HowItWorks, DemoPreview, CTA, Footer, Navbar)
  - `components/ui/*` (Button, Card, Container, GlowBg, SectionHeading)
  - `lib/*` (constants: nav links, feature list)
- Global styling & design system
  - Dark base, subtle grain/noise overlay, glass cards, neon borders, animated gradient blobs.
  - Reusable `Glow` and `GlassCard` styles.
- Implement sections
  - Hero: headline/subtitle, primary CTA “Generate AI Edit”, secondary “Watch demo”, animated background (gradient + particles/glow).
  - Features: 5 feature cards with icons, hover glow.
  - How it works: 4-step timeline/cards.
  - Demo preview: 3–6 fake preview cards (anime images), hover lift + cinematic overlay.
  - CTA: large centered statement + glowing button.
  - Footer: logo (text-based cyberpunk), nav, social placeholders (X/Discord/Instagram/TikTok/YouTube).
- Animations (Framer Motion)
  - Section reveal on scroll, staggered card entrances, hover micro-interactions, subtle looping hero gradient.
  - Respect `prefers-reduced-motion`.
- Performance & accessibility pass
  - Use `next/image`, optimized sizes, lazy loading.
  - Semantic headings, focus states, contrast checks, keyboard nav.

**Phase 2 test (1 round E2E)**
- Verify all sections render, no layout shift, responsive breakpoints.
- Check animations performance (desktop/mobile), reduced motion.
- Validate links/CTAs, hover/focus states.

### Phase 3: V1 Polish + Scalability Improvements
**User stories**
1. As a user, I want smooth scrolling to sections from the navbar.
2. As a user, I want the CTA button to feel responsive with press/hover feedback.
3. As a user, I want consistent spacing/typography across sections.
4. As a user, I want the demo cards to look like a creator dashboard (not random images).
5. As a developer, I want content (features/steps/nav) editable via constants, not hardcoded.

**Improvements**
- Add sticky/glass Navbar with section anchors + mobile menu.
- Add `lib/content.ts` for all copy + arrays for features/steps/social.
- Add “badge” elements (e.g., “New: Emotion Detection”), and optional testimonials strip (if space).
- Refine demo previews with consistent aspect ratios, overlays, tags (FPS, Beat Sync, Style).
- Add SEO metadata (`app/layout.tsx`), OpenGraph basics.

**Phase 3 test (1 round E2E)**
- Verify smooth scroll, mobile menu, anchors.
- Verify no regressions in layout/animations.

### Phase 4: Optional Enhancements (only if requested)
**User stories**
1. As a user, I want a pricing section so I can understand value quickly.
2. As a creator, I want a comparison table vs CapCut/others.
3. As a user, I want a waitlist/email capture form (frontend-only placeholder).
4. As a user, I want a FAQ to reduce uncertainty before clicking CTA.
5. As a developer, I want a ready path to add API routes later without refactor.

**Add-ons**
- Pricing + FAQ sections.
- Waitlist modal (no backend; local state + “coming soon”).
- Component library refinement and docs in README.

## 3. Next Actions
- Create Next.js app scaffold + Tailwind theme tokens.
- Build shared UI components (Button/Card/Container/SectionHeading/GlowBg).
- Implement page sections in order: Hero → Features → HowItWorks → Demo → CTA → Footer.
- Run one full responsive pass and animation/performance pass.

## 4. Success Criteria
- Matches cyberpunk anime SaaS aesthetic (glass + neon purple/cyan + pink accent) with premium feel.
- Fully responsive and readable on mobile/desktop; no overflow issues.
- Smooth Framer Motion animations; reduced-motion supported.
- Clean App Router structure with reusable components and content constants.
- Lighthouse-friendly: optimized images, minimal layout shift, fast initial load.