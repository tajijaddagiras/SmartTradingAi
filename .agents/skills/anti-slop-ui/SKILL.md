---
name: anti-slop-ui
description: >-
  Human-crafted UI/UX design skill that prevents AI slop, eliminates generic templates,
  and enforces institutional financial terminal aesthetics with seamless responsiveness
  across Mobile, Tablet, and Desktop.
version: 1.0.0
---

# Anti-Slop UI/UX Engineering Skill

This skill enforces high-craft, human-designed user interface standards inspired by **Nutlope/hallmark** and **taste-skill**, completely eliminating generic "AI slop" tells in financial, trading, and dashboard applications.

---

## 1. What Defines "AI Slop" in Web UI?

| AI Slop Tell (Banned ❌) | Human-Crafted Institutional Standard (Required ✅) |
| :--- | :--- |
| **Nested Card Clutter:** Cards placed inside cards inside containers with heavy borders and drop shadows. | **Flat Visual Planes:** Single-depth structural cards separated by hairline borders (`1px solid rgba(255, 255, 255, 0.08)`) and rhythmic whitespace. |
| **Purple/Cyan Neon Gradient Soup:** Arbitrary glowing gradients everywhere. | **Semantic Monochrome with Accent Purpose:** Deep obsidian/slate base (`#090d16`), crisp high-contrast text (`#f8fafc`), and purposeful trade colors (Green/Red/Blue). |
| **Disproportionate Giant Buttons:** Oversized chunky controls that push critical data offscreen. | **Compact Ergonomic Controls:** Precise `32px` - `36px` control heights matching professional desktop trading software (TradingView / Bloomberg / cTrader). |
| **Decorative Emoji Icons:** Rocket ship 🚀, fire 🔥, bags of cash 💰 in headers. | **Clean Typography or Vector SVG:** Sharp micro-badges, tabular numerical indicators, and semantic typography. |
| **Horizontal Overflow on Mobile:** Elements bursting out of viewports, causing awkward horizontal scrolling. | **Zero Overflow:** `overflow-x: clip;` on `html, body`. Adaptive flex/grid with `minmax(0, 1fr)`. |

---

## 2. Institutional Design System Tokens

When building or refining interfaces, use this exact token framework:

```css
:root {
  /* Surface Layers (Deep Obsidian & Slate) */
  --surface-base: #080b11;
  --surface-panel: #0d121d;
  --surface-overlay: #131b2a;
  --surface-hover: rgba(255, 255, 255, 0.04);
  --surface-active: rgba(255, 255, 255, 0.08);

  /* Hairline Borders */
  --border-subtle: rgba(255, 255, 255, 0.08);
  --border-focus: rgba(255, 255, 255, 0.22);
  --border-active: #3b82f6;

  /* Typography Colors */
  --text-primary: #f8fafc;
  --text-secondary: #94a3b8;
  --text-muted: #64748b;
  --text-inverse: #0f172a;

  /* Trading Semantics */
  --trade-bullish: #10b981;
  --trade-bearish: #f43f5e;
  --trade-info: #0284c7;
  --trade-warning: #f59e0b;

  /* Spacing Scale */
  --space-2xs: 2px;
  --space-xs: 4px;
  --space-sm: 8px;
  --space-md: 12px;
  --space-lg: 16px;
  --space-xl: 24px;
  --space-2xl: 32px;

  /* Radii */
  --radius-xs: 4px;
  --radius-sm: 6px;
  --radius-md: 8px;
  --radius-lg: 12px;
  --radius-full: 9999px;
}
```

---

## 3. Responsive Screen Layout Matrix

### A. Mobile Viewport (< 768px)
* **Header:** Ultra-slim (`44px` height). Brand icon + Active Symbol + Compact Balance.
* **Navigation:** Bottom floating glass dock (`56px` height) with touch targets $\ge 44px$.
* **Chart Area:** Aspect ratio tuned for portrait/landscape auto-fit (`min-height: 380px`).
* **Forms & Setting Cards:** Stacked 1-column layout, full-width inputs, clear tappable steppers.

### B. Tablet & Laptop Viewport (768px – 1199px)
* **Header:** Single-row toolbar containing Symbol Switcher, Live Spread, Quick Buy/Sell, Bot Toggle.
* **Layout:** Chart dominates top (60% height), telemetry and order management split bottom (40%).

### C. Desktop & Ultra-wide Viewport (1200px+)
* **Density:** High information density. Multi-column telemetry grids.
* **Alignment:** Strict 32px or 36px control baseline alignment across the top toolbar.

---

## 4. Verification & Audit Checklist

Before finalizing any frontend change:
1. **Double-Card Check:** Are there any dark boxes sitting inside another dark box? If yes, remove the inner container and use subtle separator lines instead.
2. **Horizontal Overflow Check:** Resize the viewport from 360px to 1920px. Does any element cause horizontal scrollbars? (Check `document.documentElement.scrollWidth > window.innerWidth`).
3. **Contrast Ratio Check:** Are labels and prices legible against their backgrounds (WCAG AA $\ge 4.5:1$)?
4. **Interactive Responsiveness:** Do buttons have instant active states (`:active { transform: scale(0.98); }`) without sluggish animations?
